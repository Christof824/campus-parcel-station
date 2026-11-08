"""Database schema and seed tests."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from parcel_station import database
from parcel_station.web import create_app


class DatabaseFoundationTests(unittest.TestCase):
    """Verify schema creation and deterministic sample data."""

    def setUp(self):
        self.temp_directory = TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.sqlite"
        self.app = create_app(
            Config,
            {
                "TESTING": True,
                "DATABASE": self.database_path,
                "INSTANCE_DIR": Path(self.temp_directory.name),
            },
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_expected_tables_exist(self):
        with self.app.app_context():
            rows = database.get_db().execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            table_names = {row["name"] for row in rows}

        self.assertTrue(
            {"staff_users", "packages", "operation_logs"}.issubset(table_names)
        )

    def test_demo_seed_is_idempotent(self):
        with self.app.app_context():
            first_count = database.seed_demo_data()
            second_count = database.seed_demo_data()
            parcel_count = database.get_db().execute(
                "SELECT COUNT(*) AS count FROM packages"
            ).fetchone()["count"]

        self.assertEqual(first_count, 3)
        self.assertEqual(second_count, 0)
        self.assertEqual(parcel_count, 3)


if __name__ == "__main__":
    unittest.main()
