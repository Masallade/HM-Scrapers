# Update Records Table Structure

## Overview
The `update_records` table stores daily pricing, occupancy, and revenue management metrics for each property. It contains pricing data (algorithm output, standard price, competitor prices), occupancy metrics, forecasts, year-over-year comparisons, and room inventory information.

**Table Name:** `update_records`  
**Model:** `App\Models\UpdateRecord`  
**Created:** December 8, 2025  
**Last Updated:** January 27, 2026

---

## Complete Table Structure

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | BIGINT UNSIGNED | PRIMARY KEY, AUTO_INCREMENT | Auto-increment record ID |
| `property_id` | BIGINT UNSIGNED | FOREIGN KEY → `properties.id`, NOT NULL, ON DELETE CASCADE | Reference to the property |
| `scraping_run_id` | BIGINT UNSIGNED | FOREIGN KEY → `scraping_runs.id`, NULLABLE, ON DELETE SET NULL | Reference to the scraping run that created this record |
| `record_timestamp` | TIMESTAMP | NULLABLE | Exact timestamp when the record was created |
| `record_date` | DATE | NOT NULL | Date of the record |
| `day_of_week` | VARCHAR(20) | NULLABLE | Day of the week (e.g., Monday, Tuesday) |
| `algo_output_price` | DECIMAL(10,4) | NULLABLE | Algorithm-suggested room price |
| `standard_price` | DECIMAL(10,4) | NULLABLE | Standard room price |
| `standard_previous_price` | DECIMAL(10,4) | NULLABLE | Previous standard room price |
| `standard_price_change` | DECIMAL(10,4) | NULLABLE | Price change amount (previous - current) |
| `competitor_set_avg_price` | DECIMAL(10,4) | NULLABLE | Average price from competitor set |
| `occupancy` | DECIMAL(5,4) | NULLABLE | Current occupancy percentage (stored as 0-1 decimal) |
| `forecasted_occupancy` | DECIMAL(5,4) | NULLABLE | Forecasted occupancy percentage (stored as 0-1 decimal) |
| `updated_by_rm` | BOOLEAN | DEFAULT FALSE | Flag indicating if updated by revenue management system |
| `revenue_per_room` | DECIMAL(10,4) | NULLABLE | Revenue per room |
| `pms_name` | VARCHAR(255) | NULLABLE | Property Management System name |
| `ly_occupancy` | DECIMAL(5,4) | NULLABLE | Last year's occupancy (year-over-year comparison) |
| `ly_adr` | DECIMAL(10,4) | NULLABLE | Last year's Average Daily Rate (year-over-year comparison) |
| `on_the_books_occ` | DECIMAL(5,4) | NULLABLE | On the books occupancy percentage |
| `arrivals_forecast` | INTEGER | NULLABLE | Forecasted number of arrivals |
| `departure_forecast` | INTEGER | NULLABLE | Forecasted number of departures |
| **`total_rooms`** | **SMALLINT UNSIGNED** | **NULLABLE** | **🆕 Total number of rooms** |
| **`ooo`** | **SMALLINT UNSIGNED** | **NULLABLE** | **🆕 Out of order rooms** |
| **`otb_rooms`** | **SMALLINT UNSIGNED** | **NULLABLE** | **🆕 On the books rooms** |
| **`avl_rooms`** | **SMALLINT UNSIGNED** | **NULLABLE** | **🆕 Available rooms** |
| `created_at` | TIMESTAMP | NULLABLE | Record creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Record last update timestamp |

---

## 🆕 New Columns (Added January 27, 2026)

The following **4 new columns** were added to track room inventory:

### 1. `total_rooms`
- **Type:** SMALLINT UNSIGNED
- **Nullable:** Yes
- **Description:** Total number of rooms in the property
- **Position:** After `departure_forecast`
- **Comment:** "Total number of rooms"

### 2. `ooo`
- **Type:** SMALLINT UNSIGNED
- **Nullable:** Yes
- **Description:** Out of order rooms (rooms that are not available for booking due to maintenance or other issues)
- **Position:** After `total_rooms`
- **Comment:** "Out of order rooms"

### 3. `otb_rooms`
- **Type:** SMALLINT UNSIGNED
- **Nullable:** Yes
- **Description:** On the books rooms (rooms that are already booked/reserved)
- **Position:** After `ooo`
- **Comment:** "On the books rooms"

### 4. `avl_rooms`
- **Type:** SMALLINT UNSIGNED
- **Nullable:** Yes
- **Description:** Available rooms (rooms that are available for booking)
- **Position:** After `otb_rooms`
- **Comment:** "Available rooms"

**Note:** All new columns are nullable to ensure backward compatibility with existing records.

---

## Indexes

| Index Name | Columns | Type |
|-----------|---------|------|
| Primary Key | `id` | PRIMARY |
| Composite Index | `property_id`, `record_date` | INDEX |
| Foreign Key Index | `scraping_run_id` | INDEX |

---

## Foreign Keys

| Column | References | On Delete | On Update |
|--------|-----------|-----------|-----------|
| `property_id` | `properties.id` | CASCADE | RESTRICT |
| `scraping_run_id` | `scraping_runs.id` | SET NULL | RESTRICT |

---

## Relationships

### Belongs To
- **Property:** `$record->property` - Returns the property that owns this record
- **ScrapingRun:** `$record->scrapingRun` - Returns the scraping run that created this record (nullable)

---

## Model Information

### Model: `App\Models\UpdateRecord`

#### Fillable Attributes
All columns listed in the table structure are fillable, including the new room inventory fields:
- `total_rooms`
- `ooo`
- `otb_rooms`
- `avl_rooms`

#### Casts
The model includes the following type casts:

**Date/Time:**
- `record_timestamp` → `datetime`
- `record_date` → `date`

**Decimal (4 decimal places):**
- `algo_output_price` → `decimal:4`
- `standard_price` → `decimal:4`
- `standard_previous_price` → `decimal:4`
- `standard_price_change` → `decimal:4`
- `competitor_set_avg_price` → `decimal:4`
- `revenue_per_room` → `decimal:4`
- `ly_adr` → `decimal:4`
- `occupancy` → `decimal:4`
- `forecasted_occupancy` → `decimal:4`
- `ly_occupancy` → `decimal:4`
- `on_the_books_occ` → `decimal:4`

**Integer:**
- `arrivals_forecast` → `integer`
- `departure_forecast` → `integer`
- **`total_rooms` → `integer`** 🆕
- **`ooo` → `integer`** 🆕
- **`otb_rooms` → `integer`** 🆕
- **`avl_rooms` → `integer`** 🆕

**Boolean:**
- `updated_by_rm` → `boolean`

---

## Migration History

1. **2025_12_08_190856** - Initial table creation
2. **2025_12_24_000002** - Added PMS name, year-over-year metrics, booking metrics, and forecast columns
3. **2025_12_26_170519** - Added `scraping_run_id` foreign key
4. **2026_01_19_124642** - Updated decimal precision from 2 to 4 decimal places for pricing and occupancy fields
5. **2026_01_27_072319** - **🆕 Added room inventory columns (`total_rooms`, `ooo`, `otb_rooms`, `avl_rooms`)**

---

## Usage Notes

### Room Inventory Fields
The new room inventory fields (`total_rooms`, `ooo`, `otb_rooms`, `avl_rooms`) allow you to track:
- Total room capacity
- Rooms out of service
- Booked rooms
- Available inventory

**Relationship:** Typically, `total_rooms = ooo + otb_rooms + avl_rooms`

### Occupancy Calculation
- `occupancy` is stored as a decimal (0-1) in the database
- For display purposes, multiply by 100 to get percentage (0-100%)
- Example: `0.14` in database = `14%` in display

### Price Fields
- All price fields use 4 decimal places for precision
- Prices are stored in the property's base currency

---

## Example Usage

```php
use App\Models\UpdateRecord;

// Create a new record with room inventory
$record = UpdateRecord::create([
    'property_id' => 1,
    'record_date' => '2026-01-27',
    'day_of_week' => 'Monday',
    'standard_price' => 125.5000,
    'occupancy' => 0.75, // 75%
    'total_rooms' => 100,
    'ooo' => 5,
    'otb_rooms' => 70,
    'avl_rooms' => 25,
]);

// Access room inventory
echo "Total Rooms: " . $record->total_rooms;
echo "Out of Order: " . $record->ooo;
echo "On the Books: " . $record->otb_rooms;
echo "Available: " . $record->avl_rooms;
```

---

## Summary of Changes

### Latest Update (January 27, 2026)
- ✅ Added 4 new room inventory columns
- ✅ All columns are nullable for backward compatibility
- ✅ Model updated with fillable attributes and casts
- ✅ Migration executed successfully

### Previous Updates
- ✅ Decimal precision increased to 4 decimal places (January 19, 2026)
- ✅ Added scraping run tracking (December 26, 2025)
- ✅ Added PMS name, year-over-year metrics, and forecast columns (December 24, 2025)

---

*Last Updated: January 27, 2026*
