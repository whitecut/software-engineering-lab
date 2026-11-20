"""Bill calculation, payments and voiding."""

from __future__ import annotations

from .audit import AuditService
from .domain import PaymentMethod, Role
from .errors import NotFoundError, PermissionDeniedError, ValidationError
from .repository import Repository
from .security import require_role
from .utils import money


class BillingService:
    """Build and settle the bill of an order."""

    def __init__(self, repo: Repository, audit: AuditService) -> None:
        self.repo = repo
        self.audit = audit

    def compute(self, order: dict) -> dict[str, float]:
        """Calculate room, breakfast, other and cancellation fees."""
        nights = self.repo.nights(order["id"])
        if order["status"] == "CANCELLED":
            cancel_fee = float(order.get("cancel_fee") or 0)
            return {
                "room_fee": 0.0,
                "breakfast_fee": 0.0,
                "other_fee": 0.0,
                "cancel_fee": round(cancel_fee, 2),
                "total": round(cancel_fee, 2),
            }
        room_fee = sum(float(night["price"]) for night in nights) * int(order["rooms"])
        consumptions = [
            item for item in self.repo.consumptions(order["id"]) if item["status"] == "ACTIVE"
        ]
        breakfast_fee = sum(
            float(item["amount"]) for item in consumptions if "早餐" in item["name"]
        )
        other_fee = sum(
            float(item["amount"]) for item in consumptions if "早餐" not in item["name"]
        )
        cancel_fee = float(order.get("cancel_fee") or 0)
        total = room_fee + breakfast_fee + other_fee + cancel_fee
        return {
            "room_fee": round(room_fee, 2),
            "breakfast_fee": round(breakfast_fee, 2),
            "other_fee": round(other_fee, 2),
            "cancel_fee": round(cancel_fee, 2),
            "total": round(total, 2),
        }

    def rebuild(self, order_id: int, actor: dict | None = None) -> dict:
        """Recompute the bill and persist the amounts."""
        order = self.repo.order_by_id(order_id)
        if not order:
            raise NotFoundError("订单不存在")
        amounts = self.compute(order)
        bill = self.repo.bill_by_order(order_id)
        if bill is None:
            self.repo.create_bill(
                order_id,
                room_fee=amounts["room_fee"],
                breakfast_fee=amounts["breakfast_fee"],
                other_fee=amounts["other_fee"],
                total=amounts["total"],
            )
            self.repo.update_bill(order_id, cancel_fee=amounts["cancel_fee"])
        else:
            self.repo.update_bill(
                order_id,
                room_fee=amounts["room_fee"],
                breakfast_fee=amounts["breakfast_fee"],
                other_fee=amounts["other_fee"],
                cancel_fee=amounts["cancel_fee"],
                total=amounts["total"],
            )
        if actor:
            self.audit.record(
                actor,
                "REBUILD_BILL",
                order["order_no"],
                before_value=str(bill["total"] if bill else 0),
                after_value=str(amounts["total"]),
            )
        return self.bill(order_id)

    def bill(self, order_id: int) -> dict:
        """Return bill with payments and unpaid amount."""
        bill = self.repo.bill_by_order(order_id)
        if not bill:
            raise NotFoundError("账单不存在")
        result = dict(bill)
        result["unpaid"] = round(float(bill["total"]) - float(bill["paid"]), 2)
        result["payments"] = self.repo.payments(bill["id"])
        return result

    def add_payment(self, actor: dict, order_no: str, method: str, amount: float) -> dict:
        """Register one cash/QR payment."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        if method not in (PaymentMethod.CASH.value, PaymentMethod.QR.value):
            raise ValidationError("收款方式只能是现金或扫码")
        if amount <= 0:
            raise ValidationError("收款金额必须大于 0")
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if order["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能处理本酒店订单")
        bill = self.bill(order["id"])
        if bill["voided"]:
            raise ValidationError("账单已作废，不能收款")
        if amount > bill["unpaid"] + 1e-6:
            raise ValidationError(f"收款金额超过未收金额 {money(bill['unpaid'])}")
        self.repo.add_payment(bill["id"], method, amount, actor["id"])
        updated = self.bill(order["id"])
        self.audit.record(
            actor,
            "PAYMENT",
            f"订单 {order_no}",
            before_value=money(bill["paid"]),
            after_value=money(updated["paid"]),
        )
        return updated

    def void(self, actor: dict, order_no: str, reason: str) -> None:
        """Void a bill; only the owner or platform admin may do it."""
        require_role(actor, Role.OWNER, Role.ADMIN)
        if not reason.strip():
            raise ValidationError("作废账单必须填写原因")
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if actor.get("role") == Role.OWNER and order["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能作废本酒店账单")
        self.repo.void_bill(order["id"])
        self.audit.record(
            actor,
            "VOID_BILL",
            f"订单 {order_no}",
            before_value="有效",
            after_value=f"作废：{reason}",
        )
