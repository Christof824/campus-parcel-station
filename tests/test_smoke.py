"""Smoke tests for the initial Flask foundation."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from parcel_station.web import create_app


class FoundationSmokeTests(unittest.TestCase):
    """Verify that the project shell serves expected responses."""

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

    def test_home_page_requires_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_login_page_loads(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Staff sign in", response.data)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["stage"], "hardened-release")
        self.assertEqual(payload["database"], "ready")


if __name__ == "__main__":
    unittest.main()
