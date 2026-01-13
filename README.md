# Choice Pricing Scraper - Database Integration

## Overview

Automated web scraper for hotel pricing data from Choice MAX platform, integrated with Laravel hotel revenue management system.

---

## Quick Start

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Test Database Connection
```bash
python3 test_db_connection.py
```

### 3. Run Scraper (Coming Soon)
```bash
python3 choice_pricing_local.py
```

---

## Project Structure

```
hm_scrapers/
├── choice_pricing_local.py          # Main scraper script
├── db_config.py                     # Database configuration
├── db_operations.py                 # Database operations
├── test_db_connection.py            # Connection test utility
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── SETUP_COMPLETE.md                # Setup guide
├── DATABASE_SCHEMA.md               # Database documentation
├── DB_MIGRATION_GUIDE.md            # Migration guide
└── choice_pricing_analysis.md       # Code analysis

```

---

## Database Architecture

### Tables

1. **`properties`** - Hotel information
2. **`hotel_pms_platforms`** - Platform credentials (Choice, Wyndham, etc.)
3. **`property_hotel_pms_platform`** - Links properties to platforms (many-to-many)
4. **`scraping_runs`** - Tracks each scraping session
5. **`update_records`** - Stores scraped pricing/occupancy data
6. **`properties_characteristics_history`** - Room inventory history

### Key Concept: Many-to-Many Relationship

```
Platform Account (Choice Max)
├── username: abc@choice.com
├── password: ****
└── Linked Properties:
    ├── Pearl Continental
    ├── Budget Inn
    └── Grand Plaza

Result: Login ONCE, scrape ALL THREE properties
```

---

## How It Works

### 1. Fetch Platforms
```python
platforms = get_platforms_for_scraping('Choice Max')
# Returns: [{platform_id, username, password, property_ids, hotel_names, ...}]
```

### 2. Group by Credentials (Automatic!)
- Properties linked to same platform = automatically grouped
- No need for manual group_id management
- Script handles optimization

### 3. Scrape Efficiently
```python
for platform in platforms:
    # Login ONCE
    login(platform['username'], platform['password'])
    
    # Scrape ALL properties using this account
    for property_id in platform['property_ids']:
        scrape_property(property_id)
```

### 4. Save to Database
```python
save_pricing_data(run_id, property_id, scraped_data)
# Saves to: update_records table
```

---

## Database Configuration

**File:** `db_config.py`

```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'hotel_revenue_management',
    'user': 'root',
    'password': ''
}
```

---

## Available Functions

### From `db_operations.py`:

#### Fetching Data
- `get_platforms_for_scraping(platform_name)` - Get platforms with properties
- `get_property_details(property_id)` - Get property information
- `get_statistics()` - Get database statistics

#### Managing Scraping Runs
- `create_scraping_run(platform_id, start_date, end_date, days)` - Start new run
- `update_scraping_run(run_id, status, records, error)` - Update run status
- `update_platform_last_scraped(platform_id)` - Update timestamp

#### Saving Data
- `save_pricing_data(run_id, property_id, data_list)` - Save scraped records

#### Utilities
- `print_statistics()` - Print database stats
- `parse_price(price_str)` - Parse "$1,234.56" → 1234.56
- `parse_occupancy(occ_str)` - Parse "45 (67.5%)" → (45, 67.5)
- `parse_date(date_str)` - Parse "December 26, 2025" → date object

---

## Current Status

### ✅ Completed
- Database schema designed
- Connection module created
- Database operations module created
- Test utilities created
- Helper functions implemented
- Documentation complete

### ⬜ Pending
- Update main scraper script to use database
- Test with real scraping
- Integrate with Laravel application
- Add error handling and retry logic
- Implement logging

---

## Testing

### Test Database Connection
```bash
python3 test_db_connection.py
```

**What it tests:**
- Database connectivity
- Table existence
- Sample data queries
- Scraping query (grouped by platform)
- Option to insert test data

### Expected Output
```
✅ Successfully connected to MySQL Server
✅ Connected to database: hotel_revenue_management
✅ All tables exist
📊 Total properties: X
📊 Total platforms: Y
🔗 Sample relationships shown
```

---

## Important Notes

### 1. Platform Name
Your database uses **"Choice Max"** not "Choice"

```python
# Correct:
platforms = get_platforms_for_scraping('Choice Max')

# Wrong:
platforms = get_platforms_for_scraping('Choice')
```

### 2. Password Encryption
Currently passwords are stored as plain text. For production:
- Use Laravel's encryption
- Decrypt in Python using matching algorithm
- Or use separate encryption key

### 3. Property Platform ID
The scraper needs the platform-specific property ID. Currently using `property_code`.
Adjust `get_platform_property_id()` function if needed.

---

## Laravel Integration

### Add Platform (Admin)
```php
// In Laravel
$platform = HotelPmsPlatform::create([
    'platform_name' => 'Choice Max',
    'username' => 'user@example.com',
    'password' => Crypt::encryptString('password'),
    'status' => 'active'
]);

// Link properties
$platform->properties()->attach([1, 2, 3]);
```

### View Results (Admin)
```php
// Get all update records for a property
$records = UpdateRecord::where('property_id', 1)
    ->whereDate('record_date', '>=', now()->subDays(30))
    ->orderBy('record_date')
    ->get();

// Get scraping history
$runs = ScrapingRun::with('platform')
    ->latest()
    ->paginate(20);
```

---

## Workflow

### Daily Automated Scraping

```
1. Laravel Scheduler (10 AM daily)
   ↓
2. Triggers Python Script
   ↓
3. Script fetches active platforms from DB
   ↓
4. Groups properties by platform credentials
   ↓
5. For each platform:
   - Login once
   - Scrape all linked properties
   - Save data to update_records
   - Update timestamps
   ↓
6. Laravel displays data in dashboard
```

---

## Troubleshooting

### Connection Error
```bash
# Check MySQL is running
mysql.server status

# Test manual connection
mysql -u root hotel_revenue_management
```

### No Platforms Found
```sql
-- Check platform name
SELECT platform_name FROM hotel_pms_platforms;

-- Check status
SELECT platform_name, status FROM hotel_pms_platforms;

-- Check relationships
SELECT COUNT(*) FROM property_hotel_pms_platform;
```

### Module Not Found
```bash
pip3 install mysql-connector-python
```

---

## Documentation

- **SETUP_COMPLETE.md** - Setup guide and quick reference
- **DATABASE_SCHEMA.md** - Complete database documentation
- **DB_MIGRATION_GUIDE.md** - Migration from Google Sheets
- **choice_pricing_analysis.md** - Detailed code analysis

---

## Requirements

### Python Packages
- selenium >= 4.0.0
- webdriver-manager >= 3.8.0
- selenium-stealth >= 1.0.6
- pandas >= 1.5.0
- mysql-connector-python >= 8.0.33
- gspread >= 5.7.0 (for migration)
- python-dotenv >= 1.0.0

### System Requirements
- Python 3.7+
- MySQL/MariaDB
- Chrome browser
- ChromeDriver (auto-installed)

---

## Support & Contact

For issues or questions:
1. Check SETUP_COMPLETE.md
2. Run test_db_connection.py
3. Review error logs in scraping_runs table
4. Check DATABASE_SCHEMA.md for table structure

---

## License

Internal use only.

---

**Version:** 1.0  
**Last Updated:** December 26, 2025  
**Status:** Ready for integration 🚀









