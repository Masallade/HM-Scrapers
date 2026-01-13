# -*- coding: utf-8 -*-
"""
Choice Pricing Trend Scraper - Database Version
Integrated with Laravel hotel revenue management system
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
print("Choice Pricing Trend Scraper - Database Version")
print("=" * 50)

start_date = input("Enter start date (yyyy-mm-dd): ")
ver_type = input("Enter 'PN' for Push Notification verification, else enter 1: ")
days = int(input("Enter number of days to scrape data: "))

# Calculate end date
start_dt = datetime.strptime(start_date, "%Y-%m-%d")
end_dt = start_dt + timedelta(days=days)
end_date = end_dt.strftime("%Y-%m-%d")
print(f"\nDate range: {start_date} to {end_date}")
print(f"Days to scrape: {days}")

# ============== DATABASE SETUP ==============
print("\nConnecting to database...")

# Fetch platforms from database
# NOTE: Change 'Choice Max' to match your platform name in the database
PLATFORM_NAME = 'Choice Max'

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
    
    return driver

# ============== LOGIN FUNCTION ==============
def login_to_choice_max(driver, username, password, ver_type):
    """Handle login to Choice MAX portal"""
    print("Navigating to login portal...")
    driver.get('https://id.ideasrms.com/choice/max?continue=https:%2F%2Fchoicemax.ideasrms.com')
    wait = WebDriverWait(driver, 20)
    
    # Try SSO login first
    try:
        sso_button = wait.until(EC.element_to_be_clickable((By.ID, "login-with-sso")))
        sso_button.click()
        print("Login with SSO")
        time.sleep(2)
    except TimeoutException:
        print("SSO button not found, proceeding with regular login")
    
    # Enter credentials
    print("Entering credentials...")
    try:
    username_input = wait.until(EC.presence_of_element_located((By.ID, "input28")))
    username_input.clear()
    username_input.send_keys(username)
        print(f"✅ Username entered: {username}")
    except Exception as e:
        print(f"❌ Error entering username: {e}")
        driver.save_screenshot("login_username_error.png")
        raise
    
    try:
    password_input = driver.find_element(By.ID, "input36")
    password_input.clear()
    password_input.send_keys(password)
        print("✅ Password entered")
    except Exception as e:
        print(f"❌ Error entering password: {e}")
        driver.save_screenshot("login_password_error.png")
        raise
    
    try:
        # Wait for submit button to be clickable
        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.button.button-primary[type='submit']")))
        # Scroll into view if needed
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(0.5)
        # Click using JavaScript as fallback
        try:
    submit_button.click()
        except:
            driver.execute_script("arguments[0].click();", submit_button)
        print("✅ Submit button clicked")
        # Wait for page to navigate/process
        time.sleep(5)  # Increased wait time
    except Exception as e:
        print(f"❌ Error clicking submit button: {e}")
        driver.save_screenshot("login_submit_error.png")
        raise
    
    # Handle MFA
    print("Selecting verification method...")
    try:
    if ver_type == "PN":
            push_notification = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[aria-label*='push notification']"))
        )
        push_notification.click()
            print("✅ Push notification selected")
        print("Awaiting MFA confirmation via push notification...")
            time.sleep(2)
        driver.save_screenshot("mfa_screenshot.png")
    else:
        # OTP verification
            otp_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button.select-factor.link-button[aria-label*='Okta Verify app']"))
            )
            otp_option.click()
            print("Selected OTP verification method")
            
            otp_rc = input("Enter OTP: ")
            
            try:
                otp_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "input352")))
            except:
                otp_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "credentials.totp")))
            
            otp_input.clear()
            otp_input.send_keys(otp_rc)
            
            verify_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input.button.button-primary[type='submit'][value='Verify']"))
            )
            verify_button.click()
            print("OTP submitted")
    except TimeoutException as e:
        print(f"❌ Timeout waiting for MFA options: {e}")
        print(f"Current URL: {driver.current_url}")
        driver.save_screenshot("mfa_timeout_error.png")
        raise
        except Exception as e:
        print(f"❌ Error during MFA: {str(e)}")
        print(f"Current URL: {driver.current_url}")
        driver.save_screenshot("mfa_error.png")
            raise
    
    # Wait for successful login
    try:
        print("Waiting for login to complete...")
    WebDriverWait(driver, 130).until(lambda d: "choicemax.ideasrms.com" in d.current_url)
        print("✅ Login successful!")
    
    WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(3)
    except TimeoutException as e:
        print(f"❌ Login timeout: {e}")
        print(f"Current URL: {driver.current_url}")
        driver.save_screenshot("login_timeout_error.png")
        raise
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print(f"Current URL: {driver.current_url}")
        driver.save_screenshot("login_final_error.png")
        raise

# ============== SCRAPE DATA FUNCTION ==============
def scrape_property_data(driver, property_id, property_name, property_code, total_inventory, days, start_date):
    """Scrape pricing data for a single property"""
    results = []
    
    # Navigate to Action Manager page (where the AG-Grid with pricing data is located)
    property_url = f"https://choicemax.ideasrms.com/app/properties/{property_id}/action-manager"
    print(f"Navigating to: {property_url}")
    driver.get(property_url)
    
    # Wait for page to load
    print("Waiting for page to load...")
    WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(3)
    
    # Wait for spinner to disappear (Angular app loading)
    print("Waiting for Angular app to load...")
    try:
        WebDriverWait(driver, 30).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ui-spinner"))
        )
        print("✅ Spinner disappeared, app loaded")
    except:
        print("⚠️ Spinner still present, continuing anyway...")
    
    time.sleep(5)
    
    # Wait for calendar data to load
    print("Waiting for calendar data...")
    try:
        # Wait for ui-choice-price elements (these contain the actual pricing data)
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ui-choice-price"))
        )
        print("✅ Calendar data loaded (found pricing elements)")
    except Exception as e:
        print(f"⚠️ Calendar data not loading: {str(e)}")
        driver.save_screenshot(f'calendar_not_loaded_{property_code}.png')
        raise
    
    time.sleep(3)
    
    # Skip date navigation for now - the table should show all available data
    print("Skipping date navigation - will extract from current table view")
    
    # NEW APPROACH: Look for AG-Grid data
    print(f"\nScanning page for AG-Grid pricing data...")
    time.sleep(3)
    
    try:
        # Wait for the System Near Lock section to load
        print("Waiting for System Near Lock section...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "casper-system-near-lock-details"))
        )
        print("✅ System Near Lock section found")
        time.sleep(2)  # Give it a moment to fully render
        
        # Wait for AG-Grid data rows to load (rows with actual data, not headers)
        print("Looking for AG-Grid data rows...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[role='row'][row-index]"))
        )
        
        # Find all data rows in AG-Grid (exclude header rows which don't have row-index)
        ag_rows = driver.find_elements(By.CSS_SELECTOR, "div[role='row'][row-index]")
        print(f"Found {len(ag_rows)} AG-Grid data rows")
        
        if len(ag_rows) == 0:
            print("⚠️ No AG-Grid rows found")
            driver.save_screenshot(f'no_ag_grid_rows_{property_code}.png')
            # Save HTML for debugging
            with open(f'no_ag_grid_{property_code}.html', 'w') as f:
                f.write(driver.page_source)
            return results
        
        # Extract Hotel Level Summary data (this is shared across all rows for the selected date)
        # The summary panel shows data for the currently selected date in the grid
        hotel_summary_data = {}
        try:
            print("\n  Extracting Hotel Level Summary data...")
            # Wait for Hotel Level Summary panel to load
            time.sleep(2)
            
            # Extract Available Rooms
            try:
                available_rooms_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'AVAILABLE ROOMS:')]")
                available_rooms_text = available_rooms_elem.text.strip()
                # Extract number from "AVAILABLE ROOMS: 48"
                available_rooms = int(available_rooms_text.split(':')[1].strip()) if ':' in available_rooms_text else None
                hotel_summary_data['Available Rooms'] = available_rooms
                print(f"    Available Rooms: {available_rooms}")
            except:
                hotel_summary_data['Available Rooms'] = None
                print("    ⚠️ Could not extract Available Rooms")
            
            # Extract Occ. on Books (occupancy)
            try:
                occ_books_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Occ. on Books')]/following-sibling::div[1]")
                occ_books_text = occ_books_elem.text.strip()
                hotel_summary_data['Occ. on Books'] = occ_books_text
                print(f"    Occ. on Books: {occ_books_text}")
            except:
                hotel_summary_data['Occ. on Books'] = None
                print("    ⚠️ Could not extract Occ. on Books")
            
            # Extract Occ. Forecast
            try:
                occ_forecast_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Occ. Forecast')]/following-sibling::div[1]")
                occ_forecast_text = occ_forecast_elem.text.strip()
                hotel_summary_data['Occ. Forecast'] = occ_forecast_text
                print(f"    Occ. Forecast: {occ_forecast_text}")
            except:
                hotel_summary_data['Occ. Forecast'] = None
                print("    ⚠️ Could not extract Occ. Forecast")
            
            # Extract Occ. LY
            try:
                occ_ly_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Occ. LY')]/following-sibling::div[1]")
                occ_ly_text = occ_ly_elem.text.strip()
                hotel_summary_data['Occ. LY'] = occ_ly_text
                print(f"    Occ. LY: {occ_ly_text}")
            except:
                hotel_summary_data['Occ. LY'] = None
                print("    ⚠️ Could not extract Occ. LY")
            
            # Extract ADR
            try:
                adr_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'ADR')]/following-sibling::div[1]")
                adr_text = adr_elem.text.strip()
                hotel_summary_data['ADR'] = adr_text
                print(f"    ADR: {adr_text}")
            except:
                hotel_summary_data['ADR'] = None
                print("    ⚠️ Could not extract ADR")
            
            # Extract Revenue
            try:
                revenue_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Revenue')]/following-sibling::div[1]")
                revenue_text = revenue_elem.text.strip()
                hotel_summary_data['Revenue'] = revenue_text
                print(f"    Revenue: {revenue_text}")
            except:
                hotel_summary_data['Revenue'] = None
                print("    ⚠️ Could not extract Revenue")
            
            # Extract STLY ADR
            try:
                stly_adr_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'STLY ADR')]/following-sibling::div[1]")
                stly_adr_text = stly_adr_elem.text.strip()
                hotel_summary_data['STLY ADR'] = stly_adr_text if stly_adr_text != '-' else None
                print(f"    STLY ADR: {stly_adr_text}")
            except:
                hotel_summary_data['STLY ADR'] = None
                print("    ⚠️ Could not extract STLY ADR")
            
            # Extract Arrivals
            try:
                arrivals_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Arrivals')]/following-sibling::div[1]")
                arrivals_text = arrivals_elem.text.strip()
                hotel_summary_data['Arrivals'] = arrivals_text
                print(f"    Arrivals: {arrivals_text}")
            except:
                hotel_summary_data['Arrivals'] = None
                print("    ⚠️ Could not extract Arrivals")
            
            # Extract Departures
            try:
                departures_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Departures')]/following-sibling::div[1]")
                departures_text = departures_elem.text.strip()
                hotel_summary_data['Departures'] = departures_text
                print(f"    Departures: {departures_text}")
            except:
                hotel_summary_data['Departures'] = None
                print("    ⚠️ Could not extract Departures")
                
        except Exception as e:
            print(f"    ⚠️ Error extracting Hotel Level Summary: {e}")
            # Continue with empty summary data
        
        # Process each AG-Grid row
        for idx, row in enumerate(ag_rows[:days + 1]):  # Limit to requested days
            print(f"\n  Processing row {idx + 1}/{min(len(ag_rows), days + 1)}...")
            try:
                # AG-Grid has pinned columns on the left and center columns
                # We need to get cells from both sections
                # Left pinned section: Date (col-id="0") and Room Class (col-id="1")
                # Center section: Price (col-id="2"), System Price (col-id="3"), etc.
                
                # Get row-index to match cells across sections
                row_index = row.get_attribute("row-index")
                if not row_index:
                    print(f"    ⚠️ Row has no row-index, skipping")
                    continue
                
                # Find all cells in this row (from both pinned and center sections)
                # Look in the entire row container, not just the row element
                cells = row.find_elements(By.CSS_SELECTOR, "div[role='gridcell']")
                
                # Also try to find cells by looking for the row by its index in the grid
                # AG-Grid structure: rows are in containers, cells are in those rows
                if len(cells) < 3:
                    # Try alternative: find cells by looking in the grid body
                    grid_body = driver.find_element(By.CSS_SELECTOR, "div.ag-body-viewport")
                    all_cells_for_row = grid_body.find_elements(
                        By.XPATH, f".//div[@role='row'][@row-index='{row_index}']//div[@role='gridcell']"
                    )
                    if len(all_cells_for_row) > len(cells):
                        cells = all_cells_for_row
                        print(f"    Found {len(cells)} cells using alternative method")
                
                if len(cells) < 3:
                    print(f"    ⚠️ Row {row_index} has only {len(cells)} cells, skipping")
                    # Debug: print what cells we found
                    for i, cell in enumerate(cells):
                        col_id = cell.get_attribute("col-id")
                        text = cell.text.strip()[:50]  # First 50 chars
                        print(f"      Cell {i}: col-id={col_id}, text='{text}'")
                    continue
                
                # Extract data from cells by col-id
                # col-id="0" = Date
                # col-id="1" = Room Class
                # col-id="2" = Price
                # col-id="3" = System Price
                # col-id="4" = Difference
                # col-id="5" = Comp. Avg
                # col-id="6" = Forecast
                
                date_cell = None
                room_class_cell = None
                price_cell = None
                system_price_cell = None
                difference_cell = None
                comp_avg_cell = None
                forecast_cell = None
                
                # Debug: print all cells found
                print(f"    Found {len(cells)} cells for row {row_index}")
                
                for cell in cells:
                    col_id = cell.get_attribute("col-id")
                    cell_text = cell.text.strip()
                    if col_id == "0":
                        date_cell = cell
                        print(f"      Date cell (col-id=0): '{cell_text}'")
                    elif col_id == "1":
                        room_class_cell = cell
                        print(f"      Room Class cell (col-id=1): '{cell_text}'")
                    elif col_id == "2":
                        price_cell = cell
                        print(f"      Price cell (col-id=2): '{cell_text}'")
                    elif col_id == "3":
                        system_price_cell = cell
                        print(f"      System Price cell (col-id=3): '{cell_text}'")
                    elif col_id == "4":
                        difference_cell = cell
                        print(f"      Difference cell (col-id=4): '{cell_text}'")
                    elif col_id == "5":
                        comp_avg_cell = cell
                        print(f"      Comp Avg cell (col-id=5): '{cell_text}'")
                    elif col_id == "6":
                        forecast_cell = cell
                        print(f"      Forecast cell (col-id=6): '{cell_text}'")
                    else:
                        print(f"      Unknown cell (col-id={col_id}): '{cell_text[:30]}'")
                
                # Extract text from cells (AG-Grid cells may have nested elements)
                date_text = date_cell.text.strip() if date_cell and date_cell.text.strip() else "Unknown"
                room_class = room_class_cell.text.strip() if room_class_cell and room_class_cell.text.strip() else "Unknown"
                current_price = price_cell.text.strip() if price_cell and price_cell.text.strip() else None
                system_price = system_price_cell.text.strip() if system_price_cell and system_price_cell.text.strip() else None
                difference = difference_cell.text.strip() if difference_cell and difference_cell.text.strip() else None
                competitor_avg_price = comp_avg_cell.text.strip() if comp_avg_cell and comp_avg_cell.text.strip() else None
                forecast = forecast_cell.text.strip() if forecast_cell and forecast_cell.text.strip() else None
                
                # Validate we have at least Date and Room Class
                if date_text == "Unknown" or room_class == "Unknown":
                    print(f"    ⚠️ Missing essential data (Date or Room Class), skipping row")
                    continue
                
                print(f"    Date: {date_text}, Room: {room_class}, Price: {current_price}, System: {system_price}")
                
                # Parse date and add year
                try:
                    # Extract day of week and date part
                    if "," in date_text:
                        day_of_week, date_only = date_text.split(",", 1)
                        day_of_week = day_of_week.strip()
                        date_only = date_only.strip()
                    else:
                        day_of_week = ""
                        date_only = date_text
                    
                    # Parse the date part (e.g., "Dec 31" or "Jan 04")
                    # and add the year based on start_date
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    start_year = start_dt.year
                    start_month = start_dt.month
                    
                    # Try to parse the date part
                    try:
                        # Try formats like "Dec 31" or "January 31"
                        parsed_date = None
                        for fmt in ["%b %d", "%B %d"]:  # "Dec 31" or "December 31"
                            try:
                                parsed_date = datetime.strptime(date_only.strip(), fmt)
                                break
                            except ValueError:
                                continue
                        
                        if parsed_date:
                            # Determine the year
                            date_month = parsed_date.month
                            date_day = parsed_date.day
                            
                            # If the date month is January and start month is December, it's next year
                            # If the date month is December and start month is January, it's previous year
                            if date_month == 1 and start_month == 12:
                                year = start_year + 1
                            elif date_month == 12 and start_month == 1:
                                year = start_year - 1
                            else:
                                year = start_year
                            
                            # Create full date string for database
                            full_date_str = f"{parsed_date.strftime('%b')} {date_day}, {year}"  # "Dec 31, 2025"
                            date_only = full_date_str
                        else:
                            # If parsing fails, try to use start_date as fallback
                            date_only = start_date
                    except Exception as e:
                        print(f"    ⚠️ Could not parse date '{date_only}': {e}, using start_date")
                        date_only = start_date
                        
                except Exception as e:
                    print(f"    ⚠️ Error parsing date: {e}, using start_date")
                    day_of_week = ""
                    date_only = start_date
                
                # Store data - combine AG-Grid data with Hotel Level Summary data
                data = {
                    "Unlock Price Present": False,  # Not applicable in new UI
                    "Current Price": current_price,
                    "System Price": system_price,
                    "Competitor Avg Price": competitor_avg_price,
                    "Available Rooms": hotel_summary_data.get('Available Rooms'),
                    "Occ. on Books": hotel_summary_data.get('Occ. on Books'),
                    "Occ. on Books LY": None,  # Not shown in UI
                    "Occ. Forecast": hotel_summary_data.get('Occ. Forecast') or forecast,  # Use summary if available, fallback to AG-Grid
                    "Occ. LY": hotel_summary_data.get('Occ. LY'),
                    "ADR": hotel_summary_data.get('ADR'),
                    "STLY ADR": hotel_summary_data.get('STLY ADR'),
                    "Revenue": hotel_summary_data.get('Revenue'),
                    "STLY Revenue": None,  # Not shown in UI
                    "Arrivals": hotel_summary_data.get('Arrivals'),
                    "Departures": hotel_summary_data.get('Departures'),
                    "Full Date": date_text,
                    "Day of Week": day_of_week,
                    "Date Only": date_only,
                    "Property name": property_name,
                    "Property Code": property_code,
                    "Saleable rooms": total_inventory,
                    "Room Class": room_class,
                    "Price Difference": difference
                }
                results.append(data)
                
            except Exception as e:
                print(f"    ❌ Error processing row: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n✅ Extracted {len(results)} records from AG-Grid")
        return results
        
    except Exception as e:
        print(f"❌ Error extracting AG-Grid data: {str(e)}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot(f'ag_grid_error_{property_code}.png')
        # Save HTML for debugging
        with open(f'ag_grid_error_{property_code}.html', 'w') as f:
            f.write(driver.page_source)
        raise


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
    
    try:
        # Create browser
        driver = create_browser()
        
        # Login once for this platform
        print(f"\n🔐 Logging in as: {platform['username']}")
        
        # Get password from database (plain text)
        password = get_password(platform.get('password'))
        if not password:
            raise ValueError(f"No password found in database for platform: {platform['username']}")
        
        # Debug: Confirm password is from database (show first/last char only for security)
        if password:
            masked_password = password[0] + "*" * (len(password) - 2) + password[-1] if len(password) > 2 else "***"
            print(f"✅ Password retrieved from database (length: {len(password)}, masked: {masked_password})")
        
        login_to_choice_max(driver, platform['username'], password, ver_type)
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
                
                # Scrape property data
                property_results = scrape_property_data(
                    driver,
                    property_code,  # Using property_code as platform_property_id
                    hotel_name,
                    property_code,
                    saleable_rooms,
                    days,
                    start_date
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
    csv_filename = f"choice_pricing_backup_{start_date}_to_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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