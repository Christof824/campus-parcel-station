# Three-Minute Demo Script

## Before Presenting

1. Start the application with `python3 app.py`.
2. Open `http://127.0.0.1:5001`.
3. Sign in with the local staff account.
4. Close private tabs and notifications.
5. Show the dashboard, not source code.

## 0:00-0:25 Introduction

> Hi everyone, my project is Campus Parcel Station. It is a browser-based
> parcel management system for campus parcel-station staff and students.

## 0:25-0:50 Problem and solution

> Staff need a reliable way to record parcels, assign shelf space, calculate
> overdue fees, and release shelf positions. The system connects all of these
> steps in one workflow instead of maintaining separate paper or spreadsheet
> records.

## 0:50-1:05 Architecture

> I used Flask for the web application, SQLite for persistence, and server-side
> business services for parcel rules. Staff pages are protected with hashed
> passwords, sessions, and CSRF tokens.

## 1:05-1:35 Check in a parcel

1. Open **Packages**.
2. Enter a courier and demo recipient.
3. Submit the form.

> The system validates the input, finds the first available shelf position,
> generates a unique pickup code, writes the parcel, and creates an audit log.

Point to the success message and the new table row.

## 1:35-2:10 Pick up and charge a fee

1. Open **Pickup**.
2. Enter the code of an overdue demonstration parcel.
3. Show recipient, shelf, waiting days, and fee.
4. Confirm collection.

> The first three days are free, and each additional day costs one dollar.
> Confirming pickup records the fee, marks the parcel as collected, and releases
> the shelf position.

## 2:10-2:35 Reports and shelf map

1. Open **Reports**.
2. Point to the released shelf position.
3. Show today's check-ins, pickups, overdue rate, and revenue.

> The shelf is a four-by-five resource map. The report combines current package
> state with audit history and produces operational statistics.

## 2:35-2:55 Advanced concepts

> The project uses object-oriented service boundaries, dictionary-based data
> access, multi-dimensional shelf state, exception handling, SQLite transactions,
> authentication, file-backed persistence, and automated testing.

## 2:55-3:00 Close

> The complete flow is check-in, pickup, fee collection, shelf release, and
> reporting. Thank you.

## Emergency Fallback

If a form cannot be submitted during the presentation:

> I will show the test suite and the existing records instead of changing code
> during the demonstration.

Run:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
