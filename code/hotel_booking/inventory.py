"""Inventory and stop-sale checks."""

from __future__ import annotations

from datetime import date

from .errors import InsufficientInventoryError, ValidationError
from .repository import Repository
from .utils import fmt_date


class InventoryService:
    """Reserve and release daily inventory for a room type."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def ensure(self, room_type: dict, start: date, end: date) -> None:
        """Make sure rows exist for the requested range."""
        self.repo.ensure_inventory(
            room_type["id"], fmt_date(start), fmt_date(end), int(room_type["room_count"])
        )

    def ensure_days(self, room_type: dict, days: list[date]) -> None:
        """Ensure rows for an explicit list of nights."""
        for day in days:
            self.repo.ensure_inventory(
                room_type["id"],
                fmt_date(day),
                fmt_date(day.fromordinal(day.toordinal() + 1)),
                int(room_type["room_count"]),
            )

    def available(self, room_type_id: int, day: date) -> int:
        """Remaining rooms for one night."""
        return self.repo.available(room_type_id, fmt_date(day))

    def check_available(
        self,
        room_type: dict,
        days: list[date],
        rooms: int,
        hotel_id: int | None = None,
        room_id: int | None = None,
    ) -> None:
        """Validate stop sales and availability for every night."""
        if rooms < 1:
            raise ValidationError("间数必须大于 0")
        if not days:
            raise ValidationError("入住日期必须早于离店日期")
        for day in days:
            if hotel_id is not None and self.repo.is_stopped(
                hotel_id, room_type["id"], room_id, fmt_date(day)
            ):
                raise ValidationError(f"{fmt_date(day)} 已停售，无法预订")
            self.repo.ensure_inventory(
                room_type["id"],
                fmt_date(day),
                fmt_date(day.fromordinal(day.toordinal() + 1)),
                int(room_type["room_count"]),
            )
            left = self.available(room_type["id"], day)
            if left < rooms:
                raise InsufficientInventoryError(
                    f"{fmt_date(day)} 仅剩 {left} 间，不满足 {rooms} 间的需求", fmt_date(day)
                )

    def deduct(self, room_type_id: int, days: list[date], rooms: int) -> None:
        """Reserve all nights or raise; the caller owns the transaction."""
        for day in days:
            if not self.repo.deduct(room_type_id, fmt_date(day), rooms):
                raise InsufficientInventoryError(f"{fmt_date(day)} 该房型当天已售完", fmt_date(day))

    def release(self, room_type_id: int, days: list[date], rooms: int) -> None:
        """Release reserved rooms for all nights."""
        for day in days:
            self.repo.release(room_type_id, fmt_date(day), rooms)
