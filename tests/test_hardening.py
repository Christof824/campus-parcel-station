"""Security-header, error-page, and empty-state regression tests."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from parcel_station.auth import create_staff_user
from parcel_station.services.reports import build_operations_report
from parcel_station.web import create_app


class HardeningTests(unittest.TestCase):
    """Verify final resilience and browser security behaviour."""

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

    def tearDown(self):
        self.temp_directory.cleanup()

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session.get("_csrf_token")

    def login(self):
        self.client.get("/login")
        with self.app.app_context():
            create_staff_user("empty_staff", "Empty Staff", "StrongPass123!")
        self.client.post(
            "/login",
            data={
                "username": "empty_staff",
                "password": "StrongPass123!",
                "csrf_token": self.csrf_token(),
            },
        )

    def test_security_headers_are_present(self):
        response = self.client.get("/login")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_unknown_page_has_styled_404(self):
        response = self.client.get("/missing-page")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"This page does not exist", response.data)

    def test_invalid_csrf_has_styled_400(self):
        response = self.client.post(
            "/login",
            data={"username": "nobody", "password": "nothing"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"REQUEST NOT COMPLETED", response.data)

    def test_empty_station_report_has_zeroed_metrics(self):
        with self.app.app_context():
            report = build_operations_report()
        self.assertEqual(report["active_count"], 0)
        self.assertEqual(report["overdue_count"], 0)
        self.assertEqual(report["fees_total"], 0.0)
        self.assertEqual(len(report["shelf_rows"]), 4)
        self.assertEqual(len(report["shelf_rows"][0]["cells"]), 5)

    def test_empty_dashboard_renders_empty_state(self):
        self.login()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No activity yet", response.data)


if __name__ == "__main__":
    unittest.main()
