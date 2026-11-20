"""Tests for hotel review, price approval, staff and front-desk edge cases."""

from __future__ import annotations

import pytest

from hotel_booking.app import App
from hotel_booking.domain import Role
from hotel_booking.errors import DomainError, PermissionDeniedError, ValidationError


@pytest.fixture()
def app(tmp_path):
    application = App(tmp_path / "admin.db")
    yield application
    application.close()


def login(app: App, phone: str, password: str) -> dict:
    return app.auth.login(phone, password)


def test_review_pending_hotel(app: App) -> None:
    admin = login(app, "13900000000", "admin123")
    pending = app.hotel_admin.pending_hotels()
    assert pending
    hotel_id = pending[0]["id"]
    app.hotel_admin.review(admin, hotel_id, True, "资料齐全")
    assert app.repo.hotel(hotel_id)["status"] == "APPROVED"


def test_review_reject_requires_reason(app: App) -> None:
    admin = login(app, "13900000000", "admin123")
    hotel_id = app.hotel_admin.pending_hotels()[0]["id"]
    with pytest.raises(ValidationError):
        app.hotel_admin.review(admin, hotel_id, False, "")


def test_price_change_over_five_times_needs_approval(app: App) -> None:
    owner = login(app, "13800000001", "owner123")
    admin = login(app, "13900000000", "admin123")
    room_type = app.repo.room_types(owner["hotel_id"])[0]
    message = app.hotel_admin.set_base_price(owner, room_type["id"], 3000)
    assert "审批" in message
    approvals = app.hotel_admin.pending_approvals()
    assert len(approvals) == 1
    app.hotel_admin.approve_price(admin, approvals[0]["id"], True)
    assert app.repo.room_type(room_type["id"])["base_price"] == 3000


def test_expired_price_approval_is_rejected(app: App) -> None:
    owner = login(app, "13800000001", "owner123")
    admin = login(app, "13900000000", "admin123")
    room_type = app.repo.room_types(owner["hotel_id"])[0]
    app.hotel_admin.set_base_price(owner, room_type["id"], 4000)
    approval = app.hotel_admin.pending_approvals()[0]
    app.repo.conn.execute(
        "UPDATE price_approvals SET expires_at = '2000-01-01 00:00:00' WHERE id = ?",
        (approval["id"],),
    )
    app.repo.conn.commit()
    with pytest.raises(ValidationError):
        app.hotel_admin.approve_price(admin, approval["id"], True)


def test_frontdesk_can_book_for_guest(app: App) -> None:
    desk = login(app, "13800000002", "desk123")
    owner = login(app, "13800000001", "owner123")
    room_type = app.repo.room_types(owner["hotel_id"])[0]
    order = app.booking.create_order(
        desk, room_type["id"], "2026-12-20", "2026-12-22", 1,
        "李静", "13912345678", source="DESK",
    )
    assert order["source"] == "DESK"
    assert order["customer_id"] is None


def test_mark_no_show(app: App) -> None:
    desk = login(app, "13800000002", "desk123")
    guest = login(app, "13800000003", "guest123")
    owner = login(app, "13800000001", "owner123")
    room_type = app.repo.room_types(owner["hotel_id"])[0]
    order = app.booking.create_order(
        guest, room_type["id"], "2026-12-20", "2026-12-21", 1, "张伟", "13800000003"
    )
    app.booking.mark_no_show(desk, order["order_no"])
    assert app.repo.order(order["order_no"])["status"] == "NO_SHOW"


def test_refund_consumption(app: App) -> None:
    desk = login(app, "13800000002", "desk123")
    guest = login(app, "13800000003", "guest123")
    owner = login(app, "13800000001", "owner123")
    room_type = app.repo.room_types(owner["hotel_id"])[0]
    order = app.booking.create_order(
        guest, room_type["id"], "2026-12-20", "2026-12-21", 1, "张伟", "13800000003"
    )
    app.booking.check_in(desk, order["order_no"], "301")
    consumption_id = app.booking.add_consumption(desk, order["order_no"], "洗衣服务", 2)
    assert app.billing.bill(order["id"])["other_fee"] == 124.0
    app.frontdesk.refund_consumption(desk, consumption_id, "客人取消")
    assert app.billing.bill(order["id"])["other_fee"] == 0.0


def test_void_bill_blocks_payment(app: App) -> None:
    owner = login(app, "13800000001", "owner123")
    desk = login(app, "13800000002", "desk123")
    guest = login(app, "13800000003", "guest123")
    room_type = app.repo.room_types(owner["hotel_id"])[0]
    order = app.booking.create_order(
        guest, room_type["id"], "2026-12-20", "2026-12-21", 1, "张伟", "13800000003"
    )
    app.billing.void(owner, order["order_no"], "测试作废")
    assert app.repo.bill_by_order(order["id"])["voided"] == 1
    with pytest.raises(ValidationError):
        app.billing.add_payment(desk, order["order_no"], "CASH", 100)


def test_staff_accounts(app: App) -> None:
    owner = login(app, "13800000001", "owner123")
    account_id = app.hotel_admin.add_staff(owner, "13600000001", "赵敏", "staff123")
    assert app.repo.account_by_id(account_id)["role"] == Role.FRONT_DESK.value
    app.hotel_admin.disable_staff(owner, account_id)
    with pytest.raises(PermissionDeniedError):
        app.auth.login("13600000001", "staff123")


def test_guest_cannot_change_price(app: App) -> None:
    guest = login(app, "13800000003", "guest123")
    owner = login(app, "13800000001", "owner123")
    room_type = app.repo.room_types(owner["hotel_id"])[0]
    with pytest.raises(DomainError):
        app.hotel_admin.set_base_price(guest, room_type["id"], 500)
