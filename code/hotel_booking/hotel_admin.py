"""Hotel onboarding, room/price/stop-sale maintenance and staff accounts."""

from __future__ import annotations

from datetime import datetime, timedelta

from .audit import AuditService
from .domain import HotelStatus, PriceRuleType, Role, StopScope
from .errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from .repository import Repository
from .security import hash_password, require_role
from .utils import date_range, fmt_date, money, now_text, parse_date, today

MAX_STAFF = 10


class HotelAdminService:
    """Owner-facing maintenance plus platform review operations."""

    def __init__(self, repo: Repository, audit: AuditService) -> None:
        self.repo = repo
        self.audit = audit

    # ------------------------------------------------------------------
    # onboarding and review
    # ------------------------------------------------------------------
    def register_hotel(
        self,
        owner_name: str,
        phone: str,
        password: str,
        name: str,
        city: str,
        district: str,
        address: str,
        hotel_phone: str,
        room_types: list[dict],
    ) -> dict:
        """Register a hotel and its owner account; status starts as PENDING."""
        if self.repo.account_by_phone(phone):
            raise ConflictError("手机号已注册")
        if not room_types:
            raise ValidationError("至少需要提交一个房型")
        if len(password) < 6:
            raise ValidationError("密码至少 6 位")
        hotel_id = self.repo.create_hotel(
            name, city, district, address, hotel_phone, owner_name, HotelStatus.PENDING.value
        )
        self.repo.create_account(
            phone, hash_password(password), Role.OWNER.value, owner_name, hotel_id, 1
        )
        for index, item in enumerate(room_types, start=1):
            self._validate_room_type(item)
            type_id = self.repo.create_room_type(
                hotel_id,
                item["name"],
                int(item.get("breakfast", 0)),
                int(item["room_count"]),
                float(item["base_price"]),
                item.get("cancel_rule", "入住前一天 18:00 前免费"),
            )
            for number in range(1, int(item["room_count"]) + 1):
                self.repo.create_room(hotel_id, type_id, f"{index}{number:02d}")
            self.repo.ensure_inventory(
                type_id,
                fmt_date(today()),
                fmt_date(today() + timedelta(days=180)),
                int(item["room_count"]),
            )
        self.audit.record(
            None, "HOTEL_APPLY", f"酒店 {name}", after_value="待审核", hotel_id=hotel_id
        )
        return {"hotel_id": hotel_id, "status": HotelStatus.PENDING.value}

    @staticmethod
    def _validate_room_type(item: dict) -> None:
        if not str(item.get("name", "")).strip():
            raise ValidationError("房型名称不能为空")
        count = int(item.get("room_count", 0))
        price = float(item.get("base_price", 0))
        if count <= 0 or count > 200:
            raise ValidationError("房间数必须在 1~200 之间")
        if price < 1 or price > 99999:
            raise ValidationError("房价必须在 1~99999 元之间")

    def review(self, admin: dict, hotel_id: int, approve: bool, reason: str = "") -> None:
        """Approve or reject a pending hotel."""
        require_role(admin, Role.ADMIN)
        hotel = self.repo.hotel(hotel_id)
        if not hotel:
            raise NotFoundError("酒店不存在")
        if hotel["status"] != HotelStatus.PENDING.value:
            raise ValidationError("该酒店不在待审核状态")
        if not approve and not reason.strip():
            raise ValidationError("退回必须填写原因")
        status = HotelStatus.APPROVED.value if approve else HotelStatus.REJECTED.value
        self.repo.set_hotel_status(hotel_id, status)
        self.audit.record(
            admin,
            "HOTEL_REVIEW",
            f"酒店 {hotel['name']}",
            before_value=hotel["status"],
            after_value=f"{status} {reason}".strip(),
            hotel_id=hotel_id,
        )

    def change_status(self, admin: dict, hotel_id: int, status: str, reason: str) -> None:
        """Take a hotel offline or ban it; approval is not allowed here."""
        require_role(admin, Role.ADMIN)
        if status not in (
            HotelStatus.OFFLINE.value,
            HotelStatus.BANNED.value,
            HotelStatus.APPROVED.value,
        ):
            raise ValidationError("不支持的酒店状态")
        hotel = self.repo.hotel(hotel_id)
        if not hotel:
            raise NotFoundError("酒店不存在")
        self.repo.set_hotel_status(hotel_id, status)
        if status == HotelStatus.OFFLINE.value:
            # Stop sale for all future dates so that no new order is accepted.
            self.repo.add_stop_sale(
                hotel_id,
                StopScope.HOTEL.value,
                fmt_date(today()),
                fmt_date(today() + timedelta(days=180)),
                reason or "平台下架",
                room_type_id=None,
                room_id=None,
            )
        self.audit.record(
            admin,
            "HOTEL_STATUS",
            f"酒店 {hotel['name']}",
            before_value=hotel["status"],
            after_value=status,
            hotel_id=hotel_id,
        )

    def pending_hotels(self) -> list[dict]:
        """List hotels waiting for review."""
        return self.repo.hotels(status=HotelStatus.PENDING.value)

    # ------------------------------------------------------------------
    # room types and rooms
    # ------------------------------------------------------------------
    def _room_type_for_owner(self, actor: dict, room_type_id: int) -> dict:
        room_type = self.repo.room_type(room_type_id)
        if not room_type:
            raise NotFoundError("房型不存在")
        if room_type["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能维护本酒店房型")
        return room_type

    def room_types(self, actor: dict) -> list[dict]:
        """List room types of the actor's hotel."""
        require_role(actor, Role.OWNER, Role.FRONT_DESK)
        return self.repo.room_types(actor["hotel_id"])

    def add_room_type(
        self,
        actor: dict,
        name: str,
        breakfast: int,
        room_count: int,
        base_price: float,
        cancel_rule: str,
    ) -> int:
        """Create one room type and its rooms."""
        require_role(actor, Role.OWNER)
        item = {
            "name": name,
            "room_count": room_count,
            "base_price": base_price,
            "breakfast": breakfast,
        }
        self._validate_room_type(item)
        type_id = self.repo.create_room_type(
            actor["hotel_id"], name, breakfast, room_count, base_price, cancel_rule
        )
        existing = self.repo.rooms(actor["hotel_id"])
        index = len({room["room_no"][0] for room in existing}) + 1
        for number in range(1, room_count + 1):
            self.repo.create_room(actor["hotel_id"], type_id, f"{index}{number:02d}")
        self.repo.ensure_inventory(
            type_id, fmt_date(today()), fmt_date(today() + timedelta(days=180)), room_count
        )
        self.audit.record(
            actor,
            "ADD_ROOM_TYPE",
            f"房型 {name}",
            after_value=f"{room_count} 间 / {money(base_price)} 元",
            hotel_id=actor["hotel_id"],
        )
        return type_id

    def update_room_type(self, actor: dict, room_type_id: int, **fields) -> None:
        """Update room type attributes; room-count changes start tomorrow."""
        require_role(actor, Role.OWNER)
        room_type = self._room_type_for_owner(actor, room_type_id)
        if "room_count" in fields:
            count = int(fields["room_count"])
            if count <= 0 or count > 200:
                raise ValidationError("房间数必须在 1~200 之间")
            fields["room_count"] = count
            self.repo.ensure_inventory(
                room_type_id,
                fmt_date(today() + timedelta(days=1)),
                fmt_date(today() + timedelta(days=180)),
                count,
            )
            self.repo.set_inventory_total(
                room_type_id, fmt_date(today() + timedelta(days=1)), count
            )
            self.repo.update_room_type(room_type_id, **fields)
        else:
            self.repo.update_room_type(room_type_id, **fields)
        self.audit.record(
            actor,
            "UPDATE_ROOM_TYPE",
            f"房型 {room_type['name']}",
            before_value=str(dict(room_type)),
            after_value=str(fields),
            hotel_id=actor["hotel_id"],
        )

    def add_room(self, actor: dict, room_type_id: int, room_no: str) -> int:
        """Add a physical room to an existing room type."""
        require_role(actor, Role.OWNER)
        room_type = self._room_type_for_owner(actor, room_type_id)
        if self.repo.room_by_no(actor["hotel_id"], room_no):
            raise ConflictError("房间号已存在")
        room_id = self.repo.create_room(actor["hotel_id"], room_type_id, room_no)
        self.repo.update_room_type(room_type_id, room_count=int(room_type["room_count"]) + 1)
        self.audit.record(
            actor, "ADD_ROOM", f"{room_type['name']} {room_no}", hotel_id=actor["hotel_id"]
        )
        return room_id

    def rooms(self, actor: dict, room_type_id: int | None = None) -> list[dict]:
        """List rooms of the hotel."""
        require_role(actor, Role.OWNER, Role.FRONT_DESK)
        return self.repo.rooms(actor["hotel_id"], room_type_id)

    # ------------------------------------------------------------------
    # price rules and approvals
    # ------------------------------------------------------------------
    def add_price_rule(
        self, actor: dict, room_type_id: int, rule_type: str, start: str, end: str, price: float
    ) -> int:
        """Add a weekend/range/single-day rule."""
        require_role(actor, Role.OWNER)
        room_type = self._room_type_for_owner(actor, room_type_id)
        if rule_type not in (
            PriceRuleType.SINGLE.value,
            PriceRuleType.RANGE.value,
            PriceRuleType.WEEKEND.value,
        ):
            raise ValidationError("价格类型只能是 SINGLE/RANGE/WEEKEND")
        if price < 1 or price > 99999:
            raise ValidationError("房价必须在 1~99999 元之间")
        if parse_date(start) > parse_date(end):
            raise ValidationError("开始日期不能晚于结束日期")
        rule_id = self.repo.add_price_rule(room_type_id, rule_type, start, end, price)
        self.audit.record(
            actor,
            "ADD_PRICE_RULE",
            f"{room_type['name']} {rule_type}",
            after_value=f"{start}~{end} {money(price)} 元",
            hotel_id=actor["hotel_id"],
        )
        return rule_id

    def set_base_price(self, actor: dict, room_type_id: int, new_price: float) -> str:
        """Change the base price; >5x requires platform approval."""
        require_role(actor, Role.OWNER)
        room_type = self._room_type_for_owner(actor, room_type_id)
        if new_price < 1 or new_price > 99999:
            raise ValidationError("房价必须在 1~99999 元之间")
        old_price = float(room_type["base_price"])
        if new_price > old_price * 5:
            expires = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            approval_id = self.repo.add_price_approval(room_type_id, old_price, new_price, expires)
            self.audit.record(
                actor,
                "PRICE_APPROVAL_REQUEST",
                f"房型 {room_type['name']}",
                before_value=money(old_price),
                after_value=money(new_price),
                hotel_id=actor["hotel_id"],
            )
            return f"涨幅超过 5 倍，已提交平台审批（编号 {approval_id}）"
        self.repo.update_room_type(room_type_id, base_price=new_price)
        self.audit.record(
            actor,
            "SET_BASE_PRICE",
            f"房型 {room_type['name']}",
            before_value=money(old_price),
            after_value=money(new_price),
            hotel_id=actor["hotel_id"],
        )
        return "基础价已更新"

    def approve_price(self, admin: dict, approval_id: int, approve: bool) -> None:
        """Approve a pending price change before its 7-day deadline."""
        require_role(admin, Role.ADMIN)
        approval = self.repo.price_approval(approval_id)
        if not approval:
            raise NotFoundError("审批记录不存在")
        if approval["status"] != "PENDING":
            raise ValidationError("该审批已处理")
        if approval["expires_at"] < now_text():
            self.repo.update_price_approval(approval_id, "EXPIRED")
            raise ValidationError("审批已超过 7 天，自动失效")
        status = "APPROVED" if approve else "REJECTED"
        self.repo.update_price_approval(approval_id, status)
        if approve:
            self.repo.update_room_type(
                approval["room_type_id"], base_price=float(approval["new_price"])
            )
        self.audit.record(
            admin,
            "PRICE_APPROVAL",
            f"审批 {approval_id}",
            before_value="PENDING",
            after_value=status,
        )

    def pending_approvals(self) -> list[dict]:
        """Return pending price approvals."""
        return self.repo.price_approvals(status="PENDING")

    # ------------------------------------------------------------------
    # stop sales
    # ------------------------------------------------------------------
    def stop_sale(
        self,
        actor: dict,
        scope: str,
        start: str,
        end: str,
        reason: str,
        room_type_id: int | None = None,
        room_no: str | None = None,
    ) -> int:
        """Stop sale for the hotel, a room type or one room."""
        require_role(actor, Role.OWNER)
        if scope not in (StopScope.HOTEL.value, StopScope.ROOM_TYPE.value, StopScope.ROOM.value):
            raise ValidationError("停售范围不正确")
        if not reason.strip():
            raise ValidationError("停售必须填写原因")
        start_date, end_date = parse_date(start), parse_date(end)
        if start_date > end_date:
            raise ValidationError("停售开始日期不能晚于结束日期")

        room_id = None
        target_type = room_type_id
        if scope == StopScope.ROOM.value:
            if not room_no:
                raise ValidationError("单间房停售需要指定房间号")
            room = self.repo.room_by_no(actor["hotel_id"], room_no)
            if not room:
                raise NotFoundError("房间不存在")
            room_id = room["id"]
            target_type = room["room_type_id"]
        elif scope == StopScope.ROOM_TYPE.value:
            if not room_type_id:
                raise ValidationError("房型停售需要指定房型")
            room_type = self._room_type_for_owner(actor, room_type_id)
            target_type = room_type["id"]
        else:
            target_type = None

        for hotel_type in self.repo.room_types(actor["hotel_id"]):
            if target_type and hotel_type["id"] != target_type:
                continue
            conflicts = self.repo.orders_overlapping(hotel_type["id"], start, end, room_id)
            if conflicts:
                raise ValidationError(f"{hotel_type['name']} 在停售区间已有订单，请先改单或取消")

        stop_id = self.repo.add_stop_sale(
            actor["hotel_id"],
            scope,
            start,
            end,
            reason,
            room_type_id=target_type,
            room_id=room_id,
        )
        if scope == StopScope.ROOM.value and room_id:
            # A single-room stop sale reduces the type's sellable count by one.
            days = date_range(start_date, end_date.fromordinal(end_date.toordinal() + 1))
            for day in days:
                self.repo.ensure_inventory(
                    target_type,
                    fmt_date(day),
                    fmt_date(day.fromordinal(day.toordinal() + 1)),
                    int(self._room_type_for_owner(actor, target_type)["room_count"]),
                )
                self.repo.deduct(target_type, fmt_date(day), 1)
        self.audit.record(
            actor,
            "STOP_SALE",
            f"{scope} {start}~{end}",
            after_value=reason,
            hotel_id=actor["hotel_id"],
        )
        return stop_id

    # ------------------------------------------------------------------
    # products and staff
    # ------------------------------------------------------------------
    def add_product(self, actor: dict, name: str, price: float, stock: int) -> int:
        """Add an extra product; names are unique inside a hotel."""
        require_role(actor, Role.OWNER)
        if price < 1 or price > 9999:
            raise ValidationError("商品单价必须在 1~9999 元之间")
        if stock < 0:
            raise ValidationError("库存不能为负数")
        if self.repo.product_by_name(actor["hotel_id"], name):
            raise ConflictError("同一酒店内商品名称不能重复")
        product_id = self.repo.create_product(actor["hotel_id"], name, price, stock)
        self.audit.record(
            actor,
            "ADD_PRODUCT",
            name,
            after_value=f"{money(price)} 元 / {stock}",
            hotel_id=actor["hotel_id"],
        )
        return product_id

    def restock(self, actor: dict, product_id: int, delta: int) -> None:
        """Increase or decrease product stock."""
        require_role(actor, Role.OWNER)
        product = self.repo.product(product_id)
        if not product or product["hotel_id"] != actor["hotel_id"]:
            raise NotFoundError("商品不存在")
        self.repo.change_stock(product_id, delta)
        self.audit.record(
            actor,
            "CHANGE_STOCK",
            product["name"],
            before_value=str(product["stock"]),
            after_value=str(product["stock"] + delta),
            hotel_id=actor["hotel_id"],
        )

    def add_staff(self, actor: dict, phone: str, name: str, password: str) -> int:
        """Create a front-desk sub-account; at most 10 per hotel."""
        require_role(actor, Role.OWNER)
        if not actor.get("is_primary"):
            raise PermissionDeniedError("只有老板主账号可以开立子账号")
        if self.repo.account_by_phone(phone):
            raise ConflictError("手机号已注册")
        staff = self.repo.accounts_by_hotel(actor["hotel_id"])
        if len([item for item in staff if item["role"] == Role.FRONT_DESK.value]) >= MAX_STAFF:
            raise ValidationError("前台子账号最多 10 个")
        if len(password) < 6:
            raise ValidationError("密码至少 6 位")
        account_id = self.repo.create_account(
            phone, hash_password(password), Role.FRONT_DESK.value, name, actor["hotel_id"]
        )
        self.audit.record(actor, "ADD_STAFF", name, after_value=phone, hotel_id=actor["hotel_id"])
        return account_id

    def disable_staff(self, actor: dict, account_id: int) -> None:
        """Disable a front-desk account; history is kept."""
        require_role(actor, Role.OWNER)
        account = self.repo.account_by_id(account_id)
        if not account or account["hotel_id"] != actor["hotel_id"]:
            raise NotFoundError("账号不存在")
        if account["role"] != Role.FRONT_DESK.value:
            raise ValidationError("只能停用前台子账号")
        self.repo.set_account_status(account_id, "DISABLED")
        self.audit.record(
            actor,
            "DISABLE_STAFF",
            account["name"],
            after_value="已停用",
            hotel_id=actor["hotel_id"],
        )

    def staff(self, actor: dict) -> list[dict]:
        """List hotel-side accounts."""
        require_role(actor, Role.OWNER)
        return [
            item
            for item in self.repo.accounts_by_hotel(actor["hotel_id"])
            if item["role"] in (Role.OWNER.value, Role.FRONT_DESK.value)
        ]
