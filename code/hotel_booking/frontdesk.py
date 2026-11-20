"""Front desk operations: room board, room status and refunds."""

from __future__ import annotations

from .audit import AuditService
from .billing import BillingService
from .domain import ROOM_TRANSITIONS, OrderStatus, Role, RoomStatus
from .errors import InvalidStateError, NotFoundError, PermissionDeniedError, ValidationError
from .repository import Repository
from .security import require_role


class FrontDeskService:
    """Day-to-day operations performed by the front desk."""

    def __init__(self, repo: Repository, audit: AuditService, billing: BillingService) -> None:
        self.repo = repo
        self.audit = audit
        self.billing = billing

    def room_board(self, actor: dict) -> list[dict]:
        """Return all rooms with the current in-house order, if any."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        result: list[dict] = []
        for room in self.repo.rooms(actor["hotel_id"]):
            rows = self.repo.conn.execute(
                "SELECT o.order_no, o.guest_name FROM order_rooms r"
                " JOIN orders o ON o.id = r.order_id"
                " WHERE r.room_id = ? AND o.status = 'CHECKED_IN' LIMIT 1",
                (room["id"],),
            ).fetchone()
            item = dict(room)
            item["guest"] = rows["guest_name"] if rows else ""
            item["order_no"] = rows["order_no"] if rows else ""
            result.append(item)
        return result

    def change_room_status(self, actor: dict, room_no: str, target: str, reason: str = "") -> None:
        """Move a room along the allowed state machine."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        room = self.repo.room_by_no(actor["hotel_id"], room_no)
        if not room:
            raise NotFoundError("房间不存在")
        current = RoomStatus(room["status"])
        if target not in {item.value for item in ROOM_TRANSITIONS.get(current, set())}:
            raise InvalidStateError(f"房间不能从 {current.value} 变为 {target}")
        if target == RoomStatus.OCCUPIED.value:
            raise ValidationError("在住状态只能通过办理入住产生")
        if target == RoomStatus.MAINTENANCE.value and not reason.strip():
            raise ValidationError("维修必须填写原因")
        self.repo.set_room_status(room["id"], target)
        self.audit.record(
            actor,
            "ROOM_STATUS",
            f"房间 {room_no}",
            before_value=current.value,
            after_value=target,
            hotel_id=actor["hotel_id"],
        )

    def refund_consumption(self, actor: dict, consumption_id: int, reason: str) -> None:
        """Refund one in-house consumption before checkout."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        row = self.repo.conn.execute(
            "SELECT c.*, o.hotel_id, o.status AS order_status, o.id AS order_id, o.order_no"
            " FROM consumptions c JOIN orders o ON o.id = c.order_id WHERE c.id = ?",
            (consumption_id,),
        ).fetchone()
        if not row:
            raise NotFoundError("消费记录不存在")
        if row["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能处理本酒店消费")
        if row["status"] != "ACTIVE":
            raise ValidationError("该消费已退款")
        if row["order_status"] in (OrderStatus.CHECKED_OUT.value, OrderStatus.CANCELLED.value):
            raise InvalidStateError("退房或取消后不能退款")
        if not reason.strip():
            raise ValidationError("退款必须填写原因")
        with self.repo.conn:
            self.repo.refund_consumption(consumption_id)
            if row["product_id"]:
                self.repo.change_stock(row["product_id"], int(row["qty"]))
            self.billing.rebuild(row["order_id"], actor)
            self.audit.record(
                actor,
                "REFUND_CONSUMPTION",
                f"订单 {row['order_no']} {row['name']}",
                before_value=str(row["amount"]),
                after_value=f"退款：{reason}",
                hotel_id=actor["hotel_id"],
            )
