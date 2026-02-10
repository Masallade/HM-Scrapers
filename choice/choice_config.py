"""
================================================================================
CHOICE HOTEL PRICING SCRAPER - CONFIGURATION MODULE
================================================================================

PURPOSE:
This module centralizes all configuration constants, URLs, selectors, and 
settings for the Choice Hotels pricing scraper. By keeping all configuration
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
    from choice_config import ChoiceConfig
    
    # Access configuration values
    url = ChoiceConfig.BASE_URL
    timeout = ChoiceConfig.DEFAULT_TIMEOUT
================================================================================
"""

# Standard library imports for path operations
import os
from pathlib import Path


class ChoiceConfig:
    """
    Central configuration class for Choice Hotels scraper.
    
    This class uses class variables (not instance variables) so that all
    configuration can be accessed without instantiating the class. This
    follows the Singleton pattern for configuration management.
    """
    
    # ========================================================================
    # CHOICE MAX WEBSITE URLS
    # ========================================================================
    # Base URL for the Choice Hotels MAX revenue management system (IdeasRMS)
    BASE_URL = "https://choicemax.ideasrms.com"
    
    # Login page URL where credentials are submitted (uses IdeasRMS SSO)
    LOGIN_URL = "https://id.ideasrms.com/choice/max?continue=https:%2F%2Fchoicemax.ideasrms.com"
    
    # URL pattern for property pages (use .format(property_code=code))
    PROPERTY_URL_PATTERN = f"{BASE_URL}/app/properties/{{property_code}}"
    
    
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
    DOWNLOAD_DIR = os.path.expanduser("~/Desktop/choice_scraper_downloads/")
    
    # File name patterns to identify downloaded files
    CALENDAR_FILE_PATTERN = "report*.xlsx"  # Calendar exports as report.xlsx
    HISTORICAL_FILE_PATTERN = "report*.xlsx"  # Historical also exports as report.xlsx
    
    # File extensions to look for (in order of preference)
    SUPPORTED_FILE_EXTENSIONS = ['.xlsx', '.xls', '.csv']
    
    
    # ========================================================================
    # WEB ELEMENT SELECTORS (XPath and CSS)
    # ========================================================================
    # These selectors are used to locate elements on the Choice MAX website
    # XPath is preferred for complex hierarchies, CSS for simple selections
    
    # Login page selectors
    LOGIN_USERNAME_FIELD = "input[name='email']"  # CSS selector for email input
    LOGIN_PASSWORD_FIELD = "input[name='password']"  # CSS selector for password input
    LOGIN_SUBMIT_BUTTON = "button[type='submit']"  # CSS selector for login button
    
    # Sidebar navigation selectors
    SIDEBAR_CALENDAR_LINK = "//a[@walkmeid='calendar']"  # XPath for Calendar menu item
    SIDEBAR_REPORTS_LINK = "//a[@walkmeid='reports']"  # XPath for Reports menu item
    SIDEBAR_HISTORICAL_LINK = "//a[contains(text(), 'Historical')]"  # XPath for Historical submenu
    
    # Export button selectors
    EXPORT_BUTTON_TEXT = "Export To Excel"  # Text content of export buttons
    EXPORT_BUTTON_XPATH = f"//button[contains(text(), '{EXPORT_BUTTON_TEXT}')]"
    
    # Date range filter selectors (for Historical reports)
    DATE_FROM_INPUT = "input[placeholder='From']"  # CSS selector for start date
    DATE_TO_INPUT = "input[placeholder='To']"  # CSS selector for end date
    
    
    # ========================================================================
    # CSV COLUMN MAPPINGS
    # ========================================================================
    # These define the exact column names in the downloaded CSV files
    # If Choice Hotels changes their CSV format, update these mappings
    
    # Calendar Grid CSV columns
    CALENDAR_COLUMNS = {
        'hotel_name': 'Hotel Name',
        'date': 'Date',
        'day_of_week': 'Day Of Week',
        'standard_price': 'Standard (Nhk) Price',
        'standard_price_change': 'Standard (Nhk) Price Change',
        'standard_previous_price': 'Standard (Nhk) Previous/System Price',
        'competitor_price': 'Competitor Set Average Price',
        'occupancy': 'Occupancy',
        'forecasted_occupancy': 'Forecasted Occupancy',
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
    
    # Date format for Choice MAX website inputs (mm/dd/yyyy)
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
    LOG_DIR = os.path.expanduser("~/Desktop/choice_scraper_downloads/logs/")
    LOG_FILE = "choice_scraper.log"
    
    # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL = "INFO"
    
    # Log format
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    
    # ========================================================================
    # DATABASE SETTINGS
    # ========================================================================
    # Database table names
    TABLE_PRICING_DATA = "choice_pricing_data"
    TABLE_OLD_RECORDS = "choice_old_records"
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
    def get_property_url(cls, property_code):
        """
        Generate the full URL for a specific property.
        
        Args:
            property_code (str): The property code (e.g., 'PA672')
        
        Returns:
            str: Full URL to the property page
        
        Example:
            >>> ChoiceConfig.get_property_url('PA672')
            'https://max.choicehotels.com/app/properties/PA672'
        """
        # Format the URL pattern with the provided property code
        return cls.PROPERTY_URL_PATTERN.format(property_code=property_code)
    
    
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
ChoiceConfig.ensure_directories_exist()

