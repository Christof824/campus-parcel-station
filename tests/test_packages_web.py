"""Tests for browser parcel check-in and search routes."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from parcel_station.auth import create_staff_user
from parcel_station.database import get_db
from parcel_station.web import create_app


class PackagePageTests(unittest.TestCase):
    """Verify parcel forms connect to the tested business service."""

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
        self.client.get("/login")
        self.token = self.csrf_token()
        self.client.post(
            "/login",
            data={
                "username": "staff_demo",
                "password": "StrongPass123!",
                "csrf_token": self.token,
            },
        )
        self.client.get("/packages")

    def tearDown(self):
        self.temp_directory.cleanup()

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def test_package_page_loads(self):
        response = self.client.get("/packages")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Register and locate parcels", response.data)

    def test_check_in_form_creates_parcel(self):
        response = self.client.post(
            "/packages/check-in",
            data={
                "csrf_token": self.csrf_token(),
                "courier": "Australia Post",
                "recipient": "Alice",
                "recipient_contact": "alice@example.test",
                "parcel_reference": "AUS-1001",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"checked in at A1", response.data)
        self.assertIn(b"Alice", response.data)

        with self.app.app_context():
            row = get_db().execute(
                "SELECT recipient, shelf_slot FROM packages"
            ).fetchone()
        self.assertEqual(row["recipient"], "Alice")
        self.assertEqual(row["shelf_slot"], "A1")

    def test_invalid_check_in_shows_error(self):
        response = self.client.post(
            "/packages/check-in",
            data={
                "csrf_token": self.csrf_token(),
                "courier": "",
                "recipient": "Alice",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Courier cannot be empty", response.data)

    def test_search_by_courier(self):
        self.client.post(
            "/packages/check-in",
            data={
                "csrf_token": self.csrf_token(),
                "courier": "SF Express",
                "recipient": "Chen",
            },
        )
        response = self.client.get("/packages?q=SF")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Chen", response.data)

    def test_status_filter_rejects_empty_results(self):
        response = self.client.get("/packages?status=collected")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No matching parcels", response.data)


if __name__ == "__main__":
    unittest.main()
