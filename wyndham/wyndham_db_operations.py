"""
================================================================================
WYNDHAM HOTEL PRICING SCRAPER - DATABASE OPERATIONS MODULE
================================================================================

PURPOSE:
This module handles all database interactions for the Wyndham Hotels pricing
scraper. It provides a clean, reusable interface for reading property data,
fetching historical records, and saving scraped pricing information.

PROBLEM IT SOLVES:
- Centralizes all database logic in one place
- Prevents SQL injection through parameterized queries
- Handles database connections and error management
- Provides transaction support for data integrity
- Makes database operations testable and maintainable

ROLE IN THE SYSTEM:
This module acts as the Data Access Layer (DAL) between the scraper and the
MySQL database. All database queries, inserts, and updates flow through this
module, ensuring consistent data handling and error management.

USAGE:
    from wyndham_db_operations import WyndhamDBOperations
    
    # Initialize database operations
    db_ops = WyndhamDBOperations()
    
    # Get properties to scrape
    properties = db_ops.get_active_properties()
    
    # Save pricing data
    db_ops.save_pricing_data(property_id, date, pricing_data)
================================================================================
"""

# Standard library imports
import logging  # For logging database operations and errors
from datetime import datetime, timedelta  # For date calculations
from decimal import Decimal  # For precise financial calculations
from typing import Dict, List, Optional, Tuple, Any  # For type hints

# Third-party imports
import mysql.connector  # MySQL database connector
from mysql.connector import Error as MySQLError  # MySQL error handling

# Local imports
from wyndham_config import WyndhamConfig  # Configuration constants


# ============================================================================
# LOGGING SETUP
# ============================================================================
# Configure logger for this module
logger = logging.getLogger(__name__)


class WyndhamDBOperations:
    """
    Database operations class for Wyndham Hotels pricing scraper.
    
    This class encapsulates all database interactions, providing methods to:
    - Fetch property details and characteristics
    - Retrieve historical performance data from wyndham_old_records
    - Save scraped pricing data
    - Manage scraping run records
    - Handle database transactions
    
    The class uses context managers for connection handling to ensure
    proper resource cleanup even if errors occur.
    """
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        """
        Initialize database operations with connection configuration.
        
        Args:
            db_config (dict, optional): Database connection parameters.
                If None, will attempt to import from db_operations.py
        
        The db_config dictionary should contain:
            - host: Database server hostname
            - user: Database username
            - password: Database password
            - database: Database name
        """
        # Store database configuration for creating connections
        if db_config:
            # Use provided configuration
            self.db_config = db_config
        else:
            # Import configuration from existing db_operations module
            try:
                # Attempt to import the get_db_connection function
                import sys
                import os
                # Add parent directory to path to import db_operations
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from db_operations import get_db_connection
                
                # Get a connection to extract config (we'll close it immediately)
                temp_conn = get_db_connection()
                # Extract connection parameters from the connection object
                self.db_config = {
                    'host': temp_conn.server_host,
                    'user': temp_conn.user,
                    'database': temp_conn.database,
                    # Password is not accessible from connection object
                    # Will need to be provided or read from environment
                }
                # Close the temporary connection
                temp_conn.close()
                
                # Log successful configuration import
                logger.info("Database configuration imported from db_operations.py")
                
            except ImportError as e:
                # If import fails, raise an error with helpful message
                logger.error(f"Failed to import database configuration: {e}")
                raise ValueError(
                    "Database configuration must be provided or db_operations.py "
                    "must be available for import"
                )
    
    
    def get_connection(self):
        """
        Create and return a new database connection.
        
        This method creates a fresh database connection using the stored
        configuration. Each connection should be closed after use to prevent
        connection pool exhaustion.
        
        Returns:
            mysql.connector.connection.MySQLConnection: Database connection
        
        Raises:
            MySQLError: If connection cannot be established
        """
        try:
            # Create a new database connection with stored configuration
            connection = mysql.connector.connect(**self.db_config)
            
            # Log successful connection (without sensitive details)
            logger.debug(f"Database connection established to {self.db_config.get('host')}")
            
            # Return the connection object
            return connection
            
        except MySQLError as e:
            # Log the connection error with details
            logger.error(f"Failed to connect to database: {e}")
            # Re-raise the exception for caller to handle
            raise
    
    
    def get_active_properties(self) -> List[Dict[str, Any]]:
        """
        Fetch all active properties that should be scraped.
        
        This method retrieves properties from the database that are linked
        to active Wyndham Hotels platform accounts. It joins the properties
        table with hotel_pms_platforms via the property_hotel_pms_platform
        linking table.
        
        Returns:
            list: List of dictionaries containing property details:
                - id (int): Property database ID
                - property_code (str): Wyndham property code
                - hotel_name (str): Property name
                - username (str): Wyndham RevIQ login username
                - password (str): Wyndham RevIQ login password
                - platform_id (int): Platform account ID
        
        Example:
            >>> db_ops = WyndhamDBOperations()
            >>> properties = db_ops.get_active_properties()
            >>> for prop in properties:
            ...     print(f"{prop['hotel_name']} ({prop['property_code']})")
        """
        # Initialize empty list to store results
        properties = []
        
        # Create database connection
        connection = None
        cursor = None
        
        try:
            # Establish database connection
            connection = self.get_connection()
            
            # Create cursor with dictionary=True to get results as dicts
            cursor = connection.cursor(dictionary=True)
            
            # SQL query to fetch active Wyndham properties
            # We join three tables:
            # 1. properties - contains property details
            # 2. property_hotel_pms_platform - links properties to platforms
            # 3. hotel_pms_platforms - contains credentials and platform info
            query = """
                SELECT 
                    p.id,
                    p.property_code,
                    p.hotel_name,
                    hpm.username,
                    hpm.password,
                    hpm.id as platform_id,
                    hpm.platform_name
                FROM properties p
                INNER JOIN property_hotel_pms_platform php 
                    ON p.id = php.property_id
                INNER JOIN hotel_pms_platforms hpm 
                    ON php.hotel_pms_platform_id = hpm.id
                WHERE hpm.platform_name LIKE '%Wyndham%'
                AND hpm.status = 'active'
                AND hpm.username IS NOT NULL
                AND hpm.password IS NOT NULL
                ORDER BY p.hotel_name
            """
            
            # Execute the query
            cursor.execute(query)
            
            # Fetch all results
            properties = cursor.fetchall()
            
            # Log the number of properties found
            logger.info(f"Found {len(properties)} active Wyndham properties")
            
            # Return the list of properties
            return properties
            
        except MySQLError as e:
            # Log database error
            logger.error(f"Error fetching active properties: {e}")
            # Return empty list on error
            return []
            
        finally:
            # Clean up database resources
            if cursor:
                cursor.close()  # Close cursor
            if connection:
                connection.close()  # Close connection
    
    
    def get_property_details(self, property_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific property.
        
        This method retrieves property details including the most recent
        saleable rooms count from the characteristics history table.
        
        Args:
            property_id (int): Database ID of the property
        
        Returns:
            dict or None: Property details including:
                - id (int): Property ID
                - property_code (str): Wyndham property code
                - hotel_name (str): Property name
                - saleable_rooms (int): Number of available rooms
                Returns None if property not found
        
        Example:
            >>> details = db_ops.get_property_details(2)
            >>> print(f"Property has {details['saleable_rooms']} rooms")
        """
        # Initialize connection and cursor
        connection = None
        cursor = None
        
        try:
            # Establish database connection
            connection = self.get_connection()
            
            # Create cursor for dictionary results
            cursor = connection.cursor(dictionary=True)
            
            # SQL query to fetch property details with most recent room count
            # We use a LEFT JOIN to get the most recent saleable_rooms value
            # from properties_characteristics_history table
            query = """
                SELECT 
                    p.id,
                    p.property_code,
                    p.hotel_name,
                    pch.saleable_rooms
                FROM properties p
                LEFT JOIN properties_characteristics_history pch 
                    ON p.id = pch.property_id
                WHERE p.id = %s
                ORDER BY pch.record_date DESC
                LIMIT 1
            """
            
            # Execute query with property_id parameter (prevents SQL injection)
            cursor.execute(query, (property_id,))
            
            # Fetch single result
            result = cursor.fetchone()
            
            # Check if property was found
            if result:
                # Log successful fetch
                logger.debug(
                    f"Fetched details for property {property_id}: "
                    f"{result['hotel_name']} ({result['property_code']})"
                )
                
                # If saleable_rooms is None, log a warning
                if result['saleable_rooms'] is None:
                    logger.warning(
                        f"No saleable_rooms found for property {property_id}, "
                        f"will use default value"
                    )
            else:
                # Log if property not found
                logger.warning(f"Property {property_id} not found in database")
            
            # Return the result (or None if not found)
            return result
            
        except MySQLError as e:
            # Log database error
            logger.error(f"Error fetching property details for ID {property_id}: {e}")
            # Return None on error
            return None
            
        finally:
            # Clean up resources
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    
    def get_property_id_by_uuid(self, property_uuid: str) -> Optional[int]:
        """
        Look up property ID by UUID.
        
        This method finds the integer ID of a property by searching for its UUID.
        
        Args:
            property_uuid (str): UUID string of the property
        
        Returns:
            int or None: Property ID if found, None otherwise
        
        Example:
            >>> property_id = db_ops.get_property_id_by_uuid('2e38cbf4-9693-486b-8d5a-54fb62e91a52')
            >>> print(f"Property ID: {property_id}")
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT id
                FROM properties
                WHERE uuid = %s
                LIMIT 1
            """
            
            cursor.execute(query, (property_uuid,))
            result = cursor.fetchone()
            
            if result:
                logger.debug(f"Found property ID {result['id']} for UUID {property_uuid}")
                return result['id']
            else:
                logger.warning(f"No property found with UUID {property_uuid}")
                return None
                
        except MySQLError as e:
            logger.error(f"Error looking up property by UUID {property_uuid}: {e}")
            return None
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    
    def get_historical_data(
        self, 
        property_id: int, 
        target_date: datetime,
        day_of_week: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch historical performance data using expanding search pattern.
        
        This method retrieves last year's performance metrics (occupancy, ADR,
        revenue) from the wyndham_old_records table. It uses an expanding search
        pattern to find data matching the same day of week:
        
        Search Order (expanding from target date):
        1. Exact date (offset 0)
        2. 1 day before (offset -1)
        3. 1 day after (offset +1)
        4. 2 days before (offset -2)
        5. 2 days after (offset +2)
        6. 3 days before (offset -3)
        7. 3 days after (offset +3)
        
        Stops at first match found (guarantees finding data within 7 days).
        
        Args:
            property_id (int): Database ID of the property
            target_date (datetime): Current date to find historical match for
            day_of_week (str): Day of week (e.g., 'Mon', 'Tue') for matching
        
        Returns:
            dict or None: Historical data including:
                - occupancy (Decimal): Last year's occupancy rate as decimal (0.0-1.0, e.g., 0.26 = 26%)
                - adr (Decimal): Last year's Average Daily Rate
                - revenue (Decimal): Last year's revenue
                - date (date): The actual date the data was found for
                - dow (str): Day of week from wyndham_old_records
                Returns None if no historical data found
        
        Example:
            >>> from datetime import datetime
            >>> date = datetime(2026, 1, 19)  # Sunday
            >>> hist = db_ops.get_historical_data(2, date, 'Sun')
            >>> print(f"Found data for: {hist['date']}")  # Might be 2025-01-18 (Saturday)
            >>> print(f"LY Occupancy: {hist['occupancy'] * 100}%")  # 0.26 * 100 = 26%
        """
        # Calculate the date from last year (same calendar date, previous year)
        # For example: 2026-01-19 -> 2025-01-19
        last_year_date = target_date - timedelta(days=365)
        
        # Initialize connection and cursor
        connection = None
        cursor = None
        
        try:
            # Establish database connection
            connection = self.get_connection()
            
            # Create cursor for dictionary results
            cursor = connection.cursor(dictionary=True)
            
            # ====================================================================
            # EXPANDING SEARCH PATTERN
            # ====================================================================
            # Try offsets in order: 0, -1, +1, -2, +2, -3, +3
            # This covers all 7 days of the week, guaranteeing a match
            search_offsets = [0, -1, 1, -2, 2, -3, 3]
            
            # Log search start
            logger.debug(
                f"Searching for historical data near {last_year_date.strftime('%Y-%m-%d')} "
                f"for property {property_id}"
            )
            
            # Try each offset until we find a match
            for offset in search_offsets:
                # Calculate search date with offset
                search_date = last_year_date + timedelta(days=offset)
                search_date_str = search_date.strftime('%Y-%m-%d')
                
                # SQL query to fetch historical data from wyndham_old_records
                # NOTE: wyndham_old_records uses 'dow' column (uppercase, e.g., 'MON')
                # We match case-insensitively using UPPER()
                query = """
                    SELECT 
                        occupancy,
                        adr,
                        revenue,
                        date,
                        dow
                    FROM wyndham_old_records
                    WHERE property_id = %s
                    AND date = %s
                    LIMIT 1
                """
                
                # Execute query with parameters (prevents SQL injection)
                cursor.execute(query, (property_id, search_date_str))
                
                # Fetch single result
                result = cursor.fetchone()
                
                # If found, log and return immediately
                if result:
                    logger.info(
                        f"✅ Found historical data for property {property_id} "
                        f"on {search_date_str} (offset: {offset:+d} days, dow: {result.get('dow', 'N/A')})"
                    )
                    return result
                else:
                    # Log attempt for debugging
                    logger.debug(
                        f"  ⏩ No data on {search_date_str} (offset: {offset:+d}), trying next..."
                    )
            
            # ====================================================================
            # NO MATCH FOUND (very rare - means no data for entire week)
            # ====================================================================
            logger.warning(
                f"⚠️ No historical data found for property {property_id} "
                f"within ±3 days of {last_year_date.strftime('%Y-%m-%d')}"
            )
            return None
            
        except MySQLError as e:
            # Log database error
            logger.error(
                f"❌ Error fetching historical data for property {property_id} "
                f"near {last_year_date.strftime('%Y-%m-%d')}: {e}"
            )
            # Return None on error
            return None
            
        finally:
            # Clean up resources
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    
    def save_pricing_data(
        self,
        update_record,  # WyndhamUpdateRecord object from models.wyndham_model
        scraping_run_id: Optional[int] = None
    ) -> bool:
        """
        Save a single WyndhamUpdateRecord to the database.
        
        This method inserts or updates pricing data in the update_records
        table using a WyndhamUpdateRecord model object. It uses INSERT ... ON DUPLICATE 
        KEY UPDATE to handle both new records and updates to existing records.
        
        The method will:
        1. Look up the property_id using the property_uuid from the WyndhamUpdateRecord
        2. Insert or update the record in update_records table
        
        NOTE: All percentage values in WyndhamUpdateRecord are already decimals (0.0-1.0)
              e.g., 26% is stored as 0.26, not 26.00
        
        Args:
            update_record (WyndhamUpdateRecord): WyndhamUpdateRecord object containing pricing data
            scraping_run_id (int, optional): ID of the current scraping run (can be None)
        
        Returns:
            bool: True if save successful, False otherwise
        
        Example:
            >>> from models.wyndham_model import WyndhamUpdateRecord
            >>> record = WyndhamUpdateRecord(
            ...     property_uuid='2e38cbf4-9693-486b-8d5a-54fb62e91a52',
            ...     record_date=date(2026, 2, 10),
            ...     standard_price=Decimal('85.00'),
            ...     occupancy=Decimal('0.20'),  # 20% as decimal
            ...     # ... other fields
            ... )
            >>> success = db_ops.save_pricing_data(record, scraping_run_id=123)
            >>> print(f"Save successful: {success}")
        """
        connection = None
        cursor = None
        
        try:
            # Step 1: Look up property_id from property_uuid
            property_id = self.get_property_id_by_uuid(update_record.property_uuid)
            
            if property_id is None:
                logger.error(f"Cannot save record: property UUID {update_record.property_uuid} not found")
                return False
            
            # Step 2: Establish database connection
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Step 3: SQL query for inserting/updating pricing data
            query = """
                INSERT INTO update_records (
                    property_id,
                    scraping_run_id,
                    record_timestamp,
                    record_date,
                    day_of_week,
                    algo_output_price,
                    standard_price,
                    standard_previous_price,
                    standard_price_change,
                    competitor_set_avg_price,
                    occupancy,
                    forecasted_occupancy,
                    updated_by_rm,
                    revenue_per_room,
                    ly_occupancy,
                    ly_adr,
                    on_the_books_occ,
                    arrivals_forecast,
                    departure_forecast,
                    total_rooms,
                    ooo,
                    otb_rooms,
                    avl_rooms,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    algo_output_price = VALUES(algo_output_price),
                    standard_price = VALUES(standard_price),
                    standard_previous_price = VALUES(standard_previous_price),
                    standard_price_change = VALUES(standard_price_change),
                    competitor_set_avg_price = VALUES(competitor_set_avg_price),
                    occupancy = VALUES(occupancy),
                    forecasted_occupancy = VALUES(forecasted_occupancy),
                    updated_by_rm = VALUES(updated_by_rm),
                    revenue_per_room = VALUES(revenue_per_room),
                    ly_occupancy = VALUES(ly_occupancy),
                    ly_adr = VALUES(ly_adr),
                    on_the_books_occ = VALUES(on_the_books_occ),
                    arrivals_forecast = VALUES(arrivals_forecast),
                    departure_forecast = VALUES(departure_forecast),
                    total_rooms = VALUES(total_rooms),
                    ooo = VALUES(ooo),
                    otb_rooms = VALUES(otb_rooms),
                    avl_rooms = VALUES(avl_rooms),
                    updated_at = NOW()
            """
            
            # Step 4: Prepare values tuple from WyndhamUpdateRecord object
            values = (
                property_id,
                scraping_run_id,
                update_record.record_timestamp,
                update_record.record_date,
                update_record.day_of_week,
                update_record.algo_output_price,
                update_record.standard_price,
                update_record.standard_previous_price,
                update_record.standard_price_change,
                update_record.competitor_set_avg_price,
                update_record.occupancy,
                update_record.forecasted_occupancy,
                update_record.updated_by_rm,
                update_record.revenue_per_room,
                update_record.ly_occupancy,
                update_record.ly_adr,
                update_record.on_the_books_occ,
                update_record.arrivals_forecast,
                update_record.departure_forecast,
                update_record.total_rooms,
                update_record.ooo,
                update_record.otb_rooms,
                update_record.avl_rooms
            )
            
            # Step 5: Execute the insert/update query
            cursor.execute(query, values)
            
            # Step 6: Commit the transaction
            connection.commit()
            
            # Step 7: Log success
            action = "inserted" if cursor.rowcount == 1 else "updated"
            logger.info(
                f"Successfully {action} record for property {property_id} "
                f"on {update_record.record_date}"
            )
            
            return True
            
        except MySQLError as e:
            logger.error(f"Error saving pricing data: {e}")
            
            if connection:
                connection.rollback()
            
            return False
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    
    def create_scraping_run(self, platform_id: int) -> Optional[int]:
        """
        Create a new scraping run record and return its ID.
        
        A scraping run represents a single execution of the scraper for a
        platform account. It tracks when the scrape started, ended, and its status.
        
        Args:
            platform_id (int): Database ID of the hotel_pms_platform being scraped
        
        Returns:
            int or None: ID of the created scraping run, or None on error
        
        Example:
            >>> run_id = db_ops.create_scraping_run(3)
            >>> print(f"Started scraping run {run_id}")
        """
        # Initialize connection and cursor
        connection = None
        cursor = None
        
        try:
            # Establish database connection
            connection = self.get_connection()
            
            # Create cursor
            cursor = connection.cursor()
            
            # SQL query to insert new scraping run
            # Note: Table uses hotel_pms_platform_id, not property_id
            # And uses started_at, not start_time
            query = """
                INSERT INTO scraping_runs (
                    hotel_pms_platform_id,
                    started_at,
                    status
                ) VALUES (
                    %s,
                    NOW(),
                    'running'
                )
            """
            
            # Execute the insert query
            cursor.execute(query, (platform_id,))
            
            # Commit the transaction
            connection.commit()
            
            # Get the ID of the inserted record
            run_id = cursor.lastrowid
            
            # Log success
            logger.info(f"Created scraping run {run_id} for platform {platform_id}")
            
            # Return the run ID
            return run_id
            
        except MySQLError as e:
            # Log database error
            logger.error(f"Error creating scraping run: {e}")
            
            # Rollback on error
            if connection:
                connection.rollback()
            
            # Return None on error
            return None
            
        finally:
            # Clean up resources
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    
    def update_scraping_run(
        self,
        run_id: int,
        status: str,
        records_created: int = 0,
        days_scraped: int = 0,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update a scraping run with completion status and statistics.
        
        This method updates the scraping run record when the scrape completes
        (successfully or with errors), recording the end time, status, and
        number of records scraped.
        
        Args:
            run_id (int): ID of the scraping run to update
            status (str): Final status ('completed', 'failed', 'running')
            records_created (int): Number of records successfully created
            days_scraped (int): Number of days of data scraped
            error_message (str, optional): Error message if scrape failed
        
        Returns:
            bool: True if update successful, False otherwise
        
        Example:
            >>> success = db_ops.update_scraping_run(123, 'completed', 365, 7)
            >>> if success:
            ...     print("Scraping run completed successfully")
        """
        # Initialize connection and cursor
        connection = None
        cursor = None
        
        try:
            # Establish database connection
            connection = self.get_connection()
            
            # Create cursor
            cursor = connection.cursor()
            
            # SQL query to update scraping run
            # Note: Table uses completed_at, not end_time
            # And uses records_created, not records_scraped
            query = """
                UPDATE scraping_runs
                SET 
                    completed_at = NOW(),
                    status = %s,
                    records_created = %s,
                    days_scraped = %s,
                    error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            
            # Execute the update query
            cursor.execute(query, (status, records_created, days_scraped, error_message, run_id))
            
            # Commit the transaction
            connection.commit()
            
            # Log success
            logger.info(
                f"Updated scraping run {run_id}: "
                f"status={status}, records={records_created}, days={days_scraped}"
            )
            
            # Return success
            return True
            
        except MySQLError as e:
            # Log database error
            logger.error(f"Error updating scraping run {run_id}: {e}")
            
            # Rollback on error
            if connection:
                connection.rollback()
            
            # Return failure
            return False
            
        finally:
            # Clean up resources
            if cursor:
                cursor.close()
            if connection:
                connection.close()


# ============================================================================
# MODULE-LEVEL HELPER FUNCTIONS
# ============================================================================

def format_occupancy_for_db(rooms: Optional[int], percentage: Optional[float]) -> Optional[str]:
    """
    Format occupancy data as "rooms (percentage%)" for database storage.
    
    The database stores occupancy in a VARCHAR field with format like
    "30 (45.5%)" which shows both the room count and percentage.
    
    Args:
        rooms (int or None): Number of occupied rooms
        percentage (float or None): Occupancy percentage (0-100)
    
    Returns:
        str or None: Formatted string like "30 (45.5%)", or None if data missing
    
    Example:
        >>> format_occupancy_for_db(30, 45.5)
        '30 (45.5%)'
        >>> format_occupancy_for_db(None, None)
        None
    """
    # Check if both values are provided
    if rooms is not None and percentage is not None:
        # Format as "rooms (percentage%)" with 1 decimal place
        return f"{rooms} ({percentage:.1f}%)"
    else:
        # Return None if either value is missing
        return None


def calculate_price_change(current_price: Optional[float], previous_price: Optional[float]) -> Optional[float]:
    """
    Calculate the price change from previous to current price.
    
    Formula: current_price - previous_price
    
    This shows how much the price has changed FROM the previous/system price
    TO the current standard price.
    
    Args:
        current_price (float or None): Current standard price
        previous_price (float or None): Previous/system price
    
    Returns:
        float or None: Price difference (current - previous), or None if data missing
    
    Example:
        >>> calculate_price_change(115.09, 108.99)
        6.10  (price increased by $6.10 - POSITIVE)
        >>> calculate_price_change(101.99, 104.99)
        -3.00  (price decreased by $3.00 - NEGATIVE)
    """
    # Check if both prices are provided
    if current_price is not None and previous_price is not None:
        # Calculate and return the difference: current - previous
        # Positive value means price went UP
        # Negative value means price went DOWN
        return float(current_price) - float(previous_price)
    else:
        # Return None if either price is missing
        return None


def calculate_revenue_per_room(revenue: Optional[float], total_rooms: int) -> Optional[float]:
    """
    Calculate revenue per available room (RevPAR equivalent).
    
    Args:
        revenue (float or None): Total revenue for the date
        total_rooms (int): Total number of saleable rooms
    
    Returns:
        float or None: Revenue divided by total rooms, or None if data missing
    
    Example:
        >>> calculate_revenue_per_room(5940.00, 66)
        90.00
        >>> calculate_revenue_per_room(None, 66)
        None
    """
    # Check if revenue is provided and total_rooms is valid
    if revenue is not None and total_rooms > 0:
        # Calculate and return revenue per room
        return float(revenue) / total_rooms
    else:
        # Return None if data is missing or invalid
        return None
