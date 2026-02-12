"""
================================================================================
CHOICE HOTEL PRICING SCRAPER - API INTERCEPTION VERSION (V4.0)
================================================================================

PURPOSE:
This is the NEW simplified scraper that intercepts API calls instead of
downloading CSV files. It captures the JSON response from the v2?start_date...
API endpoint and saves it directly to a file.

PROBLEM IT SOLVES:
- Eliminates complex CSV download and parsing logic
- Much faster and more reliable
- Direct access to API data in JSON format
- No need to navigate to calendar page

ROLE IN THE SYSTEM:
This module:
1. Logs in to Choice MAX
2. Waits for the v2?start_date... API call to happen automatically
3. Captures the JSON response using Chrome DevTools Protocol
4. Saves it to new_record_json.json (overwrite mode)

USAGE:
    python3 choice_v4_api.py

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
from choice_config import ChoiceConfig
from choice_db_operations import ChoiceDBOperations

# Add parent directory to path for model and mapper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.model import UpdateRecord
from mappers.mapper import map_json_to_update_record


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format=ChoiceConfig.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ChoiceConfig.get_log_file_path())
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
    chrome_options.add_argument("--headless=new")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1920,1080")
    
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
        driver.implicitly_wait(ChoiceConfig.IMPLICIT_WAIT)
        
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

def login_to_choice_max(driver, username, password, verification_type="PN"):
    """
    Log in to Choice Hotels MAX via IdeasRMS SSO.
    
    Args:
        driver: Selenium WebDriver instance
        username: Choice MAX username
        password: Choice MAX password
        verification_type: "PN" for Push Notification, "OTP" for One-Time Password
    
    Returns:
        bool: True if login successful
    """
    logger.info(f"Attempting login for user: {username}")
    
    try:
        # Navigate to login page
        driver.get(ChoiceConfig.LOGIN_URL)
        logger.info(f"Navigated to login page: {ChoiceConfig.LOGIN_URL}")
        
        wait = WebDriverWait(driver, 20)
        
        # Click SSO button if present
        try:
            logger.info("Looking for SSO button...")
            sso_button = wait.until(EC.element_to_be_clickable((By.ID, "login-with-sso")))
            sso_button.click()
            logger.info("✅ Clicked 'Login with SSO' button")
            time.sleep(2)
        except TimeoutException:
            logger.info("SSO button not found, proceeding with regular login")
        
        # Enter username
        logger.info("Entering credentials...")
        try:
            username_field = wait.until(EC.presence_of_element_located((By.ID, "input28")))
            username_field.clear()
            username_field.send_keys(username)
            logger.info(f"✅ Username entered: {username}")
        except:
            username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']")))
            username_field.clear()
            username_field.send_keys(username)
            logger.info(f"✅ Username entered: {username}")
        
        # Enter password
        try:
            password_field = driver.find_element(By.ID, "input36")
            password_field.clear()
            password_field.send_keys(password)
            logger.info("✅ Password entered")
        except:
            password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
            password_field.clear()
            password_field.send_keys(password)
            logger.info("✅ Password entered")
        
        # Submit login form
        try:
            submit_button = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input.button.button-primary[type='submit']")
            ))
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(0.5)
            
            try:
                submit_button.click()
            except:
                driver.execute_script("arguments[0].click();", submit_button)
            
            logger.info("✅ Submit button clicked")
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"❌ Error clicking submit button: {e}")
            driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}login_submit_error.png')
            return False
        
        # Handle MFA
        logger.info("Selecting verification method...")
        try:
            if verification_type == "PN":
                logger.info("Looking for Push Notification option...")
                
                # First, check if there are multiple push notification options
                try:
                    push_options = driver.find_elements(By.CSS_SELECTOR, "a[aria-label*='push notification']")
                    
                    if len(push_options) > 1:
                        # Multiple options found - display them
                        print("\n" + "="*60)
                        print("MULTIPLE PUSH NOTIFICATION OPTIONS FOUND:")
                        print("="*60)
                        for idx, option in enumerate(push_options, 1):
                            aria_label = option.get_attribute('aria-label')
                            print(f"  {idx}. {aria_label}")
                        print("="*60)
                        
                        # Ask user to select
                        while True:
                            try:
                                choice = input(f"Select option (1-{len(push_options)}): ").strip()
                                choice_idx = int(choice) - 1
                                if 0 <= choice_idx < len(push_options):
                                    selected_option = push_options[choice_idx]
                                    break
                                else:
                                    print(f"Please enter a number between 1 and {len(push_options)}")
                            except ValueError:
                                print("Please enter a valid number")
                        
                        # Click the selected option
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_option)
                        time.sleep(0.5)
                        selected_option.click()
                        logger.info(f"✅ Selected push notification option {choice}")
                        
                    elif len(push_options) == 1:
                        # Only one option - click it automatically
                        push_notification = push_options[0]
                        aria_label = push_notification.get_attribute('aria-label')
                        print(f"\n📱 Using push notification: {aria_label}")
                        push_notification.click()
                        logger.info("✅ Push notification selected")
                    else:
                        # No push notification found
                        logger.error("❌ No push notification options found")
                        driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}no_push_options.png')
                        return False
                    
                except Exception as e:
                    logger.error(f"❌ Error finding push notification options: {e}")
                    driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}push_options_error.png')
                    return False
                
                logger.info("⏳ Awaiting MFA confirmation via push notification...")
                logger.info("   Please approve the notification on your device...")
                print("\n⏳ Waiting for you to approve the push notification on your device...")
                time.sleep(2)
                driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}mfa_push_notification.png')
            else:
                logger.info("Looking for OTP option...")
                otp_option = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button.select-factor.link-button[aria-label*='Okta Verify app']"))
                )
                otp_option.click()
                logger.info("✅ Selected OTP verification method")
                
                print("\n" + "="*60)
                print("MFA REQUIRED: Please enter your One-Time Password (OTP)")
                print("="*60)
                otp_code = input("Enter OTP code: ").strip()
                
                try:
                    otp_input = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "input352"))
                    )
                except:
                    otp_input = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.NAME, "credentials.totp"))
                    )
                
                otp_input.clear()
                otp_input.send_keys(otp_code)
                
                verify_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input.button.button-primary[type='submit'][value='Verify']"))
                )
                verify_button.click()
                logger.info("✅ OTP submitted")
                
        except TimeoutException as e:
            logger.error(f"❌ Timeout waiting for MFA options: {e}")
            logger.error(f"Current URL: {driver.current_url}")
            driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}mfa_timeout_error.png')
            return False
        except Exception as e:
            logger.error(f"❌ Error during MFA: {str(e)}")
            logger.error(f"Current URL: {driver.current_url}")
            driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}mfa_error.png')
            return False
        
        # Wait for successful login
        try:
            logger.info("⏳ Waiting for login to complete...")
            
            WebDriverWait(driver, 130).until(
                lambda d: "choicemax.ideasrms.com" in d.current_url
            )
            logger.info("✅ Login successful!")
            
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(3)
            
            return True
            
        except TimeoutException as e:
            logger.error(f"❌ Login timeout: {e}")
            logger.error(f"Current URL: {driver.current_url}")
            driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}login_timeout_error.png')
            return False
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            logger.error(f"Current URL: {driver.current_url}")
            driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}login_final_error.png')
            return False
        
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        driver.save_screenshot(f'{ChoiceConfig.DOWNLOAD_DIR}login_general_error.png')
        return False


# ============================================================================
# API INTERCEPTION
# ============================================================================

def capture_api_response(driver):
    """
    Capture JSON response from v2?start_date... API call.
    
    Args:
        driver: Selenium WebDriver instance
    
    Returns:
        dict or None: JSON response data
    """
    logger.info("🔍 Waiting for v2?start_date... API call...")
    
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
                        
                        # Check if URL contains 'v2?start_date' or similar patterns
                        if 'v2?start_date' in url or ('v2' in url and 'start_date' in url):
                            logger.info(f"✅ Found API call: {url}")
                            
                            request_id = log['params']['requestId']
                            
                            try:
                                response_body = driver.execute_cdp_cmd(
                                    'Network.getResponseBody',
                                    {'requestId': request_id}
                                )
                                
                                if 'body' in response_body:
                                    json_data = json.loads(response_body['body'])
                                    logger.info(f"✅ Captured JSON response ({len(response_body['body'])} bytes)")
                                    return json_data
                                    
                            except Exception as e:
                                logger.debug(f"Could not get response body for {url}: {e}")
                                continue
                                
                except Exception as e:
                    continue
            
            time.sleep(1)
        
        logger.warning("⚠️ Timeout waiting for v2?start_date... API call")
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
    Process JSON data and save UpdateRecord objects to database.
    
    Args:
        json_data: JSON data from API response
        db_ops: ChoiceDBOperations instance
    
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
                    # Map JSON to UpdateRecord using mapper
                    record = map_json_to_update_record(
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
                        
                        updated_by_rm=False,
                        
                        lyBookingPercent=int(str(date_obj["lyBookingPercent"]))
                        if date_obj.get("lyBookingPercent") is not None else None,
                        
                        lyAdr=Decimal(str(date_obj["lyAdr"]))
                        if date_obj.get("lyAdr") is not None else None,
                        
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
    print("CHOICE HOTELS PRICING SCRAPER")
    print("API Interception Version - V4.0")
    print("=" * 80)
    print()
    
    # Initialize database
    print("🔌 Connecting to database...")
    try:
        db_ops = ChoiceDBOperations()
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Fetch properties
    print("\n📋 Fetching properties to scrape...")
    properties = db_ops.get_active_properties()
    
    if not properties:
        print("❌ No active Choice properties found")
        return
    
    print(f"✅ Found {len(properties)} properties:")
    for idx, prop in enumerate(properties, 1):
        print(f"   {idx}. {prop['hotel_name']} ({prop['property_code']})")
    
    # Get credentials
    username = properties[0]['username']
    password = properties[0]['password']
    
    # Launch browser
    print("\n🌐 Launching browser...")
    driver = None
    
    try:
        driver = create_browser()
        print("✅ Browser launched")
        
        # Login
        print(f"\n🔐 Logging in to Choice MAX as {username}...")
        print("Using Push Notification (PN) for MFA verification...")
        
        verification_type = "PN"
        
        login_success = login_to_choice_max(driver, username, password, verification_type)
        
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
        output_file = os.path.join(os.path.dirname(__file__), "new_record_json.json")
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
