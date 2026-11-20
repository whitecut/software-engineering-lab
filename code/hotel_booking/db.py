"""SQLite schema and demo data for the hotel booking system."""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

from .security import hash_password
from .utils import date_range, fmt_date, now_text, today

DB_PATH = Path(__file__).resolve().parent.parent / "hotel.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS hotels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    district TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    owner_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    name TEXT NOT NULL,
    hotel_id INTEGER,
    is_primary INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (hotel_id) REFERENCES hotels(id)
);

CREATE TABLE IF NOT EXISTS room_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    breakfast INTEGER NOT NULL DEFAULT 0,
    room_count INTEGER NOT NULL,
    base_price REAL NOT NULL,
    cancel_rule TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (hotel_id) REFERENCES hotels(id)
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL,
    room_type_id INTEGER NOT NULL,
    room_no TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'FREE',
    UNIQUE (hotel_id, room_no),
    FOREIGN KEY (hotel_id) REFERENCES hotels(id),
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);

CREATE TABLE IF NOT EXISTS inventory (
    room_type_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    total INTEGER NOT NULL,
    sold INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (room_type_id, date),
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);

CREATE TABLE IF NOT EXISTS price_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_type_id INTEGER NOT NULL,
    rule_type TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    price REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);

CREATE TABLE IF NOT EXISTS price_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_type_id INTEGER NOT NULL,
    old_price REAL NOT NULL,
    new_price REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);

CREATE TABLE IF NOT EXISTS stop_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL,
    room_type_id INTEGER,
    room_id INTEGER,
    scope TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (hotel_id) REFERENCES hotels(id)
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ON_SALE',
    UNIQUE (hotel_id, name),
    FOREIGN KEY (hotel_id) REFERENCES hotels(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER,
    hotel_id INTEGER NOT NULL,
    room_type_id INTEGER NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    rooms INTEGER NOT NULL DEFAULT 1,
    guest_name TEXT NOT NULL,
    guest_phone TEXT NOT NULL,
    eta TEXT NOT NULL DEFAULT '20:00',
    status TEXT NOT NULL DEFAULT 'PENDING',
    cancel_by TEXT,
    cancel_fee REAL NOT NULL DEFAULT 0,
    modify_count INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'SELF',
    idempotency_key TEXT,
    created_at TEXT NOT NULL DEFAULT '',
    checked_in_at TEXT,
    checked_out_at TEXT,
    FOREIGN KEY (customer_id) REFERENCES accounts(id),
    FOREIGN KEY (hotel_id) REFERENCES hotels(id),
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);

CREATE TABLE IF NOT EXISTS order_nights (
    order_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    price REAL NOT NULL,
    PRIMARY KEY (order_id, date),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    room_no TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS consumptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER,
    name TEXT NOT NULL,
    ctype TEXT NOT NULL,
    qty INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    confirmed_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE,
    room_fee REAL NOT NULL DEFAULT 0,
    breakfast_fee REAL NOT NULL DEFAULT 0,
    other_fee REAL NOT NULL DEFAULT 0,
    cancel_fee REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    paid REAL NOT NULL DEFAULT 0,
    voided INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL DEFAULT '',
    account_id INTEGER,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    hotel_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    ctype TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    result TEXT NOT NULL DEFAULT '',
    handler TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    handled_at TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    role TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '',
    before_value TEXT NOT NULL DEFAULT '',
    after_value TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT 'OK',
    hotel_id INTEGER,
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS snapshots (
    date TEXT NOT NULL,
    hotel_id INTEGER NOT NULL,
    room_type_id INTEGER NOT NULL,
    available_nights INTEGER NOT NULL,
    sold_nights INTEGER NOT NULL,
    PRIMARY KEY (date, hotel_id, room_type_id)
);

CREATE TABLE IF NOT EXISTS idempotency (
    key TEXT PRIMARY KEY,
    order_no TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_hotel ON orders(hotel_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_inventory_date ON inventory(date);
CREATE INDEX IF NOT EXISTS idx_logs_created ON operation_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
"""


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with dict-like rows and foreign keys."""
    path = str(db_path) if db_path else str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they do not exist."""
    conn.executescript(SCHEMA)
    conn.commit()


def _insert_hotel(
    conn: sqlite3.Connection,
    name: str,
    city: str,
    district: str,
    address: str,
    phone: str,
    owner: str,
    status: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO hotels(name, city, district, address, phone, owner_name, status,"
        " created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (name, city, district, address, phone, owner, status, now_text()),
    )
    return int(cur.lastrowid)


def _insert_account(
    conn: sqlite3.Connection,
    phone: str,
    password: str,
    role: str,
    name: str,
    hotel_id: int | None,
    primary: int = 0,
) -> int:
    cur = conn.execute(
        "INSERT INTO accounts(phone, password_hash, role, name, hotel_id, is_primary,"
        " status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
        (phone, hash_password(password), role, name, hotel_id, primary, now_text()),
    )
    return int(cur.lastrowid)


def _insert_room_type(
    conn: sqlite3.Connection,
    hotel_id: int,
    name: str,
    breakfast: int,
    count: int,
    base_price: float,
    cancel_rule: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO room_types(hotel_id, name, breakfast, room_count, base_price,"
        " cancel_rule, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (hotel_id, name, breakfast, count, base_price, cancel_rule, now_text()),
    )
    return int(cur.lastrowid)


def _insert_rooms(
    conn: sqlite3.Connection, hotel_id: int, room_type_id: int, room_numbers: list[str]
) -> None:
    for room_no in room_numbers:
        conn.execute(
            "INSERT OR IGNORE INTO rooms(hotel_id, room_type_id, room_no, status)"
            " VALUES (?, ?, ?, 'FREE')",
            (hotel_id, room_type_id, room_no),
        )


def _ensure_inventory(
    conn: sqlite3.Connection, room_type_id: int, total: int, start_offset: int = -1, days: int = 180
) -> None:
    start = today() + timedelta(days=start_offset)
    end = start + timedelta(days=days)
    for day in date_range(start, end):
        conn.execute(
            "INSERT OR IGNORE INTO inventory(room_type_id, date, total, sold, version)"
            " VALUES (?, ?, ?, 0, 0)",
            (room_type_id, fmt_date(day), total),
        )


def seed_demo(conn: sqlite3.Connection) -> None:
    """Insert a small demo dataset once."""
    count = conn.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"]
    if count:
        return

    hotel1 = _insert_hotel(
        conn,
        "云澜酒店·外滩",
        "上海",
        "黄浦区",
        "中山东一路 18 号",
        "021-63210000",
        "刘敏",
        "APPROVED",
    )
    hotel2 = _insert_hotel(
        conn,
        "栖岸民宿·武康路",
        "上海",
        "徐汇区",
        "武康路 210 号",
        "021-54001234",
        "朱莉",
        "APPROVED",
    )
    _insert_hotel(
        conn, "西溪小筑", "杭州", "西湖区", "西溪路 88 号", "0571-88001234", "陈坤", "PENDING"
    )

    _insert_account(conn, "13900000000", "admin123", "ADMIN", "陈一", None)
    _insert_account(conn, "13800000001", "owner123", "OWNER", "刘敏", hotel1, 1)
    _insert_account(conn, "13800000002", "desk123", "FRONT_DESK", "王芳", hotel1)
    _insert_account(conn, "13800000003", "guest123", "GUEST", "张伟", None)
    _insert_account(conn, "13700000001", "owner123", "OWNER", "朱莉", hotel2, 1)

    type1 = _insert_room_type(
        conn, hotel1, "江景大床房", 2, 12, 428.0, "入住前一天 18:00 前免费，之后收取首晚房费"
    )
    type2 = _insert_room_type(
        conn, hotel1, "城景双床房", 2, 16, 488.0, "入住前一天 18:00 前免费，之后收取首晚房费"
    )
    type3 = _insert_room_type(conn, hotel2, "湖景大床房", 1, 6, 368.0, "入住前一天 18:00 前免费")

    _insert_rooms(conn, hotel1, type1, [f"30{i}" for i in range(1, 13)])
    _insert_rooms(conn, hotel1, type2, [f"40{i}" for i in range(1, 17)])
    _insert_rooms(conn, hotel2, type3, [f"20{i}" for i in range(1, 7)])

    # Weekend price (Friday/Saturday) and a single-day promotion.
    single_day = fmt_date(today() + timedelta(days=5))
    range_start = fmt_date(today() + timedelta(days=10))
    range_end = fmt_date(today() + timedelta(days=12))
    conn.execute(
        "INSERT INTO price_rules(room_type_id, rule_type, start_date, end_date,"
        " price, created_at)"
        " VALUES (?, 'WEEKEND', '2026-01-01', '2030-12-31', 488.0, ?)",
        (type1, now_text()),
    )
    conn.execute(
        "INSERT INTO price_rules(room_type_id, rule_type, start_date, end_date,"
        " price, created_at)"
        " VALUES (?, 'WEEKEND', '2026-01-01', '2030-12-31', 558.0, ?)",
        (type2, now_text()),
    )
    conn.execute(
        "INSERT INTO price_rules(room_type_id, rule_type, start_date, end_date,"
        " price, created_at)"
        " VALUES (?, 'SINGLE', ?, ?, 528.0, ?)",
        (type1, single_day, single_day, now_text()),
    )
    conn.execute(
        "INSERT INTO price_rules(room_type_id, rule_type, start_date, end_date,"
        " price, created_at)"
        " VALUES (?, 'RANGE', ?, ?, 458.0, ?)",
        (type1, range_start, range_end, now_text()),
    )

    for name, price, stock in [
        ("早餐加购", 38.0, 200),
        ("机场接送", 180.0, 10),
        ("洗衣服务", 62.0, 50),
    ]:
        conn.execute(
            "INSERT INTO products(hotel_id, name, price, stock, status)"
            " VALUES (?, ?, ?, ?, 'ON_SALE')",
            (hotel1, name, price, stock),
        )
    conn.execute(
        "INSERT INTO products(hotel_id, name, price, stock, status) VALUES (?, ?, ?, ?, 'ON_SALE')",
        (hotel2, "早餐加购", 28.0, 100),
    )

    _ensure_inventory(conn, type1, 12)
    _ensure_inventory(conn, type2, 16)
    _ensure_inventory(conn, type3, 6)
    conn.commit()
