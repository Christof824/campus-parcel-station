# Interview Study Guide

## 60-Second Project Summary

> Campus Parcel Station is a Flask and SQLite application for managing a campus
> parcel station. Staff can securely sign in, check in parcels, search the live
> register, and confirm pickups with automatic overdue-fee calculation. The
> system maintains shelf occupancy, records an audit trail, and generates
> operational reports. I separated routes, authentication, business services,
> persistence, and reporting so each part can be tested independently.

## What You Should Be Able to Explain

### Why Flask

- Small and understandable for a portfolio application
- Python remains the primary language
- Server-rendered templates avoid unnecessary frontend complexity
- Easy to test with Flask's test client

### Why SQLite

- Built into Python
- No external database service or cost
- Supports constraints, indexes, and transactions
- Appropriate for a small single-server MVP

### Why a service layer

- Routes handle HTTP and browser flow
- Services handle business rules
- Database code stays separate
- Unit tests can call business functions directly

### Why a dictionary is still relevant

The business data is now persisted in SQLite, but dictionaries remain useful for:

- JSON-style health responses
- Counted courier statistics
- Mapping shelf slots to active packages
- Passing structured records between services and routes

### Why the shelf is a two-dimensional structure

The 4-by-5 shelf has rows and columns. Nested data mirrors the physical layout
and makes a visual occupancy map straightforward.

### How pickup codes stay unique

The database includes a unique constraint on `pickup_code`. Code generation also
checks existing records before insertion within a transaction.

### Why transactions are used

Check-in must allocate a shelf, create a parcel, and write a log together.
Pickup must update status, save the fee, and write the log together. If any step
fails, the transaction rolls back.

### What CSRF protects against

Another website could try to make the browser submit a form using an existing
staff session. The CSRF token proves the request came from the application's
own form.

### Why passwords use hashing

The database stores a one-way PBKDF2 hash. Login compares the submitted password
against that hash instead of storing the original password.

### What happens at the fee boundary

```text
Days 0-3: $0
Day 4: $1
Day 5: $2
```

Dates are compared using the `Australia/Sydney` timezone so a UTC server does
not calculate the wrong local day.

### What tests prove

- Input and database constraints work
- Shelf slots are allocated and reused correctly
- Invalid pickup codes do not crash the app
- Three-day and four-day fee boundaries work
- Authentication and CSRF protections work
- Reports handle empty and populated data
- Error pages and security headers are present

## Core Code Map

| Question | File |
|---|---|
| Where is the Flask app created? | `parcel_station/web.py` |
| Where is login handled? | `parcel_station/auth.py` |
| Where is check-in logic? | `parcel_station/services/parcels.py` |
| Where is the fee calculated? | `parcel_station/services/parcels.py` |
| Where is the shelf map built? | `parcel_station/services/reports.py` |
| Where are tables defined? | `parcel_station/schema.sql` |
| Where are tests? | `tests/` |

## Likely Interview Questions

### Why not use React?

> The main technical goal was a complete, understandable full-stack workflow.
> Server-rendered templates kept the project maintainable and allowed me to focus
> on business rules, security, persistence, and testing. React would be a good
> next step if the interface became much more interactive.

### What was the hardest bug?

> A real issue was keeping shelf state, package status, fee data, and audit history
> consistent. I solved it by moving these operations into service functions and
> wrapping check-in and pickup in database transactions.

### What happens if two staff members act simultaneously?

> SQLite uses an immediate write transaction for check-in and pickup. The
> operation sees a consistent snapshot of occupied shelves or the parcel status,
> and database constraints prevent duplicate active slots and duplicate pickup
> codes.

### What would you improve next?

- Add login rate limiting and password reset
- Add pagination and CSV export
- Add automated database backups
- Add production deployment with HTTPS
- Add more end-to-end browser tests

### What are the limitations?

> This is a single-server MVP. It is not a multi-campus production platform yet.
> It still needs operational controls such as backups, monitoring, privacy policy,
> account recovery, and stricter deployment configuration.

## Study Order

1. Run the application and perform the full workflow.
2. Read `schema.sql` and understand the three tables.
3. Read `parcels.py` from `check_in()` to `pick_up()`.
4. Read `auth.py` for session and CSRF flow.
5. Read `reports.py` for shelf and analytics generation.
6. Run one failing test by temporarily changing an expectation.
7. Practice the three-minute demo without reading code.
