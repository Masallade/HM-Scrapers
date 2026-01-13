# Database Schema

## Tables

### `properties`
**Description:** Stores core information about hotel properties in the system. Each property represents a hotel with its unique identifier, name, and optional integration details (BFI, PMS, BDC systems).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `property_code` | VARCHAR(50) | UNIQUE, NOT NULL | Unique property identifier |
| `hotel_name` | VARCHAR(255) | NOT NULL | Hotel name |
| `bfi_property_id` | VARCHAR(100) | NULLABLE | BFI system property ID |
| `bfi_property_name` | VARCHAR(255) | NULLABLE | BFI system property name |
| `pms_name` | VARCHAR(255) | NULLABLE | Property Management System name |
| `pms_id` | VARCHAR(100) | NULLABLE | PMS identifier |
| `bdc_property_name` | VARCHAR(255) | NULLABLE | Booking Distribution Channel property name |
| `bdc_property_id` | VARCHAR(100) | NULLABLE | BDC property identifier |
| `city` | VARCHAR(100) | NULLABLE | Property city |
| `state` | VARCHAR(100) | NULLABLE | Property state |
| `owner_name` | VARCHAR(255) | NULLABLE | Property owner name |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

**Relationships:**
- Has Many: `properties_characteristics_history`
- Has Many: `update_records`
- Belongs To Many: `hotel_pms_platforms` (via `property_hotel_pms_platform`)

---

### `hotel_pms_platforms`
**Description:** Stores PMS (Property Management System) platform credentials and configurations. These platforms are independent entities that can be shared across multiple properties. Each platform contains login credentials (encrypted), status, and scraping metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `platform_name` | VARCHAR(100) | NOT NULL | Platform name (e.g., Choice MAX, Wyndham) |
| `username` | VARCHAR(255) | NULLABLE | Platform username |
| `email` | VARCHAR(255) | NULLABLE | Platform email |
| `password` | TEXT | NOT NULL | Encrypted password |
| `status` | ENUM | DEFAULT 'active' | Status: active, inactive |
| `last_scraped_at` | TIMESTAMP | NULLABLE | Last scraping timestamp |
| `config` | JSON | NULLABLE | Platform-specific configuration |
| `notes` | TEXT | NULLABLE | Additional notes |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

**Relationships:**
- Belongs To Many: `properties` (via `property_hotel_pms_platform`)
- Has Many: `scraping_runs`

---

### `property_hotel_pms_platform` (Pivot Table)
**Description:** Junction table that establishes the many-to-many relationship between properties and PMS platforms. Allows multiple properties to use the same platform account, and enables one property to use multiple platforms.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `property_id` | BIGINT | FOREIGN KEY → properties.id | Property reference |
| `hotel_pms_platform_id` | BIGINT | FOREIGN KEY → hotel_pms_platforms.id | Platform reference |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

**Unique Constraint:** `(property_id, hotel_pms_platform_id)`

---

### `scraping_runs`
**Description:** Tracks each scraping session executed for a PMS platform. Records when scraping started, completed, status, number of days scraped, and how many update records were created. Used for monitoring and debugging scraping operations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `hotel_pms_platform_id` | BIGINT | FOREIGN KEY → hotel_pms_platforms.id | Platform reference |
| `started_at` | TIMESTAMP | NOT NULL | Scraping start time |
| `completed_at` | TIMESTAMP | NULLABLE | Scraping completion time |
| `status` | ENUM | DEFAULT 'running' | Status: running, completed, failed |
| `days_scraped` | INTEGER | DEFAULT 0 | Number of days scraped |
| `records_created` | INTEGER | DEFAULT 0 | Number of update records created |
| `error_message` | TEXT | NULLABLE | Error message if failed |
| `metadata` | JSON | NULLABLE | Additional run metadata |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

**Relationships:**
- Belongs To: `hotel_pms_platforms`
- Has Many: `update_records`

---

### `update_records`
**Description:** Stores daily pricing, occupancy, and revenue management metrics for each property. Contains pricing data (algorithm output, standard price, competitor prices), occupancy metrics, forecasts, and year-over-year comparisons. Records can be linked to scraping runs or manually entered.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `property_id` | BIGINT | FOREIGN KEY → properties.id | Property reference |
| `scraping_run_id` | BIGINT | FOREIGN KEY → scraping_runs.id | Scraping run reference (nullable) |
| `record_timestamp` | TIMESTAMP | NULLABLE | Exact record timestamp |
| `record_date` | DATE | NOT NULL | Record date |
| `day_of_week` | VARCHAR(20) | NULLABLE | Day of week |
| `algo_output_price` | DECIMAL(10,2) | NULLABLE | Algorithm suggested price |
| `standard_price` | DECIMAL(10,2) | NULLABLE | Standard room price |
| `standard_previous_price` | DECIMAL(10,2) | NULLABLE | Previous standard price |
| `standard_price_change` | DECIMAL(10,2) | NULLABLE | Price change amount |
| `competitor_set_avg_price` | DECIMAL(10,2) | NULLABLE | Competitor average price |
| `occupancy` | DECIMAL(5,2) | NULLABLE | Occupancy percentage (0-100) |
| `forecasted_occupancy` | DECIMAL(5,2) | NULLABLE | Forecasted occupancy |
| `updated_by_rm` | BOOLEAN | DEFAULT false | Updated by Revenue Manager flag |
| `revenue_per_room` | DECIMAL(10,2) | NULLABLE | Revenue per room (RevPAR) |
| `pms_name` | VARCHAR(255) | NULLABLE | PMS name |
| `ly_occupancy` | DECIMAL(5,2) | NULLABLE | Last year occupancy |
| `ly_adr` | DECIMAL(10,2) | NULLABLE | Last year Average Daily Rate |
| `on_the_books_occ` | DECIMAL(5,2) | NULLABLE | On-the-books occupancy |
| `arrivals_forecast` | INTEGER | NULLABLE | Forecasted arrivals |
| `departure_forecast` | INTEGER | NULLABLE | Forecasted departures |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

**Relationships:**
- Belongs To: `properties`
- Belongs To: `scraping_runs` (nullable)

---

### `properties_characteristics_history`
**Description:** Maintains historical records of room inventory characteristics for each property. Tracks physical capacity, out-of-order rooms, booked rooms, and calculates saleable rooms over time. Records become read-only after 24 hours to preserve historical accuracy.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `property_id` | BIGINT | FOREIGN KEY → properties.id | Property reference |
| `record_date` | DATE | NOT NULL | Record date |
| `physical_capacity` | INTEGER UNSIGNED | NOT NULL | Total physical rooms |
| `out_of_order` | INTEGER UNSIGNED | DEFAULT 0 | Out-of-order rooms |
| `on_book` | INTEGER UNSIGNED | DEFAULT 0 | Currently booked rooms |
| `saleable_rooms` | INTEGER UNSIGNED | NOT NULL | Saleable rooms (calculated) |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

**Relationships:**
- Belongs To: `properties`

**Index:** `(property_id, record_date)`

---

### `deleted_properties`
**Description:** Implements soft-delete functionality for properties. When a property is deleted, it's moved here with snapshots of related data (characteristics and update records). Records are retained for 30 days before permanent deletion, allowing for recovery if needed.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `original_id` | BIGINT | NOT NULL | Original property ID |
| `property_code` | VARCHAR(50) | NOT NULL | Property code |
| `hotel_name` | VARCHAR(255) | NOT NULL | Hotel name |
| `original_created_at` | TIMESTAMP | NULLABLE | Original creation timestamp |
| `original_updated_at` | TIMESTAMP | NULLABLE | Original update timestamp |
| `deleted_at` | TIMESTAMP | NOT NULL | Deletion timestamp |
| `characteristics_data` | JSON | NULLABLE | Snapshot of characteristics data |
| `update_records_data` | JSON | NULLABLE | Snapshot of update records data |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

**Index:** `deleted_at` (for cleanup queries)

---

### `users`
**Description:** Manages system users and authentication. Supports role-based access control (admin/user). Only admin users can access the system. Used for login, session management, and authorization.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY | Auto-increment ID |
| `name` | VARCHAR(255) | NOT NULL | User name |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User email |
| `role` | VARCHAR(255) | DEFAULT 'user' | User role (admin, user) |
| `email_verified_at` | TIMESTAMP | NULLABLE | Email verification timestamp |
| `password` | VARCHAR(255) | NOT NULL | Hashed password |
| `remember_token` | VARCHAR(100) | NULLABLE | Remember token |
| `created_at` | TIMESTAMP | NULLABLE | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Update timestamp |

---

## Relationships Summary

```
Properties (1) ──< (Many) Properties Characteristics History
Properties (1) ──< (Many) Update Records
Properties (Many) ──< (Many) Hotel PMS Platforms (via pivot)
Hotel PMS Platforms (1) ──< (Many) Scraping Runs
Scraping Runs (1) ──< (Many) Update Records
```

---

## Key Points

- **Many-to-Many:** Properties ↔ Hotel PMS Platforms (via `property_hotel_pms_platform` pivot table)
- **One-to-Many:** Property → Characteristics History, Update Records
- **One-to-Many:** Hotel PMS Platform → Scraping Runs
- **One-to-Many:** Scraping Run → Update Records
- **Soft Delete:** Deleted properties stored in `deleted_properties` for 30-day retention
- **Historical Protection:** Characteristics and Update Records become read-only after 24 hours

