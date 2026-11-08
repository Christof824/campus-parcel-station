"""Operational statistics and shelf-map generation."""

from collections import Counter
from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from flask import current_app

from parcel_station.database import get_db
from parcel_station.services import parcels


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp and make it timezone-aware."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _local_now(now: Optional[datetime] = None) -> datetime:
    """Return the current timestamp in the configured station timezone."""
    if now is None:
        current = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        current = now.replace(tzinfo=timezone.utc)
    else:
        current = now.astimezone(timezone.utc)
    return current.astimezone(ZoneInfo(current_app.config["TIME_ZONE"]))


def build_shelf_map(
    package_records: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    """Build a four-row, five-column shelf map."""
    active_by_slot = {
        package["shelf_slot"]: package
        for package in package_records
        if package["status"] == "stored"
    }
    rows = []
    for row_name in current_app.config["SHELF_ROWS"]:
        cells = []
        for column_number in range(
            1, int(current_app.config["SHELF_COLUMNS"]) + 1
        ):
            slot = f"{row_name}{column_number}"
            cells.append(
                {
                    "slot": slot,
                    "occupied": slot in active_by_slot,
                    "package": active_by_slot.get(slot),
                }
            )
        rows.append({"row": row_name, "cells": cells})
    return rows


def build_operations_report(
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """Build metrics, daily activity, shelf state, and recent logs."""
    current = _local_now(now)
    package_records = parcels.list_packages(now=now)
    active = [
        package for package in package_records if package["status"] == "stored"
    ]
    overdue = [package for package in active if package["is_overdue"]]
    total_slots = (
        len(current_app.config["SHELF_ROWS"])
        * int(current_app.config["SHELF_COLUMNS"])
    )

    courier_counts = Counter(
        package["courier"] for package in active
    ).most_common()

    today = current.date()
    daily_activity = []
    for days_ago in range(6, -1, -1):
        target_date = today.fromordinal(today.toordinal() - days_ago)
        check_ins = sum(
            1
            for package in package_records
            if _parse_timestamp(package["stored_at"])
            .astimezone(current.tzinfo)
            .date()
            == target_date
        )
        pickups = sum(
            1
            for package in package_records
            if package["picked_up_at"]
            and _parse_timestamp(package["picked_up_at"])
            .astimezone(current.tzinfo)
            .date()
            == target_date
        )
        daily_activity.append(
            {
                "date": target_date,
                "label": target_date.strftime("%a"),
                "check_ins": check_ins,
                "pickups": pickups,
            }
        )

    max_activity = max(
        [day["check_ins"] + day["pickups"] for day in daily_activity] + [1]
    )
    for day in daily_activity:
        day["total"] = day["check_ins"] + day["pickups"]
        day["height"] = max(
            6,
            round(day["total"] / max_activity * 100),
        )

    today_check_ins = daily_activity[-1]["check_ins"]
    today_pickups = daily_activity[-1]["pickups"]
    fees_today = sum(
        float(package["fee_charged"])
        for package in package_records
        if package["picked_up_at"]
        and _parse_timestamp(package["picked_up_at"])
        .astimezone(current.tzinfo)
        .date()
        == today
    )
    fees_total = sum(
        float(package["fee_charged"])
        for package in package_records
        if package["status"] == "collected"
    )

    recent_logs = get_db().execute(
        """
        SELECT action, message, amount, created_at
        FROM operation_logs
        ORDER BY id DESC
        LIMIT 8
        """
    ).fetchall()

    return {
        "generated_at": current,
        "packages": package_records,
        "active_count": len(active),
        "overdue_count": len(overdue),
        "available_slots": max(0, total_slots - len(active)),
        "total_slots": total_slots,
        "occupancy_rate": (
            round(len(active) / total_slots * 100, 1) if total_slots else 0.0
        ),
        "overdue_rate": (
            round(len(overdue) / len(active) * 100, 1) if active else 0.0
        ),
        "today_check_ins": today_check_ins,
        "today_pickups": today_pickups,
        "fees_today": fees_today,
        "fees_total": fees_total,
        "courier_counts": courier_counts,
        "daily_activity": daily_activity,
        "shelf_rows": build_shelf_map(package_records),
        "recent_logs": recent_logs,
    }
