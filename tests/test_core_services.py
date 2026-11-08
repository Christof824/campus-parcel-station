"""Tests for parcel business rules and database mutations."""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from parcel_station import database
from parcel_station.errors import (
    InvalidPickupCodeError,
    ShelfFullError,
    ValidationError,
)
from parcel_station.services import parcels
from parcel_station.web import create_app


class ParcelServiceTests(unittest.TestCase):
    """Exercise positive, negative, and boundary parcel workflows."""

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
        self.context = self.app.app_context()
        self.context.push()
        self.now = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.context.pop()
        self.temp_directory.cleanup()

    def test_check_in_assigns_slots_and_unique_codes(self):
        first = parcels.check_in("SF Express", "Alice", now=self.now)
        second = parcels.check_in("DHL", "Bob", now=self.now)

        self.assertEqual(first["shelf_slot"], "A1")
        self.assertEqual(second["shelf_slot"], "A2")
        self.assertRegex(first["pickup_code"], r"^\d{4}$")
        self.assertNotEqual(first["pickup_code"], second["pickup_code"])

    def test_search_is_case_insensitive_and_partial(self):
        parcels.check_in("DHL", "Alice Chen", now=self.now)
        results = parcels.search_by_recipient("alice", now=self.now)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["recipient"], "Alice Chen")

    def test_three_days_are_free_and_fourth_day_costs_one_dollar(self):
        stored_at = "2026-11-01T09:00:00+00:00"
        third_day = datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc)
        fourth_day = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)

        self.assertEqual(
            parcels.calculate_storage_fee(stored_at, third_day), 0.0
        )
        self.assertEqual(
            parcels.calculate_storage_fee(stored_at, fourth_day), 1.0
        )

    def test_pickup_records_fee_and_releases_slot(self):
        parcel = parcels.check_in(
            "Australia Post",
            "Alice",
            now=datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc),
        )
        collected = parcels.pick_up(
            parcel["pickup_code"],
            now=datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc),
        )
        replacement = parcels.check_in("Toll", "Bob", now=self.now)

        self.assertEqual(collected["status"], "collected")
        self.assertEqual(collected["fee_charged"], 1.0)
        self.assertEqual(replacement["shelf_slot"], "A1")

    def test_invalid_pickup_code_is_rejected(self):
        with self.assertRaises(InvalidPickupCodeError):
            parcels.pick_up("0000", now=self.now)

    def test_empty_courier_is_rejected(self):
        with self.assertRaises(ValidationError):
            parcels.check_in("", "Alice", now=self.now)

    def test_twenty_first_parcel_is_rejected(self):
        for number in range(20):
            parcels.check_in("DHL", f"Person {number}", now=self.now)

        with self.assertRaises(ShelfFullError):
            parcels.check_in("DHL", "Extra parcel", now=self.now)

    def test_operation_history_is_recorded(self):
        parcel = parcels.check_in("DHL", "Alice", now=self.now)
        parcels.pick_up(parcel["pickup_code"], now=self.now)
        rows = database.get_db().execute(
            "SELECT action FROM operation_logs ORDER BY id"
        ).fetchall()

        self.assertEqual([row["action"] for row in rows], ["check_in", "pick_up"])


if __name__ == "__main__":
    unittest.main()
