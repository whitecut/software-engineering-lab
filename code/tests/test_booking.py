"""Unit tests for pricing, booking, billing, front desk and governance."""

from __future__ import annotations

from datetime import timedelta

import pytest

from hotel_booking.app import App
from hotel_booking.domain import CancelBy, OrderStatus, Role, RoomStatus
from hotel_booking.errors import (
    DomainError,
    InsufficientInventoryError,
    InvalidStateError,
    PermissionDeniedError,
    ValidationError,
)
from hotel_booking.utils import fmt_date, today


@pytest.fixture()
def app(tmp_path):
    """A fresh in-file database seeded with demo data."""
    application = App(tmp_path / "test.db")
    yield application
    application.close()


def day(offset: int) -> str:
    """Return an ISO date relative to today."""
    return fmt_date(today() + timedelta(days=offset))


def login(app: App, phone: str, password: str) -> dict:
    """Convenience login helper."""
    return app.auth.login(phone, password)


def room_type_one(app: App, owner: dict) -> dict:
    """The first (江景大床房) room type of the demo hotel."""
    return app.repo.room_types(owner["hotel_id"])[0]


def create_order(
    app: App,
    guest: dict,
    type_id: int,
    start: int = 1,
    end: int = 3,
    rooms: int = 1,
    key: str | None = None,
) -> dict:
    """Create a standard guest order."""
    return app.booking.create_order(
        guest,
        type_id,
        day(start),
        day(end),
        rooms,
        "张伟",
        "13800000003",
        idempotency_key=key,
    )


def test_pricing_priority(app: App) -> None:
    """Single > range > weekend > base."""
    owner = login(app, "13800000001", "owner123")
    room_type = room_type_one(app, owner)
    friday = today() + timedelta(days=1)
    while friday.weekday() != 4:
        friday += timedelta(days=1)
    assert app.pricing.effective_price(room_type, friday) == 488.0
    assert app.pricing.effective_price(room_type, today() + timedelta(days=5)) == 528.0
    assert app.pricing.effective_price(room_type, today() + timedelta(days=11)) == 458.0
    monday = today() + timedelta(days=1)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    assert app.pricing.effective_price(room_type, monday) == 428.0


def test_search_sorted_by_price(app: App) -> None:
    """Search returns approved hotels sorted by total price."""
    guest = login(app, "13800000003", "guest123")
    results = app.booking.search("上海", day(1), day(3))
    assert results
    prices = [item["total_price"] for item in results]
    assert prices == sorted(prices)
    assert all(item["available"] > 0 for item in results)


def test_booking_inventory_and_idempotency(app: App) -> None:
    """Booking deducts inventory once and duplicate keys return the same order."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    before = app.inventory.available(room_type["id"], today() + timedelta(days=1))
    first = create_order(app, guest, room_type["id"], key="idem-1")
    after = app.inventory.available(room_type["id"], today() + timedelta(days=1))
    assert after == before - 1
    second = create_order(app, guest, room_type["id"], key="idem-1")
    assert second["order_no"] == first["order_no"]
    assert app.inventory.available(room_type["id"], today() + timedelta(days=1)) == after
    app.booking.cancel_order(guest, first["order_no"], CancelBy.GUEST.value)
    assert app.inventory.available(room_type["id"], today() + timedelta(days=1)) == before


def test_booking_rollback_on_partial_deduct(app, monkeypatch) -> None:
    """A failure on a later night rolls back the already deducted night."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    original = app.repo.deduct
    calls = {"count": 0}

    def flaky(room_type_id, date_text, count):
        calls["count"] += 1
        if calls["count"] == 2:
            return False
        return original(room_type_id, date_text, count)

    monkeypatch.setattr(app.repo, "deduct", flaky)
    with pytest.raises(DomainError):
        create_order(app, guest, room_type["id"], start=1, end=3)
    assert app.inventory.available(room_type["id"], today() + timedelta(days=1)) == 12
    assert app.repo.orders_by_customer(guest["id"]) == []


def test_modify_limit_and_price_snapshot(app: App) -> None:
    """Old nights keep their price; the third modification is rejected."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    order = create_order(app, guest, room_type["id"], start=1, end=3)
    old_prices = {night["date"]: night["price"] for night in app.repo.nights(order["id"])}
    modified = app.booking.modify_order(guest, order["order_no"], day(1), day(4), 1)
    assert modified["modify_count"] == 1
    new_prices = {night["date"]: night["price"] for night in app.repo.nights(order["id"])}
    for date_text, price in old_prices.items():
        assert new_prices[date_text] == price
    app.booking.modify_order(guest, order["order_no"], day(1), day(3), 1)
    with pytest.raises(ValidationError):
        app.booking.modify_order(guest, order["order_no"], day(1), day(2), 1)


def test_modify_is_atomic_when_new_dates_sold_out(app: App) -> None:
    """A failed modification leaves the original order and inventory untouched."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    order = create_order(app, guest, room_type["id"], start=1, end=3)
    target_night = today() + timedelta(days=6)
    app.repo.deduct(room_type["id"], fmt_date(target_night), 12)
    with pytest.raises(InsufficientInventoryError):
        app.booking.modify_order(guest, order["order_no"], day(5), day(7), 1)
    current = app.repo.order(order["order_no"])
    assert current["check_in"] == day(1)
    assert current["check_out"] == day(3)
    assert app.inventory.available(room_type["id"], today() + timedelta(days=1)) == 11


def test_cancel_fee_before_and_after_deadline(app: App) -> None:
    """Cancellation before 18:00 the day before is free, otherwise charged."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    late = create_order(app, guest, room_type["id"], start=0, end=1)
    first_night = app.repo.nights(late["id"])[0]["price"]
    cancelled = app.booking.cancel_order(guest, late["order_no"], CancelBy.GUEST.value)
    assert cancelled["cancel_fee"] == first_night
    bill = app.billing.bill(late["id"])
    assert bill["total"] == first_night
    assert bill["room_fee"] == 0
    early = create_order(app, guest, room_type["id"], start=10, end=12)
    free = app.booking.cancel_order(guest, early["order_no"], CancelBy.GUEST.value)
    assert free["cancel_fee"] == 0.0


def test_check_in_room_conflict(app: App) -> None:
    """The same room cannot be assigned to two orders on the same dates."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    desk = login(app, "13800000002", "desk123")
    room_type = room_type_one(app, owner)
    first = create_order(app, guest, room_type["id"], start=1, end=3)
    second = create_order(app, guest, room_type["id"], start=1, end=3)
    app.booking.check_in(desk, first["order_no"], "301")
    with pytest.raises(ValidationError):
        app.booking.check_in(desk, second["order_no"], "301")
    app.booking.check_in(desk, second["order_no"], "302")
    assert app.booking.order_detail(desk, second["order_no"])["status"] == "CHECKED_IN"


def test_bill_and_payments(app: App) -> None:
    """Room fee plus consumption, split payments and unpaid balance."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    desk = login(app, "13800000002", "desk123")
    room_type = room_type_one(app, owner)
    order = create_order(app, guest, room_type["id"], start=1, end=3)
    app.booking.check_in(desk, order["order_no"], "301")
    app.booking.add_consumption(desk, order["order_no"], "洗衣服务", 1)
    room_fee = sum(night["price"] for night in app.repo.nights(order["id"]))
    bill = app.billing.bill(order["id"])
    assert bill["total"] == room_fee + 62.0
    app.billing.add_payment(desk, order["order_no"], "CASH", 500)
    assert app.billing.bill(order["id"])["unpaid"] == room_fee + 62.0 - 500
    with pytest.raises(ValidationError):
        app.billing.add_payment(desk, order["order_no"], "CASH", 1000)
    app.booking.check_out(desk, order["order_no"])
    app.billing.add_payment(desk, order["order_no"], "QR", room_fee + 62.0 - 500)
    assert app.billing.bill(order["id"])["unpaid"] == 0


def test_stop_sale_blocks_booking(app: App) -> None:
    """A room-type stop sale rejects new orders and protects existing ones."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    existing = create_order(app, guest, room_type["id"], start=20, end=21)
    with pytest.raises(ValidationError):
        app.hotel_admin.stop_sale(owner, "ROOM_TYPE", day(20), day(21), "维修", room_type["id"])
    app.booking.cancel_order(guest, existing["order_no"], CancelBy.GUEST.value)
    app.hotel_admin.stop_sale(owner, "ROOM_TYPE", day(21), day(22), "维修", room_type["id"])
    with pytest.raises(ValidationError):
        create_order(app, guest, room_type["id"], start=21, end=22)


def test_room_status_transitions(app: App) -> None:
    """Only allowed room transitions are accepted."""
    desk = login(app, "13800000002", "desk123")
    app.repo.set_room_status(app.repo.room_by_no(1, "301")["id"], RoomStatus.DIRTY.value)
    app.frontdesk.change_room_status(desk, "301", RoomStatus.FREE.value)
    with pytest.raises(InvalidStateError):
        app.frontdesk.change_room_status(desk, "301", RoomStatus.OCCUPIED.value)
    with pytest.raises(ValidationError):
        app.frontdesk.change_room_status(desk, "301", RoomStatus.MAINTENANCE.value)


def test_complaint_flow(app: App) -> None:
    """Guest complains and admin resolves it."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    admin = login(app, "13900000000", "admin123")
    room_type = room_type_one(app, owner)
    order = create_order(app, guest, room_type["id"])
    complaint_id = app.governance.create_complaint(guest, order["order_no"], "卫生", "地面积水")
    app.governance.handle(admin, complaint_id, "RESOLVED", "已整改")
    assert app.repo.complaint(complaint_id)["status"] == "RESOLVED"


def test_privacy_masking_and_view_log(app: App) -> None:
    """Owner sees masked phone unless the full view is explicitly logged."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    order = create_order(app, guest, room_type["id"])
    masked = app.booking.order_detail(owner, order["order_no"])
    assert masked["guest_phone"] == "138****0003"
    full = app.booking.order_detail(owner, order["order_no"], view_full_phone=True)
    assert full["guest_phone"] == "13800000003"
    logs = app.governance.logs(owner)
    assert any(item["action"] == "VIEW_FULL_PHONE" for item in logs)


def test_permissions(app: App) -> None:
    """Role checks prevent cross-role operations."""
    guest = login(app, "13800000003", "guest123")
    desk = login(app, "13800000002", "desk123")
    owner = login(app, "13800000001", "owner123")
    room_type = room_type_one(app, owner)
    with pytest.raises(PermissionDeniedError):
        app.hotel_admin.set_base_price(guest, room_type["id"], 500)
    with pytest.raises(DomainError):
        app.booking.check_in(guest, "HT000", "301")


def test_reports(app: App) -> None:
    """Revenue, occupancy and dashboard read the seeded/created data."""
    owner = login(app, "13800000001", "owner123")
    guest = login(app, "13800000003", "guest123")
    room_type = room_type_one(app, owner)
    order = create_order(app, guest, room_type["id"])
    month = day(1)[:7]
    revenue = app.reports.revenue(owner["hotel_id"], month)
    assert revenue["total"] >= 856.0
    occupancy = app.reports.occupancy(owner["hotel_id"], month)
    assert occupancy and occupancy[0]["sold_nights"] >= 2
    dashboard = app.reports.dashboard(owner["hotel_id"])
    assert dashboard["new_orders"] >= 1
    app.reports.snapshot()
    assert app.repo.snapshots(owner["hotel_id"], month)
    assert app.repo.order(order["order_no"])["status"] == OrderStatus.PENDING.value
