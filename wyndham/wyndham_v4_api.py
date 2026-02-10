"""
================================================================================
WYNDHAM HOTEL PRICING SCRAPER - API INTERCEPTION VERSION (V4.0)
================================================================================

PURPOSE:
This is the NEW simplified scraper that intercepts API calls instead of
downloading CSV files. It captures the JSON response from the API endpoint
and saves it directly to a file.

PROBLEM IT SOLVES:
- Eliminates complex CSV download and parsing logic
- Much faster and more reliable
- Direct access to API data in JSON format
- No need to navigate to calendar page

ROLE IN THE SYSTEM:
This module:
1. Logs in to Wyndham RevIQ
2. Waits for the API call to happen automatically
3. Captures the JSON response using Chrome DevTools Protocol
4. Saves it to new_record_json.json (overwrite mode)
5. Processes and saves to database using UpdateRecord model

USAGE:
    python3 wyndham_v4_api.py

================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# Standard library imports
import os
import sys
import time
import logging
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Any

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium_stealth import stealth

# Local imports
from wyndham_config import WyndhamConfig
from wyndham_db_operations import WyndhamDBOperations

# Add parent directory to path for model and mapper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.wyndham_model import WyndhamUpdateRecord
from mappers.wyndham_mapper import map_wyndham_json_to_update_record


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format=WyndhamConfig.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(WyndhamConfig.get_log_file_path())
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# BROWSER SETUP
# ============================================================================

def create_browser():
    """
    Create Chrome browser with network logging enabled.
    
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    logger.info("Creating Chrome browser instance...")
    
    chrome_options = ChromeOptions()
    
    # Enable performance logging for network interception
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    # Browser options
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # User agent
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(WyndhamConfig.IMPLICIT_WAIT)
        
        # Apply stealth mode
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="MacOS",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        
        logger.info("✅ Chrome browser created successfully")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Failed to create browser: {e}")
        raise


# ============================================================================
# LOGIN FUNCTION
# ============================================================================

def login_to_wyndham_reviq(driver, username, password, last_four_digits=None):
    """
    Log in to Wyndham Hotels RevIQ via IdeasRMS SSO.
    
    Args:
        driver: Selenium WebDriver instance
        username: Wyndham RevIQ username
        password: Wyndham RevIQ password (not used in Wyndham flow)
        last_four_digits: Last four digits of phone for MFA
    
    Returns:
        bool: True if login successful
    """
    logger.info(f"Attempting login for user: {username}")
    
    try:
        # Navigate to login page
        driver.get(WyndhamConfig.LOGIN_URL)
        logger.info(f"Navigated to login page: {WyndhamConfig.LOGIN_URL}")
        
        wait = WebDriverWait(driver, 20)
        
        # Click Wyndham Account button
        try:
            logger.info("Looking for Wyndham account button...")
            wyndham_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, WyndhamConfig.LOGIN_WYNDHAM_BUTTON))
            )
            driver.execute_script("arguments[0].click();", wyndham_button)
            logger.info("✅ Clicked 'Sign in with Wyndham Account' button")
            time.sleep(2)
        except TimeoutException:
            logger.warning("⚠️ Wyndham account button not found, proceeding with regular login")
        
        # Enter username
        logger.info("Entering username...")
        try:
            username_field = wait.until(EC.presence_of_element_located((By.ID, WyndhamConfig.LOGIN_USERNAME_FIELD_ID)))
            username_field.clear()
            username_field.send_keys(username)
            logger.info(f"✅ Username entered: {username}")
        except Exception as e:
            logger.warning(f"Could not find input27, trying generic selectors: {e}")
            username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']")))
            username_field.clear()
            username_field.send_keys(username)
            logger.info(f"✅ Username entered: {username}")
        
        # Click Next button
        try:
            logger.info("Clicking Next button...")
            next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, WyndhamConfig.LOGIN_NEXT_BUTTON)))
            next_button.click()
            logger.info("✅ Clicked Next button")
            time.sleep(2)
        except Exception as e:
            logger.error(f"❌ Error clicking Next: {e}")
            driver.save_screenshot(f'{WyndhamConfig.DOWNLOAD_DIR}login_next_error.png')
            return False
        
        # Handle MFA - Select factor and SMS
        logger.info("Selecting MFA factor...")
        try:
            # If last_four_digits provided, select that factor first
            if last_four_digits:
                try:
                    element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"a.select-factor[aria-label*='{last_four_digits}']"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.select-factor[aria-label*='{last_four_digits}']")))
                    element.click()
                    time.sleep(2)
                    logger.info(f"✅ Selected MFA factor with last four digits: {last_four_digits}")
                except TimeoutException:
                    logger.warning("⚠️ Could not find MFA factor with last four digits, trying SMS directly")
            
            # Click SMS button
            logger.info("Clicking SMS OTP option...")
            sms_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, WyndhamConfig.LOGIN_SMS_BUTTON))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sms_button)
            sms_button.click()
            logger.info("✅ Clicked 'Receive a code via SMS'")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Error during MFA selection: {e}")
            driver.save_screenshot(f'{WyndhamConfig.DOWNLOAD_DIR}mfa_selection_error.png')
            return False
        
        # Get OTP from user
        print("\n" + "="*60)
        print("*** ACTION REQUIRED: ***")
        print("Please check your device for the OTP code.")
        print("="*60)
        otp = input("Enter the verification code you received here and press Enter: ").strip()
        logger.info("OTP received. Submitting...")
        
        # Enter OTP code
        try:
            otp_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, WyndhamConfig.LOGIN_OTP_FIELD))
            )
            otp_field.clear()
            otp_field.send_keys(otp)
            logger.info("✅ OTP entered")
        except Exception as e:
            logger.error(f"❌ Error entering OTP: {e}")
            driver.save_screenshot(f'{WyndhamConfig.DOWNLOAD_DIR}otp_entry_error.png')
            return False
        
        # Verify OTP
        try:
            verify_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, WyndhamConfig.LOGIN_VERIFY_BUTTON))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", verify_button)
            time.sleep(1)
            verify_button.click()
            logger.info("✅ OTP verification submitted")
            time.sleep(3)
        except Exception as e:
            logger.error(f"❌ Error verifying OTP: {e}")
            driver.save_screenshot(f'{WyndhamConfig.DOWNLOAD_DIR}otp_verify_error.png')
            return False
        
        # Wait for successful login
        try:
            logger.info("⏳ Waiting for login to complete...")
            
            wait.until(lambda d: "reviq.ideasrms.com" in d.current_url)
            logger.info("✅ Login successful!")
            
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(3)
            
            return True
            
        except TimeoutException as e:
            logger.error(f"❌ Timeout waiting for login redirect: {e}")
            logger.error(f"Current URL: {driver.current_url}")
            driver.save_screenshot(f'{WyndhamConfig.DOWNLOAD_DIR}login_timeout_error.png')
            return False
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            logger.error(f"Current URL: {driver.current_url}")
            driver.save_screenshot(f'{WyndhamConfig.DOWNLOAD_DIR}login_final_error.png')
            return False
        
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        driver.save_screenshot(f'{WyndhamConfig.DOWNLOAD_DIR}login_general_error.png')
        return False


# ============================================================================
# API INTERCEPTION
# ============================================================================

def capture_api_response(driver):
    """
    Capture JSON response from Wyndham API call.
    
    Args:
        driver: Selenium WebDriver instance
    
    Returns:
        dict or None: JSON response data
    """
    logger.info("🔍 Waiting for Wyndham API call...")
    
    try:
        # Enable network tracking
        driver.execute_cdp_cmd('Network.enable', {})
        logger.info("✅ Network tracking enabled")
        
        # Wait for API call (max 60 seconds)
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            logs = driver.get_log('performance')
            
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    if log['method'] == 'Network.responseReceived':
                        response = log['params']['response']
                        url = response.get('url', '')
                        
                        # Check for Wyndham API patterns
                        # Look for calendar/pricing API endpoints
                        if any(pattern in url for pattern in [
                            '/calendar/data',
                            '/pricing/data',
                            '/properties/',
                            'start_date',
                            'end_date'
                        ]):
                            logger.info(f"✅ Found API call: {url}")
                            
                            request_id = log['params']['requestId']
                            
                            try:
                                response_body = driver.execute_cdp_cmd(
                                    'Network.getResponseBody',
                                    {'requestId': request_id}
                                )
                                
                                if 'body' in response_body:
                                    json_data = json.loads(response_body['body'])
                                    
                                    # Validate it's the right data structure
                                    if isinstance(json_data, list) and len(json_data) > 0:
                                        if 'dates' in json_data[0]:
                                            logger.info(f"✅ Captured JSON response ({len(response_body['body'])} bytes)")
                                            return json_data
                                    
                            except Exception as e:
                                logger.debug(f"Could not get response body for {url}: {e}")
                                continue
                                
                except Exception as e:
                    continue
            
            time.sleep(1)
        
        logger.warning("⚠️ Timeout waiting for Wyndham API call")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error capturing API response: {e}")
        return None


def save_json_response(json_data, file_path):
    """
    Save JSON data to file (overwrite mode).
    
    Args:
        json_data: JSON data to save
        file_path: Path to save the file
    
    Returns:
        bool: True if successful
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"✅ Saved JSON response to: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving JSON file: {e}")
        return False


def process_and_save_to_database(json_data, db_ops):
    """
    Process JSON data and save WyndhamUpdateRecord objects to database.
    
    Args:
        json_data: JSON data from API response
        db_ops: WyndhamDBOperations instance
    
    Returns:
        tuple: (success_count, fail_count)
    """
    logger.info("📊 Processing JSON data and saving to database...")
    
    success_count = 0
    fail_count = 0
    
    try:
        # Iterate through properties in JSON
        for property_obj in json_data:
            property_uuid = property_obj.get("id")
            
            if not property_uuid:
                logger.warning("⚠️ Property missing 'id' field, skipping...")
                continue
            
            logger.info(f"Processing property: {property_uuid}")
            
            # Iterate through dates for this property
            for date_obj in property_obj.get("dates", []):
                try:
                    # Map JSON to WyndhamUpdateRecord using mapper
                    record = map_wyndham_json_to_update_record(
                        property_uuid=property_uuid,
                        date_str=date_obj["date"],
                        
                        price_value=Decimal(str(date_obj["price"]["value"]))
                        if date_obj.get("price") else None,
                        
                        previousRate_value=Decimal(str(date_obj["previousRate"]["value"]))
                        if date_obj.get("previousRate") else None,
                        
                        priceDiff_value=Decimal(str(date_obj["priceDiff"]["value"]))
                        if date_obj.get("priceDiff") else None,
                        
                        compSetAvg=Decimal(str(date_obj["compSetAvg"]["value"]))
                        if date_obj.get("compSetAvg") else None,
                        
                        onBookPercent=int(str(date_obj["onBookPercent"]))
                        if date_obj.get("onBookPercent") is not None else None,
                        
                        forecastPercent=int(str(date_obj["forecastPercent"]))
                        if date_obj.get("forecastPercent") is not None else None,
                        
                        updated_by_rm=date_obj.get("priceOverridden", False),
                        
                        lyBookingPercent=int(str(date_obj["lyBookingPercent"]))
                        if date_obj.get("lyBookingPercent") is not None else None,
                        
                        lyRevenue=Decimal(str(date_obj["lyRevenue"]["value"]))
                        if date_obj.get("lyRevenue") is not None else None,
                        
                        arrivals=date_obj.get("arrivals"),
                        departures=date_obj.get("departures"),
                        
                        physicalCapacity=date_obj.get("physicalCapacity"),
                        outOfOrder=date_obj.get("outOfOrder"),
                        onBook=date_obj.get("onBook")
                    )
                    
                    # Save to database
                    success = db_ops.save_pricing_data(record, scraping_run_id=None)
                    
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error processing date {date_obj.get('date', 'unknown')}: {e}")
                    fail_count += 1
                    continue
        
        logger.info(f"✅ Database save complete: {success_count} saved, {fail_count} failed")
        return (success_count, fail_count)
        
    except Exception as e:
        logger.error(f"❌ Error processing JSON data: {e}")
        return (success_count, fail_count)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main entry point for the API interception scraper.
    """
    print("=" * 80)
    print("WYNDHAM HOTELS PRICING SCRAPER")
    print("API Interception Version - V4.0")
    print("=" * 80)
    print()
    
    # Initialize database
    print("🔌 Connecting to database...")
    try:
        db_ops = WyndhamDBOperations()
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Fetch properties
    print("\n📋 Fetching properties to scrape...")
    properties = db_ops.get_active_properties()
    
    if not properties:
        print("❌ No active Wyndham properties found")
        return
    
    print(f"✅ Found {len(properties)} properties:")
    for idx, prop in enumerate(properties, 1):
        print(f"   {idx}. {prop['hotel_name']} ({prop['property_code']})")
    
    # Get credentials
    username = properties[0]['username']
    password = properties[0]['password']
    
    # Get last four digits for MFA
    print("\nMFA Setup:")
    last_four = input("Enter last 4 digits of your phone (or press Enter to skip): ").strip()
    if not last_four:
        last_four = None
    
    # Launch browser
    print("\n🌐 Launching browser...")
    driver = None
    
    try:
        driver = create_browser()
        print("✅ Browser launched")
        
        # Login
        print(f"\n🔐 Logging in to Wyndham RevIQ as {username}...")
        
        login_success = login_to_wyndham_reviq(driver, username, password, last_four)
        
        if not login_success:
            print("❌ Login failed")
            return
        
        print("✅ Login successful")
        
        # Capture API response
        print("\n📡 Waiting for API data...")
        time.sleep(5)  # Wait for page to load and API calls to trigger
        
        json_data = capture_api_response(driver)
        
        if not json_data:
            print("❌ Failed to capture API response")
            return
        
        # Save JSON
        output_file = "/Users/apple/python/hm_scrapers/wyndham/new_record_json.json"
        print(f"\n💾 Saving JSON response to: {output_file}")
        
        success = save_json_response(json_data, output_file)
        
        if success:
            print("✅ JSON data saved successfully")
            print(f"📊 Data size: {len(json.dumps(json_data))} bytes")
        else:
            print("❌ Failed to save JSON data")
        
        # Process and save to database
        print("\n💾 Processing and saving to database...")
        success_count, fail_count = process_and_save_to_database(json_data, db_ops)
        
        print(f"✅ Database save complete:")
        print(f"   - Successfully saved: {success_count} records")
        print(f"   - Failed: {fail_count} records")
        
        # Summary
        print("\n" + "=" * 80)
        print("SCRAPING COMPLETE")
        print("=" * 80)
        print(f"✅ JSON saved to: {output_file}")
        print(f"✅ Database records saved: {success_count}")
        print(f"⚠️  Database records failed: {fail_count}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("\n🧹 Cleaning up...")
            try:
                driver.quit()
                print("✅ Browser closed")
            except:
                pass


if __name__ == "__main__":
    main()
