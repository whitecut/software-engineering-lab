"""Password hashing and privacy masking."""

from __future__ import annotations

import hashlib
import hmac
import os

from .domain import Role
from .errors import PermissionDeniedError

_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


def mask_phone(phone: str) -> str:
    """Mask the middle digits of a mobile number."""
    if not phone or len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def mask_name(name: str) -> str:
    """Mask all but the first character of a name."""
    if not name:
        return name
    return name[0] + "*" * max(1, len(name) - 1)


def require_role(actor: dict, *roles: Role) -> None:
    """Raise if the actor does not have one of the required roles."""
    allowed = {role.value for role in roles}
    if not actor or actor.get("role") not in allowed:
        raise PermissionDeniedError("当前账号无权执行该操作")
