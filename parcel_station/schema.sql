PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS staff_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff'
        CHECK (role IN ('staff', 'manager')),
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parcel_reference TEXT,
    pickup_code TEXT NOT NULL UNIQUE
        CHECK (
            length(pickup_code) = 4
            AND pickup_code GLOB '[0-9][0-9][0-9][0-9]'
        ),
    courier TEXT NOT NULL,
    recipient TEXT NOT NULL,
    recipient_contact TEXT,
    shelf_slot TEXT NOT NULL
        CHECK (length(shelf_slot) = 2),
    status TEXT NOT NULL DEFAULT 'stored'
        CHECK (status IN ('stored', 'collected')),
    stored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    picked_up_at TEXT,
    fee_charged REAL NOT NULL DEFAULT 0.0
        CHECK (fee_charged >= 0),
    notes TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_packages_active_shelf
    ON packages(shelf_slot)
    WHERE status = 'stored';

CREATE INDEX IF NOT EXISTS idx_packages_recipient
    ON packages(recipient);

CREATE INDEX IF NOT EXISTS idx_packages_status
    ON packages(status);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id INTEGER,
    action TEXT NOT NULL,
    message TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0.0
        CHECK (amount >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (package_id) REFERENCES packages(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_operation_logs_package
    ON operation_logs(package_id);

CREATE INDEX IF NOT EXISTS idx_operation_logs_created
    ON operation_logs(created_at);
