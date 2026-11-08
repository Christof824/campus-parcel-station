"""Staff authentication and session tests."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from parcel_station.auth import create_staff_user
from parcel_station.web import create_app


class AuthenticationTests(unittest.TestCase):
    """Verify protected access and the staff login lifecycle."""

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

    def tearDown(self):
        self.temp_directory.cleanup()

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def login(self):
        self.client.get("/login")
        return self.client.post(
            "/login",
            data={
                "username": "staff_demo",
                "password": "StrongPass123!",
                "csrf_token": self.csrf_token(),
            },
            follow_redirects=True,
        )

    def test_protected_page_redirects_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/login"))

    def test_valid_login_reaches_dashboard(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Good to see you", response.data)
        self.assertIn(b"Operations overview", response.data)

    def test_wrong_password_is_rejected(self):
        self.client.get("/login")
        response = self.client.post(
            "/login",
            data={
                "username": "staff_demo",
                "password": "WrongPassword",
                "csrf_token": self.csrf_token(),
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Incorrect username or password", response.data)

    def test_logout_clears_session(self):
        self.login()
        dashboard = self.client.get("/")
        token = self.csrf_token()
        response = self.client.post(
            "/logout",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Staff sign in", response.data)
        protected = self.client.get("/")
        self.assertEqual(protected.status_code, 302)

    def test_login_rejects_missing_csrf_token(self):
        response = self.client.post(
            "/login",
            data={"username": "staff_demo", "password": "StrongPass123!"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
