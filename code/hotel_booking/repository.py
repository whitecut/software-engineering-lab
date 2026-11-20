"""Data access layer built on SQLite.

Every method receives plain values and returns dictionaries (or lists of
dictionaries) so the service layer never depends on sqlite3.Row.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from .domain import RoomStatus
from .utils import date_range, fmt_date, now_text, parse_date


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


class Repository:
    """Thin repository for all aggregates."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """init   operation."""
        self.conn = conn

    # ------------------------------------------------------------------
    # accounts
    # ------------------------------------------------------------------
    def create_account(
        self,
        phone: str,
        password_hash: str,
        role: str,
        name: str,
        hotel_id: int | None = None,
        is_primary: int = 0,
    ) -> int:
        """Create account."""
        cur = self.conn.execute(
            "INSERT INTO accounts(phone, password_hash, role, name, hotel_id, is_primary,"
            " status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
            (phone, password_hash, role, name, hotel_id, is_primary, now_text()),
        )
        return int(cur.lastrowid)

    def account_by_phone(self, phone: str) -> dict[str, Any] | None:
        """By phone operation."""
        return _dict(
            self.conn.execute("SELECT * FROM accounts WHERE phone = ?", (phone,)).fetchone()
        )

    def account_by_id(self, account_id: int) -> dict[str, Any] | None:
        """By id operation."""
        return _dict(
            self.conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        )

    def accounts_by_hotel(self, hotel_id: int) -> list[dict[str, Any]]:
        """By hotel operation."""
        rows = self.conn.execute(
            "SELECT * FROM accounts WHERE hotel_id = ? ORDER BY is_primary DESC, id", (hotel_id,)
        ).fetchall()
        return _list(rows)

    def set_account_status(self, account_id: int, status: str) -> None:
        """Update account status."""
        self.conn.execute("UPDATE accounts SET status = ? WHERE id = ?", (status, account_id))

    # ------------------------------------------------------------------
    # hotels
    # ------------------------------------------------------------------
    def create_hotel(
        self,
        name: str,
        city: str,
        district: str,
        address: str,
        phone: str,
        owner_name: str,
        status: str,
    ) -> int:
        """Create hotel."""
        cur = self.conn.execute(
            "INSERT INTO hotels(name, city, district, address, phone, owner_name, status,"
            " created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, city, district, address, phone, owner_name, status, now_text()),
        )
        return int(cur.lastrowid)

    def hotel(self, hotel_id: int) -> dict[str, Any] | None:
        """hotel operation."""
        return _dict(self.conn.execute("SELECT * FROM hotels WHERE id = ?", (hotel_id,)).fetchone())

    def hotels(self, status: str | None = None, city: str | None = None) -> list[dict[str, Any]]:
        """hotels operation."""
        sql = "SELECT * FROM hotels WHERE 1 = 1"
        params: list[Any] = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if city:
            sql += " AND city = ?"
            params.append(city)
        sql += " ORDER BY id"
        return _list(self.conn.execute(sql, params).fetchall())

    def set_hotel_status(self, hotel_id: int, status: str) -> None:
        """Update hotel status."""
        self.conn.execute("UPDATE hotels SET status = ? WHERE id = ?", (status, hotel_id))

    def cities(self) -> list[str]:
        """cities operation."""
        rows = self.conn.execute("SELECT DISTINCT city FROM hotels ORDER BY city").fetchall()
        return [row["city"] for row in rows]

    # ------------------------------------------------------------------
    # room types and rooms
    # ------------------------------------------------------------------
    def create_room_type(
        self,
        hotel_id: int,
        name: str,
        breakfast: int,
        room_count: int,
        base_price: float,
        cancel_rule: str,
    ) -> int:
        """Create room type."""
        cur = self.conn.execute(
            "INSERT INTO room_types(hotel_id, name, breakfast, room_count, base_price,"
            " cancel_rule, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (hotel_id, name, breakfast, room_count, base_price, cancel_rule, now_text()),
        )
        return int(cur.lastrowid)

    def room_type(self, room_type_id: int) -> dict[str, Any] | None:
        """Type operation."""
        return _dict(
            self.conn.execute("SELECT * FROM room_types WHERE id = ?", (room_type_id,)).fetchone()
        )

    def room_types(self, hotel_id: int) -> list[dict[str, Any]]:
        """Types operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM room_types WHERE hotel_id = ? ORDER BY id", (hotel_id,)
            ).fetchall()
        )

    def update_room_type(self, room_type_id: int, **fields: Any) -> None:
        """Update room type."""
        allowed = {"name", "breakfast", "room_count", "base_price", "cancel_rule"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        self.conn.execute(
            f"UPDATE room_types SET {assignments} WHERE id = ?",
            (*updates.values(), room_type_id),
        )

    def create_room(
        self, hotel_id: int, room_type_id: int, room_no: str, status: str = RoomStatus.FREE.value
    ) -> int:
        """Create room."""
        cur = self.conn.execute(
            "INSERT INTO rooms(hotel_id, room_type_id, room_no, status) VALUES (?, ?, ?, ?)",
            (hotel_id, room_type_id, room_no, status),
        )
        return int(cur.lastrowid)

    def room(self, room_id: int) -> dict[str, Any] | None:
        """room operation."""
        return _dict(self.conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone())

    def room_by_no(self, hotel_id: int, room_no: str) -> dict[str, Any] | None:
        """By no operation."""
        return _dict(
            self.conn.execute(
                "SELECT * FROM rooms WHERE hotel_id = ? AND room_no = ?", (hotel_id, room_no)
            ).fetchone()
        )

    def rooms(
        self, hotel_id: int, room_type_id: int | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        """rooms operation."""
        sql = "SELECT * FROM rooms WHERE hotel_id = ?"
        params: list[Any] = [hotel_id]
        if room_type_id:
            sql += " AND room_type_id = ?"
            params.append(room_type_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY room_no"
        return _list(self.conn.execute(sql, params).fetchall())

    def set_room_status(self, room_id: int, status: str) -> None:
        """Update room status."""
        self.conn.execute("UPDATE rooms SET status = ? WHERE id = ?", (status, room_id))

    # ------------------------------------------------------------------
    # inventory
    # ------------------------------------------------------------------
    def ensure_inventory(self, room_type_id: int, start: str, end: str, total: int) -> None:
        """Create missing inventory rows for [start, end)."""
        for day in date_range(parse_date(start), parse_date(end)):
            self.conn.execute(
                "INSERT OR IGNORE INTO inventory(room_type_id, date, total, sold, version)"
                " VALUES (?, ?, ?, 0, 0)",
                (room_type_id, fmt_date(day), total),
            )

    def inventory_row(self, room_type_id: int, day: str) -> dict[str, Any] | None:
        """Row operation."""
        return _dict(
            self.conn.execute(
                "SELECT * FROM inventory WHERE room_type_id = ? AND date = ?",
                (room_type_id, day),
            ).fetchone()
        )

    def available(self, room_type_id: int, day: str) -> int:
        """available operation."""
        row = self.inventory_row(room_type_id, day)
        return (row["total"] - row["sold"]) if row else 0

    def deduct(self, room_type_id: int, day: str, count: int) -> bool:
        """Atomically reserve inventory. Returns False when sold out."""
        cur = self.conn.execute(
            "UPDATE inventory SET sold = sold + ?, version = version + 1"
            " WHERE room_type_id = ? AND date = ? AND total - sold >= ?",
            (count, room_type_id, day, count),
        )
        return cur.rowcount == 1

    def release(self, room_type_id: int, day: str, count: int) -> None:
        """Update release."""
        self.conn.execute(
            "UPDATE inventory SET sold = MAX(0, sold - ?), version = version + 1"
            " WHERE room_type_id = ? AND date = ?",
            (count, room_type_id, day),
        )

    def set_inventory_total(self, room_type_id: int, start: str, total: int) -> None:
        """Change the sellable total from a date onwards."""
        self.conn.execute(
            "UPDATE inventory SET total = ? WHERE room_type_id = ? AND date >= ?",
            (total, room_type_id, start),
        )

    # ------------------------------------------------------------------
    # price rules and stop sales
    # ------------------------------------------------------------------
    def add_price_rule(
        self, room_type_id: int, rule_type: str, start: str, end: str, price: float
    ) -> int:
        """Create price rule."""
        cur = self.conn.execute(
            "INSERT INTO price_rules(room_type_id, rule_type, start_date, end_date,"
            " price, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (room_type_id, rule_type, start, end, price, now_text()),
        )
        return int(cur.lastrowid)

    def price_rules(self, room_type_id: int) -> list[dict[str, Any]]:
        """Rules operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM price_rules WHERE room_type_id = ? ORDER BY id", (room_type_id,)
            ).fetchall()
        )

    def add_price_approval(
        self, room_type_id: int, old_price: float, new_price: float, expires_at: str
    ) -> int:
        """Create price approval."""
        cur = self.conn.execute(
            "INSERT INTO price_approvals(room_type_id, old_price, new_price, status,"
            " created_at, expires_at) VALUES (?, ?, ?, 'PENDING', ?, ?)",
            (room_type_id, old_price, new_price, now_text(), expires_at),
        )
        return int(cur.lastrowid)

    def price_approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        """Approvals operation."""
        sql = "SELECT * FROM price_approvals WHERE 1 = 1"
        params: list[Any] = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY id DESC"
        return _list(self.conn.execute(sql, params).fetchall())

    def price_approval(self, approval_id: int) -> dict[str, Any] | None:
        """Approval operation."""
        return _dict(
            self.conn.execute(
                "SELECT * FROM price_approvals WHERE id = ?", (approval_id,)
            ).fetchone()
        )

    def update_price_approval(self, approval_id: int, status: str) -> None:
        """Update price approval."""
        self.conn.execute(
            "UPDATE price_approvals SET status = ? WHERE id = ?", (status, approval_id)
        )

    def add_stop_sale(
        self,
        hotel_id: int,
        scope: str,
        start: str,
        end: str,
        reason: str,
        room_type_id: int | None = None,
        room_id: int | None = None,
    ) -> int:
        """Create stop sale."""
        cur = self.conn.execute(
            "INSERT INTO stop_sales(hotel_id, room_type_id, room_id, scope, start_date, end_date,"
            " reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (hotel_id, room_type_id, room_id, scope, start, end, reason, now_text()),
        )
        return int(cur.lastrowid)

    def stop_sales(self, hotel_id: int) -> list[dict[str, Any]]:
        """Sales operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM stop_sales WHERE hotel_id = ? ORDER BY id DESC", (hotel_id,)
            ).fetchall()
        )

    def is_stopped(self, hotel_id: int, room_type_id: int, room_id: int | None, day: str) -> bool:
        """Check stopped."""
        row = self.conn.execute(
            "SELECT 1 FROM stop_sales WHERE hotel_id = ? AND start_date <= ? AND end_date >= ?"
            " AND (scope = 'HOTEL' OR (scope = 'ROOM_TYPE' AND room_type_id = ?)"
            "      OR (scope = 'ROOM' AND room_id = ?)) LIMIT 1",
            (hotel_id, day, day, room_type_id, room_id),
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------
    # products
    # ------------------------------------------------------------------
    def create_product(self, hotel_id: int, name: str, price: float, stock: int) -> int:
        """Create product."""
        cur = self.conn.execute(
            "INSERT INTO products(hotel_id, name, price, stock, status)"
            " VALUES (?, ?, ?, ?, 'ON_SALE')",
            (hotel_id, name, price, stock),
        )
        return int(cur.lastrowid)

    def product(self, product_id: int) -> dict[str, Any] | None:
        """product operation."""
        return _dict(
            self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        )

    def product_by_name(self, hotel_id: int, name: str) -> dict[str, Any] | None:
        """By name operation."""
        return _dict(
            self.conn.execute(
                "SELECT * FROM products WHERE hotel_id = ? AND name = ?", (hotel_id, name)
            ).fetchone()
        )

    def products(self, hotel_id: int) -> list[dict[str, Any]]:
        """products operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM products WHERE hotel_id = ? ORDER BY id", (hotel_id,)
            ).fetchall()
        )

    def change_stock(self, product_id: int, delta: int) -> None:
        """Update stock."""
        self.conn.execute(
            "UPDATE products SET stock = MAX(0, stock + ?) WHERE id = ?", (delta, product_id)
        )

    # ------------------------------------------------------------------
    # orders
    # ------------------------------------------------------------------
    def create_order(self, **fields: Any) -> int:
        """Create order."""
        columns = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        cur = self.conn.execute(
            f"INSERT INTO orders({columns}) VALUES ({placeholders})", tuple(fields.values())
        )
        return int(cur.lastrowid)

    def order(self, order_no: str) -> dict[str, Any] | None:
        """order operation."""
        return _dict(
            self.conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
        )

    def order_by_id(self, order_id: int) -> dict[str, Any] | None:
        """By id operation."""
        return _dict(self.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone())

    def orders_by_customer(self, customer_id: int) -> list[dict[str, Any]]:
        """By customer operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC", (customer_id,)
            ).fetchall()
        )

    def orders_by_hotel(self, hotel_id: int, status: str | None = None) -> list[dict[str, Any]]:
        """By hotel operation."""
        sql = "SELECT * FROM orders WHERE hotel_id = ?"
        params: list[Any] = [hotel_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY id DESC"
        return _list(self.conn.execute(sql, params).fetchall())

    def find_orders(self, hotel_id: int, keyword: str) -> list[dict[str, Any]]:
        """Return orders."""
        like = f"%{keyword}%"
        return _list(
            self.conn.execute(
                "SELECT * FROM orders WHERE hotel_id = ? AND"
                " (order_no LIKE ? OR guest_phone LIKE ? OR guest_name LIKE ?)"
                " ORDER BY id DESC",
                (hotel_id, like, like, like),
            ).fetchall()
        )

    def orders_overlapping(
        self, room_type_id: int, start: str, end: str, room_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Orders that overlap a stop-sale range and are still active."""
        sql = (
            "SELECT DISTINCT o.* FROM orders o"
            " LEFT JOIN order_rooms r ON r.order_id = o.id"
            " WHERE o.room_type_id = ? AND o.status IN ('PENDING', 'CHECKED_IN')"
            " AND o.check_in <= ? AND o.check_out > ?"
        )
        params: list[Any] = [room_type_id, end, start]
        if room_id is not None:
            sql += " AND r.room_id = ?"
            params.append(room_id)
        return _list(self.conn.execute(sql, params).fetchall())

    def update_order(self, order_id: int, **fields: Any) -> None:
        """Update order."""
        if not fields:
            return
        assignments = ", ".join(f"{key} = ?" for key in fields)
        self.conn.execute(
            f"UPDATE orders SET {assignments} WHERE id = ?", (*fields.values(), order_id)
        )

    def add_night(self, order_id: int, day: str, price: float) -> None:
        """Create night."""
        self.conn.execute(
            "INSERT INTO order_nights(order_id, date, price) VALUES (?, ?, ?)",
            (order_id, day, price),
        )

    def nights(self, order_id: int) -> list[dict[str, Any]]:
        """nights operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM order_nights WHERE order_id = ? ORDER BY date", (order_id,)
            ).fetchall()
        )

    def clear_nights(self, order_id: int) -> None:
        """Nights operation."""
        self.conn.execute("DELETE FROM order_nights WHERE order_id = ?", (order_id,))

    def add_order_room(self, order_id: int, room_id: int, room_no: str) -> None:
        """Create order room."""
        self.conn.execute(
            "INSERT INTO order_rooms(order_id, room_id, room_no) VALUES (?, ?, ?)",
            (order_id, room_id, room_no),
        )

    def order_rooms(self, order_id: int) -> list[dict[str, Any]]:
        """Rooms operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM order_rooms WHERE order_id = ? ORDER BY room_no", (order_id,)
            ).fetchall()
        )

    def room_conflicts(
        self, room_id: int, check_in: str, check_out: str, exclude_order_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Active orders occupying a room in an overlapping date range."""
        sql = (
            "SELECT DISTINCT o.* FROM order_rooms r JOIN orders o ON o.id = r.order_id"
            " WHERE r.room_id = ? AND o.status IN ('PENDING', 'CHECKED_IN')"
            " AND o.check_in < ? AND o.check_out > ?"
        )
        params: list[Any] = [room_id, check_out, check_in]
        if exclude_order_id:
            sql += " AND o.id <> ?"
            params.append(exclude_order_id)
        return _list(self.conn.execute(sql, params).fetchall())

    # ------------------------------------------------------------------
    # consumptions and bills
    # ------------------------------------------------------------------
    def add_consumption(
        self,
        order_id: int,
        name: str,
        ctype: str,
        qty: int,
        unit_price: float,
        amount: float,
        confirmed_by: str,
        product_id: int | None = None,
    ) -> int:
        """Create consumption."""
        cur = self.conn.execute(
            "INSERT INTO consumptions(order_id, product_id, name, ctype, qty, unit_price,"
            " amount, status, confirmed_by, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)",
            (order_id, product_id, name, ctype, qty, unit_price, amount, confirmed_by, now_text()),
        )
        return int(cur.lastrowid)

    def consumptions(self, order_id: int) -> list[dict[str, Any]]:
        """consumptions operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM consumptions WHERE order_id = ? ORDER BY id", (order_id,)
            ).fetchall()
        )

    def refund_consumption(self, consumption_id: int) -> None:
        """Consumption operation."""
        self.conn.execute(
            "UPDATE consumptions SET status = 'REFUNDED' WHERE id = ?", (consumption_id,)
        )

    def create_bill(
        self,
        order_id: int,
        room_fee: float = 0,
        breakfast_fee: float = 0,
        other_fee: float = 0,
        total: float = 0,
    ) -> int:
        """Create bill."""
        cur = self.conn.execute(
            "INSERT INTO bills(order_id, room_fee, breakfast_fee, other_fee, cancel_fee,"
            " total, paid, voided, created_at) VALUES (?, ?, ?, ?, 0, ?, 0, 0, ?)",
            (order_id, room_fee, breakfast_fee, other_fee, total, now_text()),
        )
        return int(cur.lastrowid)

    def bill_by_order(self, order_id: int) -> dict[str, Any] | None:
        """By order operation."""
        return _dict(
            self.conn.execute("SELECT * FROM bills WHERE order_id = ?", (order_id,)).fetchone()
        )

    def update_bill(self, order_id: int, **fields: Any) -> None:
        """Update bill."""
        if not fields:
            return
        assignments = ", ".join(f"{key} = ?" for key in fields)
        self.conn.execute(
            f"UPDATE bills SET {assignments} WHERE order_id = ?", (*fields.values(), order_id)
        )

    def void_bill(self, order_id: int) -> None:
        """Bill operation."""
        self.conn.execute("UPDATE bills SET voided = 1 WHERE order_id = ?", (order_id,))

    def add_payment(self, bill_id: int, method: str, amount: float, account_id: int) -> int:
        """Create payment."""
        cur = self.conn.execute(
            "INSERT INTO payments(bill_id, method, amount, paid_at, account_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (bill_id, method, amount, now_text(), account_id),
        )
        self.conn.execute("UPDATE bills SET paid = paid + ? WHERE id = ?", (amount, bill_id))
        return int(cur.lastrowid)

    def payments(self, bill_id: int) -> list[dict[str, Any]]:
        """payments operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM payments WHERE bill_id = ? ORDER BY id", (bill_id,)
            ).fetchall()
        )

    # ------------------------------------------------------------------
    # complaints, logs, snapshots, idempotency
    # ------------------------------------------------------------------
    def create_complaint(
        self, order_id: int, hotel_id: int, customer_id: int, ctype: str, content: str
    ) -> int:
        """Create complaint."""
        cur = self.conn.execute(
            "INSERT INTO complaints(order_id, hotel_id, customer_id, ctype, content,"
            " status, created_at) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
            (order_id, hotel_id, customer_id, ctype, content, now_text()),
        )
        return int(cur.lastrowid)

    def complaint(self, complaint_id: int) -> dict[str, Any] | None:
        """complaint operation."""
        return _dict(
            self.conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        )

    def complaints(
        self, status: str | None = None, hotel_id: int | None = None
    ) -> list[dict[str, Any]]:
        """complaints operation."""
        sql = "SELECT * FROM complaints WHERE 1 = 1"
        params: list[Any] = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if hotel_id:
            sql += " AND hotel_id = ?"
            params.append(hotel_id)
        sql += " ORDER BY id DESC"
        return _list(self.conn.execute(sql, params).fetchall())

    def update_complaint(self, complaint_id: int, **fields: Any) -> None:
        """Update complaint."""
        if not fields:
            return
        assignments = ", ".join(f"{key} = ?" for key in fields)
        self.conn.execute(
            f"UPDATE complaints SET {assignments} WHERE id = ?", (*fields.values(), complaint_id)
        )

    def add_log(
        self,
        account_id: int | None,
        role: str,
        action: str,
        target: str,
        before_value: str = "",
        after_value: str = "",
        result: str = "OK",
        hotel_id: int | None = None,
    ) -> None:
        """Create log."""
        self.conn.execute(
            "INSERT INTO operation_logs(account_id, role, action, target, before_value,"
            " after_value, result, hotel_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_id,
                role,
                action,
                target,
                before_value,
                after_value,
                result,
                hotel_id,
                now_text(),
            ),
        )

    def logs(
        self,
        hotel_id: int | None = None,
        account_id: int | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """logs operation."""
        sql = "SELECT * FROM operation_logs WHERE 1 = 1"
        params: list[Any] = []
        if hotel_id:
            sql += " AND hotel_id = ?"
            params.append(hotel_id)
        if account_id:
            sql += " AND account_id = ?"
            params.append(account_id)
        if action:
            sql += " AND action = ?"
            params.append(action)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return _list(self.conn.execute(sql, params).fetchall())

    def upsert_snapshot(
        self, day: str, hotel_id: int, room_type_id: int, available_nights: int, sold_nights: int
    ) -> None:
        """Snapshot operation."""
        self.conn.execute(
            "INSERT INTO snapshots(date, hotel_id, room_type_id, available_nights, sold_nights)"
            " VALUES (?, ?, ?, ?, ?) ON CONFLICT(date, hotel_id, room_type_id)"
            " DO UPDATE SET available_nights = excluded.available_nights,"
            " sold_nights = excluded.sold_nights",
            (day, hotel_id, room_type_id, available_nights, sold_nights),
        )

    def snapshots(self, hotel_id: int, month_prefix: str) -> list[dict[str, Any]]:
        """snapshots operation."""
        return _list(
            self.conn.execute(
                "SELECT * FROM snapshots WHERE hotel_id = ? AND date LIKE ?"
                " ORDER BY date, room_type_id",
                (hotel_id, f"{month_prefix}%"),
            ).fetchall()
        )

    def idempotent_order_no(self, key: str) -> str | None:
        """Order no operation."""
        row = self.conn.execute("SELECT order_no FROM idempotency WHERE key = ?", (key,)).fetchone()
        return row["order_no"] if row else None

    def save_idempotency(self, key: str, order_no: str) -> None:
        """Idempotency operation."""
        self.conn.execute(
            "INSERT OR REPLACE INTO idempotency(key, order_no, created_at) VALUES (?, ?, ?)",
            (key, order_no, now_text()),
        )
