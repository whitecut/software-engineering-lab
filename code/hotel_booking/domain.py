"""Domain enums and state transition rules.

The values mirror the UML design from lab 2 so that the database and the
CLI can use readable strings instead of magic numbers.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String enum with a readable value."""

    def __str__(self) -> str:
        return str(self.value)


class Role(StrEnum):
    """User roles."""

    GUEST = "GUEST"
    FRONT_DESK = "FRONT_DESK"
    OWNER = "OWNER"
    ADMIN = "ADMIN"


class AccountStatus(StrEnum):
    """Account lifecycle."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class HotelStatus(StrEnum):
    """Hotel review lifecycle."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OFFLINE = "OFFLINE"
    BANNED = "BANNED"


class RoomStatus(StrEnum):
    """Room state used by the front desk."""

    FREE = "FREE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    DIRTY = "DIRTY"
    MAINTENANCE = "MAINTENANCE"


class OrderStatus(StrEnum):
    """Order states."""

    PENDING = "PENDING"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class CancelBy(StrEnum):
    """Who cancelled an order."""

    GUEST = "GUEST"
    HOTEL = "HOTEL"
    PLATFORM = "PLATFORM"


class PriceRuleType(StrEnum):
    """Price rule kinds, highest priority first."""

    SINGLE = "SINGLE"
    RANGE = "RANGE"
    WEEKEND = "WEEKEND"


class StopScope(StrEnum):
    """Stop-sale scope."""

    HOTEL = "HOTEL"
    ROOM_TYPE = "ROOM_TYPE"
    ROOM = "ROOM"


class ConsumptionType(StrEnum):
    """Consumption categories."""

    WITH_ORDER = "WITH_ORDER"
    IN_HOUSE = "IN_HOUSE"


class PaymentMethod(StrEnum):
    """Payment methods supported by the front desk."""

    CASH = "CASH"
    QR = "QR"


class ComplaintStatus(StrEnum):
    """Complaint lifecycle."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


# Allowed order transitions. Terminal states have no outgoing edges.
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {
        OrderStatus.CHECKED_IN,
        OrderStatus.CANCELLED,
        OrderStatus.NO_SHOW,
    },
    OrderStatus.CHECKED_IN: {OrderStatus.CHECKED_OUT, OrderStatus.PENDING},
    OrderStatus.CHECKED_OUT: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.NO_SHOW: set(),
}

# Allowed room transitions. Maintenance rooms cannot be assigned.
ROOM_TRANSITIONS: dict[RoomStatus, set[RoomStatus]] = {
    RoomStatus.FREE: {RoomStatus.RESERVED, RoomStatus.MAINTENANCE},
    RoomStatus.RESERVED: {RoomStatus.OCCUPIED, RoomStatus.FREE},
    RoomStatus.OCCUPIED: {RoomStatus.DIRTY},
    RoomStatus.DIRTY: {RoomStatus.FREE},
    RoomStatus.MAINTENANCE: {RoomStatus.FREE},
}

TERMINAL_ORDER_STATUS = {
    OrderStatus.CHECKED_OUT,
    OrderStatus.CANCELLED,
    OrderStatus.NO_SHOW,
}

CANCELLED_STATUS = OrderStatus.CANCELLED
