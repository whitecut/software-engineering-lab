"""Operational reports and the real-time dashboard."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .domain import Role
from .repository import Repository
from .security import require_role
from .utils import fmt_date, today


class ReportService:
    """Fixed reports, occupancy and the daily snapshot."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def dashboard(self, hotel_id: int) -> dict:
        """Real-time numbers for the front desk home page."""
        day = fmt_date(today())
        new_orders = self.repo.conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE hotel_id = ? AND created_at LIKE ?",
            (hotel_id, f"{day}%"),
        ).fetchone()["n"]
        pending = self.repo.conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE hotel_id = ? AND check_in = ?"
            " AND status = 'PENDING'",
            (hotel_id, day),
        ).fetchone()["n"]
        inhouse = self.repo.conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE hotel_id = ? AND status = 'CHECKED_IN'",
            (hotel_id,),
        ).fetchone()["n"]
        remaining = []
        for room_type in self.repo.room_types(hotel_id):
            row = self.repo.inventory_row(room_type["id"], day)
            left = (row["total"] - row["sold"]) if row else 0
            remaining.append({"room_type": room_type["name"], "left": left})
        return {
            "date": day,
            "new_orders": new_orders,
            "pending_check_in": pending,
            "in_house": inhouse,
            "remaining": remaining,
        }

    def revenue(self, hotel_id: int, month: str) -> dict:
        """Room/breakfast/other revenue for a month."""
        room_fee = self.repo.conn.execute(
            "SELECT COALESCE(SUM(n.price * o.rooms), 0) AS amount FROM order_nights n"
            " JOIN orders o ON o.id = n.order_id"
            " WHERE o.hotel_id = ? AND n.date LIKE ? AND o.status <> 'CANCELLED'",
            (hotel_id, f"{month}%"),
        ).fetchone()["amount"]
        rows = self.repo.conn.execute(
            "SELECT c.name, c.amount FROM consumptions c JOIN orders o ON o.id = c.order_id"
            " WHERE o.hotel_id = ? AND c.created_at LIKE ? AND c.status = 'ACTIVE'"
            " AND o.status <> 'CANCELLED'",
            (hotel_id, f"{month}%"),
        ).fetchall()
        breakfast = sum(float(row["amount"]) for row in rows if "早餐" in row["name"])
        other = sum(float(row["amount"]) for row in rows if "早餐" not in row["name"])
        return {
            "hotel_id": hotel_id,
            "month": month,
            "room_fee": round(float(room_fee), 2),
            "breakfast_fee": round(breakfast, 2),
            "other_fee": round(other, 2),
            "total": round(float(room_fee) + breakfast + other, 2),
        }

    def occupancy(self, hotel_id: int, month: str) -> list[dict]:
        """Occupancy per room type for a month."""
        result = []
        for room_type in self.repo.room_types(hotel_id):
            row = self.repo.conn.execute(
                "SELECT COALESCE(SUM(total), 0) AS available, COALESCE(SUM(sold), 0) AS sold"
                " FROM inventory WHERE room_type_id = ? AND date LIKE ?",
                (room_type["id"], f"{month}%"),
            ).fetchone()
            available = int(row["available"])
            sold = int(row["sold"])
            result.append(
                {
                    "room_type": room_type["name"],
                    "available_nights": available,
                    "sold_nights": sold,
                    "occupancy": round(sold / available * 100, 2) if available else 0.0,
                }
            )
        return result

    def consumption_detail(self, hotel_id: int, month: str) -> list[dict]:
        """Breakfast and in-house product summary."""
        rows = self.repo.conn.execute(
            "SELECT c.name, SUM(c.qty) AS qty, SUM(c.amount) AS amount"
            " FROM consumptions c JOIN orders o ON o.id = c.order_id"
            " WHERE o.hotel_id = ? AND c.created_at LIKE ? AND c.status = 'ACTIVE'"
            " GROUP BY c.name ORDER BY c.name",
            (hotel_id, f"{month}%"),
        ).fetchall()
        return [dict(row) for row in rows]

    def city_summary(self, month: str) -> list[dict]:
        """Platform-wide revenue grouped by city."""
        rows = self.repo.conn.execute(
            "SELECT h.city, COUNT(DISTINCT o.id) AS orders,"
            " COALESCE(SUM(n.price * o.rooms), 0) AS room_fee"
            " FROM orders o JOIN hotels h ON h.id = o.hotel_id"
            " LEFT JOIN order_nights n ON n.order_id = o.id AND n.date LIKE ?"
            " WHERE o.status <> 'CANCELLED' GROUP BY h.city ORDER BY h.city",
            (f"{month}%",),
        ).fetchall()
        return [dict(row) for row in rows]

    def snapshot(self, day: date | None = None) -> int:
        """Save available/sold night snapshots for every room type."""
        target = fmt_date(day or today())
        count = 0
        for hotel in self.repo.hotels():
            for room_type in self.repo.room_types(hotel["id"]):
                row = self.repo.inventory_row(room_type["id"], target)
                if not row:
                    continue
                self.repo.upsert_snapshot(
                    target,
                    hotel["id"],
                    room_type["id"],
                    int(row["total"]),
                    int(row["sold"]),
                )
                count += 1
        self.repo.conn.commit()
        return count

    def export_revenue(self, hotel_id: int, month: str, path: str | Path) -> Path:
        """Write the monthly revenue to a CSV file."""
        data = self.revenue(hotel_id, month)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["hotel_id", "month", "room_fee", "breakfast_fee", "other_fee", "total"]
            )
            writer.writerow(
                [
                    data["hotel_id"],
                    data["month"],
                    data["room_fee"],
                    data["breakfast_fee"],
                    data["other_fee"],
                    data["total"],
                ]
            )
        return target

    def admin_overview(self, admin: dict) -> dict:
        """Platform-level counters for the admin dashboard."""
        require_role(admin, Role.ADMIN)
        total_orders = self.repo.conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
        cancelled = self.repo.conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE status = 'CANCELLED'"
        ).fetchone()["n"]
        hotels = self.repo.conn.execute(
            "SELECT COUNT(*) AS n FROM hotels WHERE status = 'APPROVED'"
        ).fetchone()["n"]
        pending_complaints = self.repo.conn.execute(
            "SELECT COUNT(*) AS n FROM complaints WHERE status IN ('PENDING', 'PROCESSING')"
        ).fetchone()["n"]
        return {
            "hotels": hotels,
            "orders": total_orders,
            "cancelled": cancelled,
            "pending_complaints": pending_complaints,
        }
