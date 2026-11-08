"""Parcel check-in, collection, search, and fee calculations."""

import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from flask import current_app

from parcel_station.database import get_db
from parcel_station.errors import (
    InvalidPickupCodeError,
    ShelfFullError,
    ValidationError,
)


def _clean_required(value: object, field_name: str, maximum_length: int) -> str:
    """Normalise and validate a required text field."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be text.")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty.")
    if len(cleaned) > maximum_length:
        raise ValidationError(
            f"{field_name} must be {maximum_length} characters or fewer."
        )
    return cleaned


def _clean_optional(value: object, maximum_length: int) -> str:
    """Normalise an optional text field."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("Optional contact information must be text.")
    cleaned = " ".join(value.split())
    if len(cleaned) > maximum_length:
        raise ValidationError(
            f"Contact information must be {maximum_length} characters or fewer."
        )
    return cleaned


def _now(value: Optional[datetime] = None) -> datetime:
    """Return an aware UTC timestamp."""
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp from SQLite."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def calculate_waiting_days(
    stored_at: str, now: Optional[datetime] = None
) -> int:
    """Calculate completed calendar days since parcel storage."""
    local_zone = ZoneInfo(current_app.config["TIME_ZONE"])
    stored_date = _parse_timestamp(stored_at).astimezone(local_zone).date()
    current_date = _now(now).astimezone(local_zone).date()
    return max(0, (current_date - stored_date).days)


def calculate_storage_fee(
    stored_at: str, now: Optional[datetime] = None
) -> float:
    """Calculate the fee after the free storage period."""
    waiting_days = calculate_waiting_days(stored_at, now)
    extra_days = waiting_days - int(current_app.config["FREE_STORAGE_DAYS"])
    if extra_days <= 0:
        return 0.0
    return extra_days * float(current_app.config["FEE_PER_EXTRA_DAY"])


def _active_slots() -> set:
    """Return shelf slots currently occupied by stored parcels."""
    rows = get_db().execute(
        "SELECT shelf_slot FROM packages WHERE status = 'stored'"
    ).fetchall()
    return {row["shelf_slot"] for row in rows}


def find_free_slot() -> Optional[str]:
    """Return the first free shelf slot, or None when the shelf is full."""
    occupied = _active_slots()
    row_names = current_app.config["SHELF_ROWS"]
    column_count = int(current_app.config["SHELF_COLUMNS"])

    for row_name in row_names:
        for column_number in range(1, column_count + 1):
            slot = f"{row_name}{column_number}"
            if slot not in occupied:
                return slot
    return None


def generate_pickup_code() -> str:
    """Generate a unique four-digit pickup code."""
    connection = get_db()
    while True:
        code = str(secrets.randbelow(9000) + 1000)
        exists = connection.execute(
            "SELECT 1 FROM packages WHERE pickup_code = ?",
            (code,),
        ).fetchone()
        if exists is None:
            return code


def _decorate_package(row, now: Optional[datetime] = None) -> Dict[str, object]:
    """Convert a database row into a presentation-safe package dictionary."""
    package = dict(row)
    package["waiting_days"] = calculate_waiting_days(
        package["stored_at"], now
    )
    package["is_overdue"] = (
        package["status"] == "stored"
        and package["waiting_days"]
        > int(current_app.config["FREE_STORAGE_DAYS"])
    )
    package["fee_due"] = (
        calculate_storage_fee(package["stored_at"], now)
        if package["status"] == "stored"
        else float(package["fee_charged"])
    )
    return package


def check_in(
    courier: object,
    recipient: object,
    recipient_contact: object = "",
    parcel_reference: object = "",
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """Create a parcel and atomically reserve its first available shelf slot."""
    courier_name = _clean_required(courier, "Courier", 40)
    recipient_name = _clean_required(recipient, "Recipient", 80)
    contact = _clean_optional(recipient_contact, 120)
    reference = _clean_optional(parcel_reference, 80)
    timestamp = _now(now).isoformat()
    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")
        occupied = {
            row["shelf_slot"]
            for row in connection.execute(
                "SELECT shelf_slot FROM packages WHERE status = 'stored'"
            ).fetchall()
        }
        row_names = current_app.config["SHELF_ROWS"]
        column_count = int(current_app.config["SHELF_COLUMNS"])
        slot = None
        for row_name in row_names:
            for column_number in range(1, column_count + 1):
                candidate = f"{row_name}{column_number}"
                if candidate not in occupied:
                    slot = candidate
                    break
            if slot is not None:
                break

        if slot is None:
            raise ShelfFullError("The parcel shelf is full.")

        pickup_code = generate_pickup_code()
        cursor = connection.execute(
            """
            INSERT INTO packages (
                parcel_reference,
                pickup_code,
                courier,
                recipient,
                recipient_contact,
                shelf_slot,
                stored_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference or None,
                pickup_code,
                courier_name,
                recipient_name,
                contact or None,
                slot,
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO operation_logs (package_id, action, message)
            VALUES (?, 'check_in', ?)
            """,
            (
                cursor.lastrowid,
                f"Parcel {pickup_code} checked in at {slot}.",
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    row = connection.execute(
        "SELECT * FROM packages WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _decorate_package(row, now)


def list_packages(
    status: Optional[str] = None, now: Optional[datetime] = None
) -> List[Dict[str, object]]:
    """Return parcel records ordered by most recent storage."""
    connection = get_db()
    if status in {"stored", "collected"}:
        rows = connection.execute(
            "SELECT * FROM packages WHERE status = ? ORDER BY stored_at DESC",
            (status,),
        ).fetchall()
    elif status in {None, "", "all", "overdue"}:
        rows = connection.execute(
            "SELECT * FROM packages ORDER BY stored_at DESC"
        ).fetchall()
    else:
        raise ValidationError("Unknown parcel status filter.")
    packages = [_decorate_package(row, now) for row in rows]
    if status == "overdue":
        packages = [package for package in packages if package["is_overdue"]]
    return packages


def search_packages(
    query: object,
    status: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[Dict[str, object]]:
    """Search parcel reference, pickup code, courier, or recipient."""
    search_text = _clean_required(query, "Parcel search", 80)
    connection = get_db()
    rows = connection.execute(
        """
        SELECT *
        FROM packages
        WHERE instr(
            lower(
                courier || ' ' ||
                recipient || ' ' ||
                pickup_code || ' ' ||
                COALESCE(parcel_reference, '')
            ),
            lower(?)
        ) > 0
        ORDER BY stored_at DESC
        """,
        (search_text,),
    ).fetchall()
    packages = [_decorate_package(row, now) for row in rows]
    if status in {"stored", "collected"}:
        packages = [
            package for package in packages if package["status"] == status
        ]
    elif status == "overdue":
        packages = [package for package in packages if package["is_overdue"]]
    elif status not in {None, "", "all"}:
        raise ValidationError("Unknown parcel status filter.")
    return packages


def search_by_recipient(
    query: object, include_collected: bool = True, now: Optional[datetime] = None
) -> List[Dict[str, object]]:
    """Search recipients using a case-insensitive partial match."""
    search_text = _clean_required(query, "Recipient search", 80)
    connection = get_db()
    status_clause = "" if include_collected else "AND status = 'stored'"
    rows = connection.execute(
        f"""
        SELECT *
        FROM packages
        WHERE instr(lower(recipient), lower(?)) > 0
        {status_clause}
        ORDER BY stored_at DESC
        """,
        (search_text,),
    ).fetchall()
    return [_decorate_package(row, now) for row in rows]


def find_stored_package(
    code: object, now: Optional[datetime] = None
) -> Dict[str, object]:
    """Return a stored parcel without changing its state."""
    if not isinstance(code, str):
        raise ValidationError("Pickup code must be text.")
    cleaned_code = code.strip()
    if len(cleaned_code) != 4 or not cleaned_code.isdigit():
        raise InvalidPickupCodeError("The pickup code must contain four digits.")
    row = get_db().execute(
        """
        SELECT *
        FROM packages
        WHERE pickup_code = ? AND status = 'stored'
        """,
        (cleaned_code,),
    ).fetchone()
    if row is None:
        raise InvalidPickupCodeError(
            "No stored parcel matches this pickup code."
        )
    return _decorate_package(row, now)


def pick_up(code: object, now: Optional[datetime] = None) -> Dict[str, object]:
    """Collect a stored parcel and atomically record its fee."""
    if not isinstance(code, str):
        raise ValidationError("Pickup code must be text.")
    cleaned_code = code.strip()
    if len(cleaned_code) != 4 or not cleaned_code.isdigit():
        raise InvalidPickupCodeError("The pickup code must contain four digits.")

    timestamp = _now(now)
    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT *
            FROM packages
            WHERE pickup_code = ? AND status = 'stored'
            """,
            (cleaned_code,),
        ).fetchone()
        if row is None:
            raise InvalidPickupCodeError(
                "No stored parcel matches this pickup code."
            )

        fee = calculate_storage_fee(row["stored_at"], timestamp)
        connection.execute(
            """
            UPDATE packages
            SET status = 'collected',
                picked_up_at = ?,
                fee_charged = ?
            WHERE id = ?
            """,
            (timestamp.isoformat(), fee, row["id"]),
        )
        connection.execute(
            """
            INSERT INTO operation_logs (
                package_id,
                action,
                message,
                amount
            )
            VALUES (?, 'pick_up', ?, ?)
            """,
            (
                row["id"],
                f"Parcel {cleaned_code} collected. Fee charged: ${fee:.2f}.",
                fee,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    collected_row = connection.execute(
        "SELECT * FROM packages WHERE id = ?", (row["id"],)
    ).fetchone()
    return _decorate_package(collected_row, timestamp)
