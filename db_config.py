"""
Database Configuration
Connection settings and helper functions
"""

import mysql.connector
from mysql.connector import pooling, Error

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'hotel_revenue_management',
    'user': 'root',
    'password': '',  # Empty password
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# Create connection pool for better performance
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="scraper_pool",
        pool_size=5,
        pool_reset_session=True,
        **DB_CONFIG
    )
    print("✅ Database connection pool created")
except Error as e:
    print(f"❌ Error creating connection pool: {e}")
    connection_pool = None

def get_db_connection():
    """Get connection from pool"""
    if connection_pool:
        return connection_pool.get_connection()
    else:
        # Fallback to direct connection
        return mysql.connector.connect(**DB_CONFIG)

def test_connection():
    """Test database connectivity"""
    try:
        conn = get_db_connection()
        if conn.is_connected():
            print("✅ Database connection successful")
            conn.close()
            return True
    except Error as e:
        print(f"❌ Database connection failed: {e}")
        return False
    return False




















