"""Audit logging used by every write service."""

from __future__ import annotations

from .repository import Repository


class AuditService:
    """Write and read operation logs."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def record(
        self,
        actor: dict | None,
        action: str,
        target: str,
        before_value: str = "",
        after_value: str = "",
        result: str = "OK",
        hotel_id: int | None = None,
    ) -> None:
        """Append one operation log entry."""
        account_id = actor.get("id") if actor else None
        role = actor.get("role", "SYSTEM") if actor else "SYSTEM"
        if hotel_id is None and actor:
            hotel_id = actor.get("hotel_id")
        self.repo.add_log(
            account_id, role, action, target, before_value, after_value, result, hotel_id
        )

    def record_privacy_view(self, actor: dict, order_no: str, _guest_phone: str) -> None:
        """Record a full phone-number lookup (REQ-028)."""
        self.record(
            actor,
            "VIEW_FULL_PHONE",
            f"订单 {order_no}",
            before_value="",
            after_value="查看手机号全号（已留痕）",
        )

    def logs(
        self, actor: dict, hotel_id: int | None = None, action: str | None = None, limit: int = 100
    ) -> list[dict]:
        """List logs with the role-based data scope."""
        if actor.get("role") == "ADMIN":
            return self.repo.logs(hotel_id=hotel_id, action=action, limit=limit)
        if actor.get("role") in ("OWNER", "FRONT_DESK"):
            if actor.get("role") == "FRONT_DESK":
                return self.repo.logs(account_id=actor["id"], action=action, limit=limit)
            return self.repo.logs(hotel_id=actor.get("hotel_id"), action=action, limit=limit)
        return self.repo.logs(account_id=actor["id"], action=action, limit=limit)
