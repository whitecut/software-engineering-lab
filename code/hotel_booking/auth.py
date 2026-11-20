"""Authentication and guest registration."""

from __future__ import annotations

from .domain import AccountStatus, Role
from .errors import ConflictError, PermissionDeniedError, ValidationError
from .repository import Repository
from .security import hash_password, verify_password
from .utils import now_text


class AuthService:
    """Login and guest account registration."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def login(self, phone: str, password: str) -> dict:
        """Authenticate an account and return the actor dictionary."""
        account = self.repo.account_by_phone(phone)
        if not account or not verify_password(password, account["password_hash"]):
            raise PermissionDeniedError("手机号或密码错误")
        if account["status"] != AccountStatus.ACTIVE.value:
            raise PermissionDeniedError("账号已停用")
        actor = dict(account)
        actor.pop("password_hash", None)
        return actor

    def register_guest(self, phone: str, password: str, name: str) -> dict:
        """Register a guest account."""
        if len(phone) < 7:
            raise ValidationError("手机号不合法")
        if len(password) < 6:
            raise ValidationError("密码至少 6 位")
        if not name.strip():
            raise ValidationError("姓名不能为空")
        if self.repo.account_by_phone(phone):
            raise ConflictError("手机号已注册")
        account_id = self.repo.create_account(
            phone, hash_password(password), Role.GUEST.value, name.strip()
        )
        self.repo.add_log(
            account_id, Role.GUEST.value, "REGISTER", f"客人 {name}", after_value=now_text()
        )
        return self.repo.account_by_id(account_id) or {}
