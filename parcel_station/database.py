"""SQLite connection management and database setup."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from flask import current_app, g


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_db():
    """Return the request-scoped SQLite connection."""
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_error=None):
    """Close the SQLite connection at the end of a request."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    """Create missing database tables and indexes."""
    connection = get_db()
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


def seed_demo_data():
    """Insert deterministic, non-sensitive demonstration parcels once."""
    connection = get_db()
    existing_count = connection.execute(
        "SELECT COUNT(*) AS count FROM packages"
    ).fetchone()["count"]
    if existing_count:
        return 0

    now = datetime.now(timezone.utc)
    demo_packages = [
        (
            "DEMO-SF-1001",
            "9101",
            "SF Express",
            "Demo Alice",
            "demo-alice@example.test",
            "A1",
            (now - timedelta(days=1)).isoformat(),
            "Safe demonstration record.",
        ),
        (
            "DEMO-DHL-1002",
            "9102",
            "DHL",
            "Demo Chen",
            "demo-chen@example.test",
            "A2",
            (now - timedelta(days=4)).isoformat(),
            "Safe demonstration record.",
        ),
        (
            "DEMO-AP-1003",
            "9103",
            "Australia Post",
            "Demo Mia",
            "demo-mia@example.test",
            "B1",
            (now - timedelta(days=6)).isoformat(),
            "Safe demonstration record.",
        ),
    ]

    with connection:
        for package in demo_packages:
            cursor = connection.execute(
                """
                INSERT INTO packages (
                    parcel_reference,
                    pickup_code,
                    courier,
                    recipient,
                    recipient_contact,
                    shelf_slot,
                    stored_at,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                package,
            )
            connection.execute(
                """
                INSERT INTO operation_logs (package_id, action, message)
                VALUES (?, 'check_in', ?)
                """,
                (
                    cursor.lastrowid,
                    f"Demo parcel {package[1]} checked in at {package[5]}.",
                ),
            )
    return len(demo_packages)


def database_status():
    """Return a lightweight database readiness description."""
    try:
        get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return "unavailable"
    return "ready"


def init_app(app):
    """Register database lifecycle hooks and Flask CLI commands."""
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.cli.command("init-db")
    def init_db_command():
        """Create all missing tables and indexes."""
        init_db()
        click.echo(f"Initialized database: {current_app.config['DATABASE']}")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Insert safe demonstration records if the database is empty."""
        inserted = seed_demo_data()
        click.echo(f"Inserted {inserted} demonstration parcel(s).")
