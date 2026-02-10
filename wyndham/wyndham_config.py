"""
================================================================================
WYNDHAM HOTEL PRICING SCRAPER - CONFIGURATION MODULE
================================================================================

PURPOSE:
This module centralizes all configuration constants, URLs, selectors, and 
settings for the Wyndham Hotels pricing scraper. By keeping all configuration
in one place, we make the codebase easier to maintain, update, and debug.

PROBLEM IT SOLVES:
- Eliminates hardcoded values scattered throughout the codebase
- Makes it easy to update URLs, timeouts, and selectors in one place
- Provides clear documentation of all configurable parameters
- Enables easy switching between environments (dev/staging/production)

ROLE IN THE SYSTEM:
This is the central configuration hub that other modules import from. Any
changes to URLs, timeouts, file paths, or web element selectors should be
made here rather than in the main scraper code.

USAGE:
    from wyndham_config import WyndhamConfig
    
    # Access configuration values
    url = WyndhamConfig.BASE_URL
    timeout = WyndhamConfig.DEFAULT_TIMEOUT
================================================================================
"""

# Standard library imports for path operations
import os
from pathlib import Path


class WyndhamConfig:
    """
    Central configuration class for Wyndham Hotels scraper.
    
    This class uses class variables (not instance variables) so that all
    configuration can be accessed without instantiating the class. This
    follows the Singleton pattern for configuration management.
    """
    
    # ========================================================================
    # WYNDHAM REVIQ WEBSITE URLS
    # ========================================================================
    # Base URL for the Wyndham RevIQ revenue management system (IdeasRMS)
    BASE_URL = "https://reviq.ideasrms.com"
    
    # Login page URL where credentials are submitted (uses IdeasRMS SSO)
    LOGIN_URL = "https://id.ideasrms.com/wyndham/reviq?continue=https:%2F%2Freviq.ideasrms.com"
    
    # URL pattern for property calendar pages (use .format(property_id=id))
    # NOTE: Wyndham uses property_id (numeric) instead of property_code
    # Changed to /calendar/list to scrape room inventory data from List view
    PROPERTY_CALENDAR_URL_PATTERN = f"{BASE_URL}/app/properties/{{property_id}}/calendar/list"
    
    
    # ========================================================================
    # WEB DRIVER SETTINGS
    # ========================================================================
    # Maximum time (seconds) to wait for page elements to load
    DEFAULT_TIMEOUT = 30
    
    # Time (seconds) to wait for page to stabilize after navigation
    PAGE_LOAD_WAIT = 3
    
    # Time (seconds) to wait for file downloads to complete
    DOWNLOAD_WAIT = 10
    
    # Maximum time (seconds) to wait for a file download
    MAX_DOWNLOAD_WAIT = 60
    
    # Implicit wait time (seconds) for element searches
    IMPLICIT_WAIT = 10
    
    
    # ========================================================================
    # FILE DOWNLOAD SETTINGS
    # ========================================================================
    # Directory where CSV files will be downloaded (on user's Desktop)
    # Using expanduser to handle ~ (home directory) cross-platform
    DOWNLOAD_DIR = os.path.expanduser("~/Desktop/wyndham_scraper_downloads/")
    
    # File name patterns to identify downloaded files
    CALENDAR_FILE_PATTERN = "report*.xlsx"  # Calendar exports as report.xlsx
    HISTORICAL_FILE_PATTERN = "report*.xlsx"  # Historical also exports as report.xlsx
    
    # File extensions to look for (in order of preference)
    SUPPORTED_FILE_EXTENSIONS = ['.xlsx', '.xls', '.csv']
    
    
    # ========================================================================
    # WEB ELEMENT SELECTORS (XPath and CSS)
    # ========================================================================
    # These selectors are used to locate elements on the Wyndham RevIQ website
    # XPath is preferred for complex hierarchies, CSS for simple selections
    
    # Login page selectors
    LOGIN_WYNDHAM_BUTTON = "button.login-button[type='submit']"  # CSS selector for Wyndham account button
    LOGIN_USERNAME_FIELD_ID = "input27"  # ID for username input field
    LOGIN_NEXT_BUTTON = "input[value='Next'][data-type='save']"  # CSS selector for Next button
    LOGIN_SMS_BUTTON = "//input[@value='Receive a code via SMS']"  # XPath for SMS OTP option
    LOGIN_OTP_FIELD = "input[name='credentials.passcode']"  # CSS selector for OTP input
    LOGIN_VERIFY_BUTTON = 'input[value="Verify"]'  # CSS selector for Verify button
    
    # Sidebar navigation selectors
    # Calendar menu item: The SVG inside the menu item has walkmeid="CalendarMenu"
    # We click the parent <a> or <div> element that contains the SVG, not the SVG itself
    # Primary: Find the <a> tag that contains the SVG with walkmeid="CalendarMenu"
    SIDEBAR_CALENDAR_LINK = "//svg[@walkmeid='CalendarMenu']/ancestor::a[1]"  # Parent <a> tag containing Calendar SVG
    # Fallback selectors for Calendar menu item
    SIDEBAR_CALENDAR_LINK_FALLBACK_1 = "//svg[@walkmeid='CalendarMenu']/ancestor::div[contains(@class, 'menu__item')][1]"  # Parent div with menu__item class
    SIDEBAR_CALENDAR_LINK_FALLBACK_2 = "//a[contains(@href, '/calendar')]"  # Any link with /calendar in href
    SIDEBAR_CALENDAR_LINK_FALLBACK_3 = "//div[contains(@class, 'menu__item')]//svg[@walkmeid='CalendarMenu']/ancestor::a[1]"  # More specific path to <a>
    SIDEBAR_REPORTS_LINK = "//a[@walkmeid='reports']"  # XPath for Reports menu item
    SIDEBAR_HISTORICAL_LINK = "//a[contains(text(), 'Historical')]"  # XPath for Historical submenu
    
    # Export button selectors (Wyndham-specific UI)
    # Wyndham uses a div with walkmeid="ExportToExcel" instead of a button
    EXPORT_BUTTON_WALKMEID = "ExportToExcel"  # walkmeid attribute for export button
    EXPORT_BUTTON_XPATH_WALKMEID = f"//div[@walkmeid='{EXPORT_BUTTON_WALKMEID}']"  # Primary selector
    EXPORT_BUTTON_XPATH_CLASS = "//div[contains(@class, 'export-btn')]"  # Fallback by class
    EXPORT_BUTTON_TEXT = "Export To Excel"  # Text content for text-based fallback
    EXPORT_BUTTON_XPATH_TEXT = f"//div[contains(text(), '{EXPORT_BUTTON_TEXT}')]"  # Text-based fallback
    
    # Date range filter selectors (for Historical reports)
    DATE_FROM_INPUT = "input[placeholder='From']"  # CSS selector for start date
    DATE_TO_INPUT = "input[placeholder='To']"  # CSS selector for end date
    
    # Calendar List page selectors (for room inventory scraping)
    # Expand All button - expands all date rows to show room inventory data
    EXPAND_ALL_BUTTON_XPATH = "//button[.//small[contains(text(), 'Expand All')]]"  # Button containing "Expand All" text
    EXPAND_ALL_BUTTON_FALLBACK = "//small[contains(text(), 'Expand All')]/ancestor::button[1]"  # Fallback selector
    
    # Date extraction selectors (from Calendar List page)
    DATE_DAY_MONTH_XPATH = "//div[contains(@class, 'date__day')]"  # Month abbreviation (Jan, Feb, etc.)
    DATE_DAY_NUMBER_XPATH = "//div[contains(@class, 'date__number')]//span[1]"  # Day number (1-31)
    DATE_DAY_WEEK_XPATH = "//div[contains(@class, 'date__number')]//span[2]"  # Day of week (Mon, Tue, etc.)
    
    # Room inventory selectors (from Calendar List page expanded rows)
    TOTAL_ROOMS_XPATH = "//div[contains(@class, 'chart--header') and contains(text(), 'Total rooms')]/following-sibling::div[1]"  # Total rooms value
    OOO_ROOMS_XPATH = "//div[contains(@class, 'progress--ooo')]//div[contains(@class, 'lower-popup')]/div[contains(@class, 'text-uppercase') and contains(text(), 'ooo')]/following-sibling::div[1]"  # Out of order rooms
    OTB_ROOMS_XPATH = "//div[contains(@class, 'progress--otb')]//div[contains(@class, 'lower-popup')]/div[contains(text(), 'OTB rooms')]/following-sibling::div[1]"  # On the books rooms
    AVL_ROOMS_XPATH = "//div[contains(@class, 'progress--all')]//div[contains(@class, 'inverted-lower-popup')]/div[contains(text(), 'Avl. rooms')]/following-sibling::div[1]"  # Available rooms
    
    
    # ========================================================================
    # CSV COLUMN MAPPINGS
    # ========================================================================
    # These define the exact column names in the downloaded CSV files
    # If Wyndham Hotels changes their CSV format, update these mappings
    
    # Calendar Grid CSV columns
    # NOTE: Wyndham has updated their column names. We support both old and new formats.
    # New column names (current):
    # - 'Base Room Price' (was 'Standard (Nhk) Price')
    # - 'Base Room Previous/system Price' (was 'Standard (Nhk) Previous/System Price')
    # - 'On The Books %' (was 'Occupancy')
    # - 'Forecast Rooms' (was 'Forecasted Occupancy')
    CALENDAR_COLUMNS = {
        'hotel_name': 'Hotel Name',
        'date': 'Date',
        'day_of_week': 'Day Of Week',
        # Price columns - support both old and new names
        'standard_price': 'Base Room Price',  # New name (was 'Standard (Nhk) Price')
        'standard_price_old': 'Standard (Nhk) Price',  # Old name for backward compatibility
        'standard_price_change': 'Standard (Nhk) Price Change',
        'standard_previous_price': 'Base Room Previous/system Price',  # New name (note: lowercase 's' in 'system')
        'standard_previous_price_old': 'Standard (Nhk) Previous/System Price',  # Old name
        'standard_previous_price_old2': 'Standard (Nhk) Previous/system Price',  # Old name variant
        'competitor_price': 'Competitor Set Average Price',
        # Occupancy columns - support both old and new names
        'occupancy': 'On The Books %',  # New name (was 'Occupancy')
        'occupancy_old': 'Occupancy',  # Old name for backward compatibility
        'forecasted_occupancy': 'Forecast Rooms',  # New name (was 'Forecasted Occupancy')
        'forecasted_occupancy_old': 'Forecasted Occupancy',  # Old name for backward compatibility
        'lrv': 'LRV',
        'overbooking_level': 'Overbooking Level',
        'arrivals_forecast': 'Arrivals Forecast',
        'departures_forecast': 'Departures Forecast',
    }
    
    
    # ========================================================================
    # DATE FORMAT SETTINGS
    # ========================================================================
    # Date formats used in CSV files and database
    CSV_DATE_FORMAT_1 = "%d/%m/%Y"  # Format: 15/01/2026 (DD/MM/YYYY)
    CSV_DATE_FORMAT_2 = "%Y-%m-%d"  # Format: 2026-01-15 (YYYY-MM-DD)
    CSV_DATE_FORMAT_3 = "%Y-%m-%d %H:%M:%S"  # Format: 2026-01-15 00:00:00 (Excel timestamp)
    
    # Date format for database storage
    DB_DATE_FORMAT = "%Y-%m-%d"  # MySQL DATE format
    
    # Date format for Wyndham RevIQ website inputs (mm/dd/yyyy)
    WEBSITE_DATE_FORMAT = "%m/%d/%Y"  # Format: 01/15/2026
    
    
    # ========================================================================
    # BUSINESS LOGIC SETTINGS
    # ========================================================================
    # Default number of saleable rooms if not found in database
    # This is a fallback value based on typical property size
    DEFAULT_SALEABLE_ROOMS = 66
    
    # Number of days to scrape (forward from today)
    SCRAPE_DAYS_AHEAD = 365  # One year of forward-looking data
    
    # Number of days to look back for historical comparison
    HISTORICAL_LOOKBACK_DAYS = 365  # Match same date last year
    
    
    # ========================================================================
    # LOGGING SETTINGS
    # ========================================================================
    # Log file location
    LOG_DIR = os.path.expanduser("~/Desktop/wyndham_scraper_downloads/logs/")
    LOG_FILE = "wyndham_scraper.log"
    
    # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL = "INFO"
    
    # Log format
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    
    # ========================================================================
    # DATABASE SETTINGS
    # ========================================================================
    # Database table names
    TABLE_PRICING_DATA = "update_records"  # Same table as Choice (update_records)
    TABLE_OLD_RECORDS = "wyndham_old_records"  # Historical data table for Wyndham
    TABLE_PROPERTIES = "properties"
    TABLE_PROPERTIES_CHARACTERISTICS = "properties_characteristics_history"
    TABLE_SCRAPING_RUNS = "scraping_runs"
    
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @classmethod
    def ensure_directories_exist(cls):
        """
        Create necessary directories if they don't exist.
        
        This method ensures that the download directory and log directory
        are created before the scraper runs. This prevents FileNotFoundError
        when trying to save files.
        
        Returns:
            None
        """
        # Create download directory if it doesn't exist
        Path(cls.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
        
        # Create log directory if it doesn't exist
        Path(cls.LOG_DIR).mkdir(parents=True, exist_ok=True)
    
    
    @classmethod
    def get_property_calendar_url(cls, property_id):
        """
        Generate the full URL for a specific property's calendar page.
        
        Args:
            property_id (int): The property database ID (e.g., 123)
        
        Returns:
            str: Full URL to the property calendar page
        
        Example:
            >>> WyndhamConfig.get_property_calendar_url(123)
            'https://reviq.ideasrms.com/app/properties/123/calendar/grid'
        """
        # Format the URL pattern with the provided property ID
        return cls.PROPERTY_CALENDAR_URL_PATTERN.format(property_id=property_id)
    
    
    @classmethod
    def get_log_file_path(cls):
        """
        Get the full path to the log file.
        
        Returns:
            str: Full path to the log file
        """
        # Combine log directory and log file name
        return os.path.join(cls.LOG_DIR, cls.LOG_FILE)


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================
# Ensure all required directories exist when this module is imported
WyndhamConfig.ensure_directories_exist()
