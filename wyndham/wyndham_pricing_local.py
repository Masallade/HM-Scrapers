# -*- coding: utf-8 -*-
"""
Wyndham Pricing Trend Scraper - Database Version
Integrated with Laravel hotel revenue management system
Combines pricing trend, historical, and previous day data scraping
"""

import os
import sys
import time
import logging
import random
import tempfile
import json
import pandas as pd
from datetime import datetime, timedelta
import glob

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium_stealth import stealth

# Database imports
from db_operations import (
    get_platforms_for_scraping,
    get_property_details,
    create_scraping_run,
    update_scraping_run,
    update_platform_last_scraped,
    save_pricing_data,
    print_statistics
)

# Password utility import
from password_utils import get_password

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============== USER INPUT ==============
print("=" * 50)
print("Wyndham Pricing Trend Scraper - Database Version")
print("=" * 50)

start_date = input("Enter start date (yyyy-mm-dd): ")
scrape_type = input("Enter 'trend' for pricing trend (calendar/grid) or 'historical' for historical data: ").lower()
if scrape_type not in ['trend', 'historical']:
    scrape_type = 'trend'
    print("Defaulting to 'trend'")

if scrape_type == 'trend':
    days = int(input("Enter number of days to scrape data: "))
    ver_type = input("Enter 'SMS' for SMS OTP verification: ").upper()
    if ver_type != 'SMS':
        ver_type = 'SMS'
        print("Defaulting to 'SMS'")
else:
    # For historical, we need date range
    end_date = input("Enter end date (yyyy-mm-dd): ")
    days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
    ver_type = 'SMS'

# Calculate end date
start_dt = datetime.strptime(start_date, "%Y-%m-%d")
end_dt = start_dt + timedelta(days=days)
end_date = end_dt.strftime("%Y-%m-%d")
print(f"\nDate range: {start_date} to {end_date}")
print(f"Days to scrape: {days}")
print(f"Scrape type: {scrape_type}")

# ============== DATABASE SETUP ==============
print("\nConnecting to database...")

# Fetch platforms from database
PLATFORM_NAME = 'Wyndham'

try:
    platforms = get_platforms_for_scraping(PLATFORM_NAME)
    
    if not platforms:
        print(f"\n❌ No active '{PLATFORM_NAME}' platforms found in database!")
        print("\nPlease check:")
        print("  1. Platform exists in hotel_pms_platforms table")
        print("  2. Platform status is 'active'")
        print("  3. Properties are linked to the platform")
        print("  4. Platform name matches exactly")
        exit(1)
    
    total_properties = sum(p['property_count'] for p in platforms)
    print(f"✅ Found {len(platforms)} platform account(s)")
    print(f"✅ Total properties to scrape: {total_properties}")
    
    # Display platform details
    for idx, platform in enumerate(platforms, 1):
        print(f"\n  Platform {idx}:")
        print(f"    Username: {platform['username']}")
        print(f"    Properties: {platform['property_count']}")
        if platform['property_count'] > 0:
            print(f"    Hotels: {', '.join(platform['hotel_names'][:3])}")
            if platform['property_count'] > 3:
                print(f"            ... and {platform['property_count'] - 3} more")
    
except Exception as e:
    print(f"\n❌ Error connecting to database: {e}")
    print("\nPlease check:")
    print("  1. MySQL server is running")
    print("  2. Database 'hotel_revenue_management' exists")
    print("  3. Database credentials in db_config.py are correct")
    exit(1)


# ============== BROWSER SETUP FUNCTION ==============
def create_browser():
    """Create and configure Chrome browser with stealth settings"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    
    # Set download directory
    download_dir = tempfile.mkdtemp()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # Create temporary profile
    temp_profile = tempfile.mkdtemp()
    options.add_argument(f'--user-data-dir={temp_profile}')
    
    # Random user agent
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    user_agent = random.choice(user_agents)
    options.add_argument(f'user-agent={user_agent}')
    
    # Initialize WebDriver using ChromeDriverManager (auto-downloads correct driver)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    
    # Apply stealth settings
    stealth(driver,
            user_agent=user_agent,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win64",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
    
    return driver, download_dir

# ============== LOGIN FUNCTION ==============
def login_to_wyndham(driver, username, password, last_four_digits=None):
    """Handle login to Wyndham RevIQ portal"""
    print("Navigating to login portal...")
    driver.get('https://id.ideasrms.com/wyndham/reviq?continue=https:%2F%2Freviq.ideasrms.com')
    wait = WebDriverWait(driver, 20)
    
    # Click Wyndham account button
    try:
        wyndham_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.login-button[type='submit']"))
        )
        driver.execute_script("arguments[0].click();", wyndham_button)
        print("✅ Clicked 'Sign in with Wyndham Account' button")
        time.sleep(2)
    except TimeoutException:
        print("⚠️ Wyndham account button not found, proceeding with regular login")
    
    # Enter username
    try:
        username_input = wait.until(EC.presence_of_element_located((By.ID, "input27")))
        username_input.clear()
        username_input.send_keys(username)
        print(f"✅ Username entered: {username}")
    except Exception as e:
        print(f"❌ Error entering username: {e}")
        driver.save_screenshot("login_username_error.png")
        raise
    
    # Click Next
    try:
        next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Next'][data-type='save']")))
        next_button.click()
        print("✅ Clicked Next button")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Error clicking Next: {e}")
        driver.save_screenshot("login_next_error.png")
        raise
    
    # Handle MFA - Select factor by last four digits
    print("Selecting MFA factor...")
    try:
        if last_four_digits:
            element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"a.select-factor[aria-label*='{last_four_digits}']"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.select-factor[aria-label*='{last_four_digits}']")))
            element.click()
            time.sleep(2)
            print(f"✅ Selected MFA factor with last four digits: {last_four_digits}")
        else:
            print("⚠️ No last_four_digits provided, trying to find SMS option directly")
        
        # Click SMS button
        sms_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Receive a code via SMS']"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sms_button)
        sms_button.click()
        print("✅ Clicked 'Receive a code via SMS'")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Error during MFA selection: {e}")
        driver.save_screenshot("mfa_selection_error.png")
        raise
    
    # Get OTP from user
    print("\n*** ACTION REQUIRED: ***")
    print("Please check your device for the OTP code.")
    otp = input("Enter the verification code you received here and press Enter: ").strip()
    print("OTP received. Submitting...")
    
    # Enter OTP
    try:
        otp_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='credentials.passcode']"))
        )
        otp_field.clear()
        otp_field.send_keys(otp)
        print("✅ OTP entered")
    except Exception as e:
        print(f"❌ Error entering OTP: {e}")
        driver.save_screenshot("otp_entry_error.png")
        raise
    
    # Verify OTP
    try:
        verify_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[value="Verify"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", verify_button)
        time.sleep(1)
        verify_button.click()
        print("✅ OTP verification submitted")
        time.sleep(3)
    except Exception as e:
        print(f"❌ Error verifying OTP: {e}")
        driver.save_screenshot("otp_verify_error.png")
        raise
    
    # Wait for successful login
    try:
        wait.until(lambda d: "reviq.ideasrms.com" in d.current_url)
        print("✅ Login successful!")
        WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(3)
    except TimeoutException as e:
        print(f"❌ Timeout waiting for login redirect: {e}")
        print(f"Current URL: {driver.current_url}")
        driver.save_screenshot("login_timeout_error.png")
        raise

# ============== SCRAPE PRICING TREND (CALENDAR/GRID) ==============
def scrape_pricing_trend(driver, property_id, property_name, property_code, total_inventory, days, start_date):
    """Scrape pricing trend data from calendar/grid page"""
    results = []
    
    property_url = f"https://reviq.ideasrms.com/app/properties/{property_id}/calendar/grid"
    print(f"Navigating to: {property_url}")
    driver.get(property_url)
    
    # Wait for page to load
    print("Waiting for page to load...")
    WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(3)
    
    # Click on current date
    try:
        current_date = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[walkmeid='CurrentDate']"))
        )
        driver.execute_script("arguments[0].click();", current_date)
        print("✅ Clicked current date")
        time.sleep(3)
    except Exception as e:
        print(f"⚠️ Could not click current date: {e}")
        driver.save_screenshot(f'current_date_error_{property_code}.png')
    
    # Wait for data container
    try:
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[style='padding: 35px 50px;']"))
        )
        print("✅ Data container found")
    except Exception as e:
        print(f"❌ Data container not found: {e}")
        driver.save_screenshot(f'container_error_{property_code}.png')
        return results
    
    # Loop through days
    for i in range(int(days)):
        data = {}
        print(f"\n  Processing day {i + 1}/{days}...")
        
        try:
            # 1. Standard Price
            try:
                standard_price = container.find_element(By.CSS_SELECTOR, "span.price--big").text.strip()
                data['Standard Price'] = standard_price.replace('$', '').replace(',', '').strip()
            except:
                data['Standard Price'] = None
            
            # 2. OTB Percentage (Occupancy)
            try:
                otb_percentage = container.find_element(
                    By.XPATH, ".//div[contains(@class, 'otb')]//div[contains(@class, 'text--inline fs-20')]"
                ).text.strip()
                data['OTB Percentage'] = otb_percentage.replace('%', '').strip()
            except:
                data['OTB Percentage'] = None
            
            # 3. OTB STLY Change
            try:
                try:
                    otb_stly_change = container.find_element(
                        By.XPATH, ".//div[contains(@class, 'otb')]//span[@class='down']"
                    ).text.strip()
                    data['OTB STLY Change'] = otb_stly_change.replace('%', '').replace('+', '').strip()
                except:
                    otb_stly_change = container.find_element(
                        By.XPATH, ".//div[contains(@class, 'otb')]//span[@class='']"
                    ).text.strip()
                    data['OTB STLY Change'] = '-' + otb_stly_change.replace('%', '').replace('-', '').strip()
            except:
                data['OTB STLY Change'] = None
            
            # 4. Average Price (Competitor)
            try:
                avg_price = container.find_element(
                    By.XPATH, ".//div[contains(text(), 'Average price')]/following-sibling::div//div[contains(@class, 'd-flex')]"
                ).text.strip()
                data['Average Price'] = avg_price.replace('$', '').replace(',', '').strip()
            except:
                data['Average Price'] = None
            
            # 5. ADR
            try:
                adr = container.find_element(
                    By.XPATH, ".//div[contains(text(), 'Average Daily Rate')]/following-sibling::div//ui-choice-price/span"
                ).text.strip()
                data['ADR'] = adr.replace('$', '').replace(',', '').strip()
            except:
                data['ADR'] = None
            
            # 6. ADR STLY Change
            try:
                adr_block = driver.find_element(
                    By.XPATH, "//div[contains(@class,'data--item__name') and normalize-space()='Average Daily Rate']/following-sibling::div"
                )
                adr_value = adr_block.find_element(By.CSS_SELECTOR, "div.body--price span").text.strip()
                data['ADR'] = adr_value.replace('$', '').replace(',', '').strip()
                
                try:
                    stly_elem = adr_block.find_element(By.XPATH, ".//span[contains(text(),'STLY')]/preceding-sibling::span")
                    stly_value = stly_elem.text.strip()
                    if "down" in stly_elem.get_attribute("class"):
                        data['ADR STLY Change'] = stly_value.replace('$', '').replace(',', '').strip()
                    else:
                        data['ADR STLY Change'] = '-' + stly_value.replace('$', '').replace(',', '').replace('-', '').strip()
                except:
                    data['ADR STLY Change'] = None
            except:
                data['ADR STLY Change'] = None
            
            # 7. Revenue OTB
            try:
                revenue = container.find_element(
                    By.XPATH, ".//div[contains(text(), 'Revenue OTB')]/following-sibling::div//ui-choice-price/span"
                ).text.strip()
                data['Revenue OTB'] = revenue.replace('$', '').replace(',', '').strip()
            except:
                data['Revenue OTB'] = None
            
            # 8. Revenue STLY Change
            try:
                revenue_block = driver.find_element(
                    By.XPATH, "//div[contains(@class,'data--item__name') and normalize-space()='Revenue OTB']/following-sibling::div"
                )
                try:
                    stly_elem = revenue_block.find_element(By.XPATH, ".//span[contains(text(),'STLY')]/preceding-sibling::span")
                    stly_value = stly_elem.text.strip()
                    if "down" in stly_elem.get_attribute("class"):
                        data['Revenue STLY Change'] = stly_value.replace('$', '').replace(',', '').strip()
                    else:
                        data['Revenue STLY Change'] = '-' + stly_value.replace('$', '').replace(',', '').replace('-', '').strip()
                except:
                    data['Revenue STLY Change'] = None
            except:
                data['Revenue STLY Change'] = None
            
            # 9. OTB Rooms
            try:
                data['OTB Rooms'] = container.find_element(
                    By.XPATH, ".//div[contains(text(), 'OTB rooms')]/following-sibling::div"
                ).text.strip()
            except:
                data['OTB Rooms'] = None
            
            # 10. Available Rooms
            try:
                data['Available Rooms'] = container.find_element(
                    By.XPATH, ".//div[contains(text(), 'Avl. rooms')]/following-sibling::div"
                ).text.strip()
            except:
                data['Available Rooms'] = None
            
            # 11. OOO Rooms
            try:
                data['OOO Rooms'] = container.find_element(
                    By.XPATH, ".//div[contains(text(), 'ooo')]/following-sibling::div"
                ).text.strip()
            except:
                data['OOO Rooms'] = None
            
            # 12. Total Rooms
            try:
                data['Total Rooms'] = container.find_element(
                    By.XPATH, ".//div[contains(text(), 'Total rooms')]/following-sibling::div"
                ).text.strip()
            except:
                data['Total Rooms'] = None
            
            # 13. Forecast
            try:
                forecast = container.find_element(
                    By.XPATH, ".//div[contains(@class, 'forecast')]//div[contains(@class, 'text--inline__light mr-3')]"
                ).text.strip()
                data['Forecast'] = forecast.replace('%', '').strip()
            except:
                data['Forecast'] = None
            
            # 14. Date
            try:
                date_block = driver.find_element(
                    By.XPATH, "//em[contains(@class,'iconChevron nextDay')]/parent::div"
                )
                date_elem = date_block.find_element(By.CSS_SELECTOR, "div.date")
                date_text = date_elem.text.strip()  # e.g. "Mon, 01 Sep, 2025"
                
                # Parse date
                try:
                    parsed_date = datetime.strptime(date_text, "%a, %d %b, %Y")
                    date_only = parsed_date.strftime("%Y-%m-%d")
                    day_of_week = parsed_date.strftime("%A")
                except:
                    date_only = start_date
                    day_of_week = ""
            except:
                date_text = start_date
                date_only = start_date
                day_of_week = ""
            
            # Map to database schema
            mapped_data = {
                "Unlock Price Present": False,
                "Current Price": data.get('Standard Price'),
                "System Price": None,
                "Competitor Avg Price": data.get('Average Price'),
                "Available Rooms": data.get('Available Rooms'),
                "Occ. on Books": data.get('OTB Percentage'),
                "Occ. on Books LY": None,
                "Occ. Forecast": data.get('Forecast'),
                "Occ. LY": None,
                "ADR": data.get('ADR'),
                "STLY ADR": data.get('ADR STLY Change'),
                "Revenue": data.get('Revenue OTB'),
                "STLY Revenue": data.get('Revenue STLY Change'),
                "Full Date": date_text if 'date_text' in locals() else start_date,
                "Day of Week": day_of_week,
                "Date Only": date_only,
                "Property name": property_name,
                "Property Code": property_code,
                "Saleable rooms": total_inventory or data.get('Total Rooms'),
                "Room Class": None,
                "Price Difference": None
            }
            
            results.append(mapped_data)
            
            # Click next day button
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "em.iconChevron.nextDay")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)
            except:
                print(f"    ⚠️ Could not click next day button")
                break
                
        except Exception as e:
            print(f"    ❌ Error processing day {i + 1}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n✅ Extracted {len(results)} records from pricing trend")
    return results

# ============== SCRAPE HISTORICAL DATA ==============
def scrape_historical_data(driver, download_dir, property_id, property_name, property_code, total_inventory, start_date, end_date):
    """Scrape historical data from reports/historical page (exports Excel)"""
    results = []
    
    property_url = f"https://reviq.ideasrms.com/app/properties/{property_id}/reports/historical"
    print(f"Navigating to: {property_url}")
    driver.get(property_url)
    time.sleep(5)
    
    # Set date range
    try:
        date_input = driver.find_element(By.CLASS_NAME, "datepicker")
        date_input.send_keys(Keys.CONTROL + "a")
        date_input.send_keys(Keys.DELETE)
        date_range = f"{start_date} - {end_date}"
        date_input.send_keys(date_range)
        date_input.send_keys(Keys.TAB)
        print(f"✅ Date range set: {date_range}")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Could not set date range: {e}")
        driver.save_screenshot(f'date_range_error_{property_code}.png')
    
    # Click Export To Excel
    try:
        export_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Export To Excel']"))
        )
        export_btn.click()
        print("✅ Export button clicked")
        time.sleep(5)
    except Exception as e:
        print(f"❌ Could not find Export button: {e}")
        driver.save_screenshot(f'export_error_{property_code}.png')
        return results
    
    # Wait for file download
    print("Waiting for Excel file to download...")
    timeout = 90
    file_found = False
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        list_of_files = glob.glob(f"{download_dir}/*.xlsx")
        if list_of_files:
            latest_file = max(list_of_files, key=os.path.getctime)
            print(f"✅ File downloaded: {latest_file}")
            file_found = True
            break
        time.sleep(1)
    
    if not file_found:
        print("❌ Excel file not found within timeout period")
        return results
    
    # Read Excel file
    try:
        df = pd.read_excel(latest_file, header=0)
        column_names = df.columns.tolist()
        df = pd.read_excel(latest_file, header=None, skiprows=1, names=column_names)
        
        # Extract first row (most recent data)
        if len(df) > 0:
            row = df.iloc[0]
            
            # Map Excel columns to database schema
            mapped_data = {
                "Unlock Price Present": False,
                "Current Price": None,
                "System Price": None,
                "Competitor Avg Price": None,
                "Available Rooms": None,
                "Occ. on Books": None,
                "Occ. on Books LY": None,
                "Occ. Forecast": None,
                "Occ. LY": None,
                "ADR": None,
                "STLY ADR": None,
                "Revenue": None,
                "STLY Revenue": None,
                "Full Date": start_date,
                "Day of Week": "",
                "Date Only": start_date,
                "Property name": property_name,
                "Property Code": property_code,
                "Saleable rooms": total_inventory,
                "Room Class": None,
                "Price Difference": None
            }
            
            # Map Excel columns (adjust based on actual Excel structure)
            # This is a placeholder - you'll need to adjust based on actual Excel columns
            for col in df.columns:
                col_lower = str(col).lower()
                if 'price' in col_lower:
                    mapped_data['Current Price'] = str(row[col]) if pd.notna(row[col]) else None
                elif 'occupancy' in col_lower or 'otb' in col_lower:
                    mapped_data['Occ. on Books'] = str(row[col]) if pd.notna(row[col]) else None
                elif 'revenue' in col_lower:
                    mapped_data['Revenue'] = str(row[col]) if pd.notna(row[col]) else None
                elif 'adr' in col_lower:
                    mapped_data['ADR'] = str(row[col]) if pd.notna(row[col]) else None
                elif 'date' in col_lower:
                    try:
                        date_val = pd.to_datetime(row[col])
                        mapped_data['Date Only'] = date_val.strftime("%Y-%m-%d")
                        mapped_data['Day of Week'] = date_val.strftime("%A")
                    except:
                        pass
            
            results.append(mapped_data)
            print(f"✅ Extracted 1 record from historical data")
        
        # Clean up downloaded file
        try:
            os.remove(latest_file)
            print(f"✅ Removed downloaded file")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        import traceback
        traceback.print_exc()
    
    return results

# ============== MAIN EXECUTION ==============
print("\n" + "=" * 50)
print("Starting Scraping Process...")
print("=" * 50)

all_results = []
successful_runs = 0
failed_runs = 0

# Process each platform (automatically grouped by credentials)
for platform_idx, platform in enumerate(platforms, 1):
    print(f"\n{'='*60}")
    print(f"Platform {platform_idx}/{len(platforms)}: {platform['username']}")
    print(f"Properties: {platform['property_count']}")
    print(f"{'='*60}")
    
    driver = None
    download_dir = None
    
    try:
        # Create browser
        driver, download_dir = create_browser()
        
        # Login once for this platform
        print(f"\n🔐 Logging in as: {platform['username']}")
        
        # Get password from database (plain text)
        password = get_password(platform.get('password'))
        if not password:
            raise ValueError(f"No password found in database for platform: {platform['username']}")
        
        # Get last_four_digits from config if available
        config = platform.get('config')
        last_four_digits = None
        if config:
            try:
                config_dict = json.loads(config) if isinstance(config, str) else config
                last_four_digits = config_dict.get('last_four_digits')
            except:
                pass
        
        # Debug: Confirm password is from database
        if password:
            masked_password = password[0] + "*" * (len(password) - 2) + password[-1] if len(password) > 2 else "***"
            print(f"✅ Password retrieved from database (length: {len(password)}, masked: {masked_password})")
        
        login_to_wyndham(driver, platform['username'], password, last_four_digits)
        print("✅ Login successful!")
        
        # Scrape each property linked to this platform
        for prop_idx in range(platform['property_count']):
            property_id = platform['property_ids'][prop_idx]
            property_code = platform['property_codes'][prop_idx]
            hotel_name = platform['hotel_names'][prop_idx]
            
            print(f"\n{'─'*60}")
            print(f"[{prop_idx + 1}/{platform['property_count']}] Scraping: {hotel_name}")
            print(f"{'─'*60}")
            
            # Create scraping run record
            run_id = create_scraping_run(
                platform['platform_id'],
                start_date,
                end_date,
                days
            )
            
            if not run_id:
                print(f"❌ Failed to create scraping run record")
                failed_runs += 1
                continue
            
            try:
                # Get property details for saleable rooms
                property_details = get_property_details(property_id)
                saleable_rooms = property_details.get('saleable_rooms', 0) if property_details else 0
                
                # Scrape property data based on type
                if scrape_type == 'trend':
                    property_results = scrape_pricing_trend(
                        driver,
                        property_id,
                        hotel_name,
                        property_code,
                        saleable_rooms,
                        days,
                        start_date
                    )
                else:  # historical
                    property_results = scrape_historical_data(
                        driver,
                        download_dir,
                        property_id,
                        hotel_name,
                        property_code,
                        saleable_rooms,
                        start_date,
                        end_date
                    )
                
                if property_results:
                    # Save to database
                    print(f"💾 Saving {len(property_results)} records to database...")
                    saved_count = save_pricing_data(run_id, property_id, property_results)
                    
                    if saved_count > 0:
                        # Update scraping run as completed
                        update_scraping_run(run_id, 'completed', saved_count)
                        all_results.extend(property_results)
                        successful_runs += 1
                        print(f"✅ Success! Saved {saved_count} records")
                    else:
                        update_scraping_run(run_id, 'failed', 0, 'No records saved')
                        failed_runs += 1
                        print(f"⚠️  Warning: No records were saved")
                else:
                    update_scraping_run(run_id, 'failed', 0, 'No data scraped')
                    failed_runs += 1
                    print(f"⚠️  Warning: No data was scraped")
            
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Error scraping {hotel_name}: {error_msg}")
                
                # Update scraping run as failed
                update_scraping_run(run_id, 'failed', 0, error_msg)
                failed_runs += 1
                
                # Save error screenshot
                try:
                    driver.save_screenshot(f'error_{property_code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                except:
                    pass
                
                continue
        
        # Update platform last scraped timestamp
        update_platform_last_scraped(platform['platform_id'])
        print(f"\n✅ Completed all properties for platform: {platform['username']}")
            
    except Exception as e:
        print(f"\n❌ Login failed for {platform['username']}: {str(e)}")
        
        # Mark all properties as failed for this platform
        for prop_idx in range(platform['property_count']):
            property_id = platform['property_ids'][prop_idx]
            run_id = create_scraping_run(platform['platform_id'], start_date, end_date, days)
            if run_id:
                update_scraping_run(run_id, 'failed', 0, f"Login failed: {str(e)}")
        
        failed_runs += platform['property_count']
        
        # Save error screenshot
        try:
            if driver:
                driver.save_screenshot(f'error_login_{platform["username"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        except:
            pass
    
    finally:
        # Close browser
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        print(f"\n{'='*60}")
        print(f"Platform {platform_idx} completed")
        print(f"{'='*60}")

# ============== FINAL SUMMARY ==============
print("\n" + "=" * 70)
print("SCRAPING COMPLETED!")
print("=" * 70)

print(f"\n📊 Summary:")
print(f"  Total Platforms: {len(platforms)}")
print(f"  Total Properties: {sum(p['property_count'] for p in platforms)}")
print(f"  Successful Runs: {successful_runs}")
print(f"  Failed Runs: {failed_runs}")
print(f"  Total Records: {len(all_results)}")

if all_results:
    # Optional: Save to CSV for backup
    results_df = pd.DataFrame(all_results)
    csv_filename = f"wyndham_pricing_backup_{start_date}_to_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df.to_csv(csv_filename, index=False)
    print(f"\n💾 Backup CSV saved: {csv_filename}")
    
    # Display data summary
    print(f"\n📈 Data Summary:")
    print(f"  Date Range: {results_df['Date Only'].min()} to {results_df['Date Only'].max()}")
    print(f"  Properties: {results_df['Property name'].nunique()}")
    print(f"  Total Days: {results_df['Date Only'].nunique()}")

# Print database statistics
print("\n" + "=" * 70)
print("DATABASE STATISTICS")
print("=" * 70)
print_statistics()

print("\n" + "=" * 70)
print("✅ Script completed successfully!")
print("=" * 70)
print("\n💡 Next Steps:")
print("  1. Check your Laravel application to view the scraped data")
print("  2. Review scraping_runs table for detailed run information")
print("  3. Check update_records table for pricing data")
print("=" * 70)

