"""Domain-specific errors for parcel station operations."""


class ParcelStationError(Exception):
    """Base error for expected parcel station business failures."""


class ValidationError(ParcelStationError):
    """Raised when submitted parcel data is invalid."""


class ShelfFullError(ParcelStationError):
    """Raised when every shelf slot is occupied."""


class InvalidPickupCodeError(ParcelStationError):
    """Raised when no stored parcel matches a pickup code."""
