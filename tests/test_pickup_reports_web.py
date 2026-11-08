"""Tests for pickup confirmation, shelf maps, and reports."""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from parcel_station.auth import create_staff_user
from parcel_station.database import get_db
from parcel_station.services import parcels
from parcel_station.web import create_app


class PickupAndReportTests(unittest.TestCase):
    """Verify the browser completes the operational workflow."""

    def setUp(self):
        self.temp_directory = TemporaryDirectory()
        self.app = create_app(
            Config,
            {
                "TESTING": True,
                "DATABASE": Path(self.temp_directory.name) / "test.sqlite",
                "INSTANCE_DIR": Path(self.temp_directory.name),
            },
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            create_staff_user("staff_demo", "Demo Staff", "StrongPass123!")
            self.parcel = parcels.check_in(
                "DHL",
                "Pickup Demo",
                now=datetime.now(timezone.utc) - timedelta(days=4),
            )

        self.client.get("/login")
        self.client.post(
            "/login",
            data={
                "username": "staff_demo",
                "password": "StrongPass123!",
                "csrf_token": self.csrf_token(),
            },
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def test_pickup_lookup_finds_parcel(self):
        self.client.get("/pickup")
        response = self.client.post(
            "/pickup/lookup",
            data={
                "csrf_token": self.csrf_token(),
                "pickup_code": self.parcel["pickup_code"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pickup Demo", response.data)
        self.assertIn(b"PARCEL FOUND", response.data)

    def test_pickup_confirmation_collects_parcel(self):
        self.client.get("/pickup")
        response = self.client.post(
            "/pickup/confirm",
            data={
                "csrf_token": self.csrf_token(),
                "pickup_code": self.parcel["pickup_code"],
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"collected from A1", response.data)

        with self.app.app_context():
            row = get_db().execute(
                "SELECT status, fee_charged FROM packages WHERE id = ?",
                (self.parcel["id"],),
            ).fetchone()
        self.assertEqual(row["status"], "collected")
        self.assertGreaterEqual(row["fee_charged"], 1.0)

    def test_invalid_pickup_code_shows_error(self):
        self.client.get("/pickup")
        response = self.client.post(
            "/pickup/lookup",
            data={"csrf_token": self.csrf_token(), "pickup_code": "0000"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"No stored parcel matches", response.data)

    def test_reports_page_contains_shelf_and_statistics(self):
        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Daily operations at a glance", response.data)
        self.assertIn(b"Live occupancy", response.data)
        self.assertIn(b"Pickup Demo", response.data)
        self.assertIn(b"Parcel activity", response.data)


if __name__ == "__main__":
    unittest.main()
