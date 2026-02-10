"""
Database Operations
All database queries and data manipulation functions for the scraper
"""

import mysql.connector
from mysql.connector import Error
from db_config import get_db_connection
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== FETCH OPERATIONS ==============

def get_platforms_for_scraping(platform_name='Choice'):
    """
    Get all active platforms with their linked properties
    Returns platforms grouped by credentials (one login per platform)
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT 
            hpp.id as platform_id,
            hpp.platform_name,
            hpp.username,
            hpp.password,
            hpp.status,
            hpp.last_scraped_at,
            hpp.config,
            COUNT(p.id) as property_count,
            GROUP_CONCAT(p.id) as property_ids,
            GROUP_CONCAT(p.property_code) as property_codes,
            GROUP_CONCAT(p.hotel_name SEPARATOR '||') as hotel_names,
            GROUP_CONCAT(pivot.id) as pivot_ids
        FROM hotel_pms_platforms hpp
        JOIN property_hotel_pms_platform pivot ON hpp.id = pivot.hotel_pms_platform_id
        JOIN properties p ON pivot.property_id = p.id
        WHERE hpp.platform_name = %s
          AND hpp.status = 'active'
        GROUP BY hpp.id
        ORDER BY hpp.id
    """
    
    try:
        cursor.execute(query, (platform_name,))
        platforms = cursor.fetchall()
        
        logger.info(f"Found {len(platforms)} active {platform_name} platform(s)")
        
        # Parse the concatenated strings into lists
        for platform in platforms:
            if platform['property_ids']:
                platform['property_ids'] = platform['property_ids'].split(',')
                platform['property_codes'] = platform['property_codes'].split(',')
                platform['hotel_names'] = platform['hotel_names'].split('||')
            else:
                platform['property_ids'] = []
                platform['property_codes'] = []
                platform['hotel_names'] = []
        
        return platforms
        
    except Error as e:
        logger.error(f"Error fetching platforms: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_property_details(property_id):
    """Get detailed information about a specific property"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT 
            p.*,
            pch.saleable_rooms,
            pch.physical_capacity,
            pch.out_of_order
        FROM properties p
        LEFT JOIN (
            SELECT property_id, saleable_rooms, physical_capacity, out_of_order
            FROM properties_characteristics_history
            WHERE property_id = %s
            ORDER BY record_date DESC
            LIMIT 1
        ) pch ON p.id = pch.property_id
        WHERE p.id = %s
    """
    
    try:
        cursor.execute(query, (property_id, property_id))
        property_data = cursor.fetchone()
        return property_data
    except Error as e:
        logger.error(f"Error fetching property details: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def get_previous_standard_price(property_id, current_date):
    """
    Get the previous standard_price from the last record for the same property
    Returns the standard_price from the most recent record before current_date
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT standard_price 
        FROM update_records 
        WHERE property_id = %s 
          AND record_date < %s 
          AND standard_price IS NOT NULL
        ORDER BY record_date DESC 
        LIMIT 1
    """
    
    try:
        cursor.execute(query, (property_id, current_date))
        result = cursor.fetchone()
        return result['standard_price'] if result else None
    except Error as e:
        logger.error(f"Error fetching previous standard_price: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def get_platform_property_id(property_id, platform_id):
    """
    Get the platform-specific property ID
    This is stored in the config JSON field or can be a separate column
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # For now, we'll use property_code as platform_property_id
    # You can modify this based on your actual data structure
    query = """
        SELECT p.property_code, p.bfi_property_id, p.pms_id
        FROM properties p
        WHERE p.id = %s
    """
    
    try:
        cursor.execute(query, (property_id,))
        result = cursor.fetchone()
        
        # Return the appropriate ID based on platform
        # Modify this logic based on your needs
        return result['property_code'] if result else None
        
    except Error as e:
        logger.error(f"Error fetching platform property ID: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# ============== SCRAPING RUN OPERATIONS ==============

def create_scraping_run(platform_id, start_date, end_date, days_scraped):
    """Create a new scraping run record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO scraping_runs 
        (hotel_pms_platform_id, started_at, status, days_scraped, metadata)
        VALUES (%s, NOW(), 'running', %s, %s)
    """
    
    metadata = {
        'start_date': str(start_date),
        'end_date': str(end_date),
        'days_scraped': days_scraped
    }
    
    try:
        import json
        cursor.execute(query, (platform_id, days_scraped, json.dumps(metadata)))
        run_id = cursor.lastrowid
        conn.commit()
        
        logger.info(f"Created scraping run ID: {run_id} for platform ID: {platform_id}")
        return run_id
        
    except Error as e:
        logger.error(f"Error creating scraping run: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()


def update_scraping_run(run_id, status, records_created=0, error_message=None):
    """Update scraping run status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        UPDATE scraping_runs
        SET status = %s,
            completed_at = NOW(),
            records_created = %s,
            error_message = %s
        WHERE id = %s
    """
    
    try:
        cursor.execute(query, (status, records_created, error_message, run_id))
        conn.commit()
        
        logger.info(f"Updated scraping run {run_id}: {status}, {records_created} records")
        
    except Error as e:
        logger.error(f"Error updating scraping run: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def update_platform_last_scraped(platform_id):
    """Update platform's last_scraped_at timestamp"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        UPDATE hotel_pms_platforms
        SET last_scraped_at = NOW()
        WHERE id = %s
    """
    
    try:
        cursor.execute(query, (platform_id,))
        conn.commit()
        logger.info(f"Updated last_scraped_at for platform {platform_id}")
    except Error as e:
        logger.error(f"Error updating platform timestamp: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# ============== DATA SAVING OPERATIONS ==============

def save_pricing_data(run_id, property_id, scraped_data_list):
    """
    Save scraped pricing data to update_records table
    
    Args:
        run_id: ID of the scraping run
        property_id: ID of the property
        scraped_data_list: List of dictionaries containing scraped data
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    saved_count = 0
    
    for data in scraped_data_list:
        try:
            # Parse values from scraped data
            record_date = parse_date(data.get('Date Only'))
            if not record_date:
                logger.warning(f"Skipping record with invalid date: {data.get('Date Only')}")
                continue
            
            day_of_week = data.get('Day of Week')
            
            # Pricing data
            current_price = parse_price(data.get('Current Price'))
            system_price = parse_price(data.get('System Price'))
            competitor_price = parse_price(data.get('Competitor Avg Price'))
            
            # Get previous standard_price from database
            previous_standard_price = get_previous_standard_price(property_id, record_date)
            
            # Calculate standard_price_change (absolute: current - previous)
            # Convert both to float to avoid type mismatch (Decimal vs float)
            standard_price_change = None
            if current_price is not None and previous_standard_price is not None:
                try:
                    current_price_float = float(current_price) if current_price is not None else None
                    previous_price_float = float(previous_standard_price) if previous_standard_price is not None else None
                    if current_price_float is not None and previous_price_float is not None:
                        standard_price_change = current_price_float - previous_price_float
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error calculating standard_price_change: {e}")
                    standard_price_change = None
            
            # Occupancy data
            occ_books_val, occ_books_pct = parse_occupancy(data.get('Occ. on Books'))
            occ_forecast_val, occ_forecast_pct = parse_occupancy(data.get('Occ. Forecast'))
            occ_ly_val, occ_ly_pct = parse_occupancy(data.get('Occ. LY'))
            
            # Debug: Log occupancy values for first record
            if record_date and 'Jan 15' in str(data.get('Date Only', '')):
                logger.info(f"DEBUG - Occupancy data for {record_date}:")
                logger.info(f"  Raw 'Occ. on Books': {data.get('Occ. on Books')}")
                logger.info(f"  Parsed occ_books: val={occ_books_val}, pct={occ_books_pct}")
                logger.info(f"  Raw 'Occ. Forecast': {data.get('Occ. Forecast')}")
                logger.info(f"  Parsed occ_forecast: val={occ_forecast_val}, pct={occ_forecast_pct}")
                logger.info(f"  Arrivals: {data.get('Arrivals')}")
                logger.info(f"  Departures: {data.get('Departures')}")
            
            # Revenue data
            adr = parse_price(data.get('ADR'))
            stly_adr = parse_price(data.get('STLY ADR'))
            revenue = parse_price(data.get('Revenue'))
            stly_revenue = parse_price(data.get('STLY Revenue'))
            
            # Other fields
            available_rooms = parse_int(data.get('Available Rooms'))
            arrivals_forecast = parse_int(data.get('Arrivals'))
            departure_forecast = parse_int(data.get('Departures'))
            unlock_price_present = data.get('Unlock Price Present', False)
            
            # Calculate revenue_per_room = Revenue / Available Rooms
            revenue_per_room = None
            if revenue is not None and available_rooms is not None and available_rooms > 0:
                revenue_per_room = revenue / available_rooms
            
            # Insert or update record
            query = """
                INSERT INTO update_records 
                (property_id, scraping_run_id, record_date, day_of_week,
                 algo_output_price, standard_price, standard_previous_price, standard_price_change,
                 competitor_set_avg_price,
                 occupancy, forecasted_occupancy, 
                 ly_occupancy, ly_adr,
                 on_the_books_occ, revenue_per_room,
                 arrivals_forecast, departure_forecast,
                 created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    algo_output_price = VALUES(algo_output_price),
                    standard_price = VALUES(standard_price),
                    standard_previous_price = VALUES(standard_previous_price),
                    standard_price_change = VALUES(standard_price_change),
                    competitor_set_avg_price = VALUES(competitor_set_avg_price),
                    occupancy = VALUES(occupancy),
                    forecasted_occupancy = VALUES(forecasted_occupancy),
                    ly_occupancy = VALUES(ly_occupancy),
                    ly_adr = VALUES(ly_adr),
                    on_the_books_occ = VALUES(on_the_books_occ),
                    revenue_per_room = VALUES(revenue_per_room),
                    arrivals_forecast = VALUES(arrivals_forecast),
                    departure_forecast = VALUES(departure_forecast),
                    updated_at = NOW()
            """
            
            cursor.execute(query, (
                property_id,
                run_id,
                record_date,
                day_of_week,
                system_price,  # algo_output_price
                current_price,  # standard_price
                previous_standard_price,  # standard_previous_price
                standard_price_change,  # standard_price_change
                competitor_price,
                occ_books_pct,  # occupancy (from Occ. on Books)
                occ_forecast_pct,  # forecasted_occupancy (from Occ. Forecast)
                occ_ly_pct,  # ly_occupancy (from Occ. LY)
                stly_adr,  # ly_adr (from STLY ADR)
                occ_books_pct,  # on_the_books_occ (same as occupancy, from Occ. on Books)
                revenue_per_room,  # revenue_per_room (calculated: Revenue / Available Rooms)
                arrivals_forecast,  # arrivals_forecast
                departure_forecast  # departure_forecast
            ))
            
            saved_count += 1
            
        except Error as e:
            logger.error(f"Error saving record for date {data.get('Date Only')}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    try:
        conn.commit()
        logger.info(f"Saved {saved_count} records for property {property_id}")
        return saved_count
    except Error as e:
        logger.error(f"Error committing data: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()
        conn.close()


# ============== HELPER FUNCTIONS ==============

def parse_price(price_str):
    """Parse price string to decimal"""
    if not price_str or price_str == 'None' or price_str == '':
        return None
    try:
        # Remove $, commas, and whitespace
        cleaned = str(price_str).replace('$', '').replace(',', '').strip()
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


def parse_occupancy(occ_str):
    """
    Parse occupancy string like '45 (67.5%)' to (45, 67.5)
    Returns: (value, percentage)
    """
    if not occ_str or occ_str == 'None':
        return None, None
    try:
        # Format: "45 (67.5%)"
        parts = str(occ_str).split('(')
        value = int(parts[0].strip())
        percent = float(parts[1].replace('%)', '').strip())
        return value, percent
    except (ValueError, IndexError, AttributeError):
        return None, None


def parse_int(int_str):
    """Parse integer string"""
    if not int_str or int_str == 'None':
        return None
    try:
        return int(str(int_str).replace(',', '').strip())
    except (ValueError, AttributeError):
        return None


def parse_date(date_str):
    """
    Parse date string to date object
    Expected format: "December 26, 2025" or similar
    """
    if not date_str or date_str == 'None':
        return None
    try:
        # Try multiple date formats
        formats = [
            "%B %d, %Y",  # December 26, 2025
            "%b %d, %Y",  # Dec 26, 2025
            "%Y-%m-%d",   # 2025-12-26
            "%m/%d/%Y"    # 12/26/2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        return None


# ============== UTILITY FUNCTIONS ==============

def get_statistics():
    """Get database statistics for monitoring"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    stats = {}
    
    try:
        # Count properties
        cursor.execute("SELECT COUNT(*) as count FROM properties")
        stats['total_properties'] = cursor.fetchone()['count']
        
        # Count platforms
        cursor.execute("SELECT COUNT(*) as count FROM hotel_pms_platforms")
        stats['total_platforms'] = cursor.fetchone()['count']
        
        # Count active platforms
        cursor.execute("SELECT COUNT(*) as count FROM hotel_pms_platforms WHERE status = 'active'")
        stats['active_platforms'] = cursor.fetchone()['count']
        
        # Count scraping runs
        cursor.execute("SELECT COUNT(*) as count FROM scraping_runs")
        stats['total_runs'] = cursor.fetchone()['count']
        
        # Count successful runs
        cursor.execute("SELECT COUNT(*) as count FROM scraping_runs WHERE status = 'completed'")
        stats['successful_runs'] = cursor.fetchone()['count']
        
        # Count update records
        cursor.execute("SELECT COUNT(*) as count FROM update_records")
        stats['total_records'] = cursor.fetchone()['count']
        
        # Last scraping run
        cursor.execute("""
            SELECT started_at, status 
            FROM scraping_runs 
            ORDER BY started_at DESC 
            LIMIT 1
        """)
        last_run = cursor.fetchone()
        stats['last_run'] = last_run if last_run else None
        
        return stats
        
    except Error as e:
        logger.error(f"Error getting statistics: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()


def print_statistics():
    """Print database statistics"""
    stats = get_statistics()
    
    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)
    print(f"Total Properties: {stats.get('total_properties', 0)}")
    print(f"Total Platforms: {stats.get('total_platforms', 0)}")
    print(f"Active Platforms: {stats.get('active_platforms', 0)}")
    print(f"Total Scraping Runs: {stats.get('total_runs', 0)}")
    print(f"Successful Runs: {stats.get('successful_runs', 0)}")
    print(f"Total Update Records: {stats.get('total_records', 0)}")
    
    if stats.get('last_run'):
        print(f"\nLast Scraping Run:")
        print(f"  Time: {stats['last_run']['started_at']}")
        print(f"  Status: {stats['last_run']['status']}")
    
    print("=" * 60)

