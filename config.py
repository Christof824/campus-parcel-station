"""Application configuration."""

import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Default local-development configuration."""

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "local-development-only-change-before-public-deployment",
    )
    APP_NAME = "Campus Parcel Station"
    APP_VERSION = "0.7.0"
    INSTANCE_DIR = BASE_DIR / "instance"
    DATABASE = INSTANCE_DIR / "parcel_station.sqlite"
    SHELF_ROWS = "ABCD"
    SHELF_COLUMNS = 5
    FREE_STORAGE_DAYS = 3
    FEE_PER_EXTRA_DAY = 1.0
    TIME_ZONE = "Australia/Sydney"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 1024 * 1024
