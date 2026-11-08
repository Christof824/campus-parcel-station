# Architecture and Data Model

## High-Level Design

```text
Browser UI
├── Login
├── Dashboard
├── Packages
├── Pickup
└── Reports
        │ HTTP
        ▼
Flask application
├── Routes
├── Sessions and CSRF
└── Error handling
        │ Method calls
        ▼
Business services
├── parcels.py: check-in, pickup, search, fees
└── reports.py: shelf map, activity, metrics
        │ SQL
        ▼
SQLite
├── staff_users
├── packages
└── operation_logs
```

## Layer Responsibilities

### `web.py`

- Creates the Flask application
- Registers authentication and database components
- Defines page and form routes
- Applies common security headers
- Renders consistent error pages

### `auth.py`

- Creates staff accounts
- Hashes and verifies passwords
- Loads the current session user
- Protects staff routes
- Validates CSRF tokens
- Performs sign-in and sign-out

### `services/parcels.py`

- Validates parcel input
- Allocates shelf slots
- Generates pickup codes
- Calculates waiting days and fees
- Searches parcel records
- Handles check-in and pickup transactions

### `services/reports.py`

- Builds the 4-by-5 shelf map
- Calculates daily metrics
- Produces seven-day activity data
- Calculates courier distribution
- Reads recent audit entries

### `database.py`

- Opens request-scoped SQLite connections
- Closes connections after requests
- Creates tables and indexes
- Inserts safe demonstration records

## Database Tables

### `staff_users`

| Column | Purpose |
|---|---|
| `id` | Primary key |
| `username` | Case-insensitive unique login name |
| `password_hash` | PBKDF2 password hash |
| `display_name` | Staff UI name |
| `role` | `staff` or `manager` |
| `is_active` | Enables or disables login |
| `created_at` | Account creation timestamp |

### `packages`

| Column | Purpose |
|---|---|
| `id` | Primary key |
| `parcel_reference` | Optional external tracking reference |
| `pickup_code` | Unique four-digit staff/customer code |
| `courier` | Delivery company |
| `recipient` | Recipient name |
| `recipient_contact` | Optional contact |
| `shelf_slot` | Current or last shelf slot |
| `status` | `stored` or `collected` |
| `stored_at` | UTC check-in timestamp |
| `picked_up_at` | UTC collection timestamp |
| `fee_charged` | Final pickup fee |
| `notes` | Optional operational note |

### `operation_logs`

| Column | Purpose |
|---|---|
| `id` | Primary key |
| `package_id` | Related parcel, nullable after deletion |
| `action` | `check_in`, `pick_up`, and future actions |
| `message` | Human-readable audit event |
| `amount` | Related fee, if applicable |
| `created_at` | Event timestamp |

## Integrity Rules

- A partial unique index prevents two stored parcels from sharing a shelf slot.
- Pickup codes are unique across current and historical parcel records.
- Status is restricted to known values.
- Fees and operation amounts cannot be negative.
- Foreign keys are enabled for each connection.

## Transaction Strategy

Check-in and pickup begin with:

```sql
BEGIN IMMEDIATE
```

This acquires a write lock before reading mutable state, reducing the risk that
two simultaneous operations claim the same shelf slot or collect the same
parcel twice.

## Configured Business Rules

```text
Shelf rows: ABCD
Columns per row: 5
Total capacity: 20
Free storage period: 3 days
Fee after free period: $1/day
Station timezone: Australia/Sydney
```
