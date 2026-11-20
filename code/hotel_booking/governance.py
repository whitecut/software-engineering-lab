"""Complaints and platform governance."""

from __future__ import annotations

from .audit import AuditService
from .domain import ComplaintStatus, Role
from .errors import NotFoundError, PermissionDeniedError, ValidationError
from .repository import Repository
from .security import require_role
from .utils import now_text


class GovernanceService:
    """Complaint submission, processing and log queries."""

    def __init__(self, repo: Repository, audit: AuditService) -> None:
        self.repo = repo
        self.audit = audit

    def create_complaint(self, actor: dict, order_no: str, ctype: str, content: str) -> int:
        """A guest complains about one of their orders; order must exist."""
        require_role(actor, Role.GUEST)
        if not content.strip():
            raise ValidationError("投诉内容不能为空")
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if order["customer_id"] != actor["id"]:
            raise PermissionDeniedError("只能投诉本人订单")
        complaint_id = self.repo.create_complaint(
            order["id"], order["hotel_id"], actor["id"], ctype.strip(), content.strip()
        )
        self.audit.record(
            actor,
            "CREATE_COMPLAINT",
            f"订单 {order_no}",
            after_value=ctype,
            hotel_id=order["hotel_id"],
        )
        return complaint_id

    def handle(self, admin: dict, complaint_id: int, status: str, result: str) -> None:
        """Platform admin resolves or rejects a complaint."""
        require_role(admin, Role.ADMIN)
        if status not in (
            ComplaintStatus.PROCESSING.value,
            ComplaintStatus.RESOLVED.value,
            ComplaintStatus.REJECTED.value,
        ):
            raise ValidationError("投诉状态不正确")
        complaint = self.repo.complaint(complaint_id)
        if not complaint:
            raise NotFoundError("投诉不存在")
        if not result.strip():
            raise ValidationError("处理结果不能为空")
        self.repo.update_complaint(
            complaint_id,
            status=status,
            result=result.strip(),
            handler=admin["name"],
            handled_at=now_text(),
        )
        self.audit.record(
            admin,
            "HANDLE_COMPLAINT",
            f"投诉 {complaint_id}",
            before_value=complaint["status"],
            after_value=status,
            hotel_id=complaint["hotel_id"],
        )

    def complaints(self, actor: dict, status: str | None = None) -> list[dict]:
        """List complaints with role-based scope."""
        if actor.get("role") == Role.ADMIN.value:
            return self.repo.complaints(status=status)
        if actor.get("role") == Role.OWNER.value:
            return self.repo.complaints(status=status, hotel_id=actor.get("hotel_id"))
        if actor.get("role") == Role.GUEST.value:
            return [
                item
                for item in self.repo.complaints(status=status)
                if item["customer_id"] == actor["id"]
            ]
        return []

    def logs(self, actor: dict, action: str | None = None, limit: int = 50) -> list[dict]:
        """Query operation logs through the audit service."""
        return self.audit.logs(actor, action=action, limit=limit)
