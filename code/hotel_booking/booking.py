"""Booking, modification, cancellation and order state transitions."""

from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from .audit import AuditService
from .billing import BillingService
from .domain import (
    ORDER_TRANSITIONS,
    CancelBy,
    ConsumptionType,
    HotelStatus,
    OrderStatus,
    Role,
    RoomStatus,
)
from .errors import (
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from .inventory import InventoryService
from .pricing import PricingService
from .repository import Repository
from .security import mask_name, mask_phone, require_role
from .utils import date_range, fmt_date, money, now_text, parse_date, today


class BookingService:
    """Guest booking flow and the order state machine."""

    def __init__(
        self,
        repo: Repository,
        audit: AuditService,
        pricing: PricingService,
        inventory: InventoryService,
        billing: BillingService,
    ) -> None:
        self.repo = repo
        self.audit = audit
        self.pricing = pricing
        self.inventory = inventory
        self.billing = billing

    # ------------------------------------------------------------------
    # search and quote
    # ------------------------------------------------------------------
    def search(
        self,
        city: str,
        check_in: str,
        check_out: str,
        guests: int = 1,
        keyword: str = "",
        max_price: float | None = None,
    ) -> list[dict]:
        """Search approved hotels for the given city and date range."""
        start, end = parse_date(check_in), parse_date(check_out)
        if start >= end:
            raise ValidationError("离店日期必须晚于入住日期")
        if start < today():
            raise ValidationError("入住日期不能早于今天")
        if guests < 1:
            raise ValidationError("入住人数必须大于 0")
        days = date_range(start, end)
        results: list[dict] = []
        for hotel in self.repo.hotels(status=HotelStatus.APPROVED.value, city=city):
            for room_type in self.repo.room_types(hotel["id"]):
                if keyword and keyword not in room_type["name"]:
                    continue
                quote = self.pricing.quote(room_type, check_in, check_out)
                total = sum(price for _, price in quote)
                if max_price is not None and total / max(1, len(days)) > max_price:
                    continue
                available = self._min_available(room_type, days)
                if available < 1:
                    continue
                if any(
                    self.repo.is_stopped(hotel["id"], room_type["id"], None, fmt_date(day))
                    for day in days
                ):
                    continue
                results.append(
                    {
                        "hotel_id": hotel["id"],
                        "hotel_name": hotel["name"],
                        "district": hotel["district"],
                        "address": hotel["address"],
                        "phone": hotel["phone"],
                        "room_type_id": room_type["id"],
                        "room_type": room_type["name"],
                        "breakfast": room_type["breakfast"],
                        "cancel_rule": room_type["cancel_rule"],
                        "available": available,
                        "nightly_from": min(price for _, price in quote) if quote else 0,
                        "total_price": total,
                        "nights": len(quote),
                    }
                )
        results.sort(key=lambda item: item["total_price"])
        return results

    def _min_available(self, room_type: dict, days: list) -> int:
        self.inventory.ensure_days(room_type, days)
        return min(self.inventory.available(room_type["id"], day) for day in days) if days else 0

    def quote(self, room_type_id: int, check_in: str, check_out: str, rooms: int = 1) -> dict:
        """Quote a stay without creating an order."""
        room_type = self.repo.room_type(room_type_id)
        if not room_type:
            raise NotFoundError("房型不存在")
        nights_data = self.pricing.quote(room_type, check_in, check_out)
        if not nights_data:
            raise ValidationError("住宿晚数必须大于 0")
        total = sum(price for _, price in nights_data) * rooms
        return {
            "room_type": room_type["name"],
            "check_in": check_in,
            "check_out": check_out,
            "rooms": rooms,
            "nights": len(nights_data),
            "nightly": [(fmt_date(day), price) for day, price in nights_data],
            "total": round(total, 2),
        }

    # ------------------------------------------------------------------
    # create order
    # ------------------------------------------------------------------
    def _new_order_no(self) -> str:
        return "HT" + datetime.now().strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 999):03d}"

    def create_order(
        self,
        actor: dict,
        room_type_id: int,
        check_in: str,
        check_out: str,
        rooms: int,
        guest_name: str,
        guest_phone: str,
        eta: str = "20:00",
        idempotency_key: str | None = None,
        source: str = "SELF",
    ) -> dict:
        """Create an order, atomically reserving every night."""
        require_role(actor, Role.GUEST, Role.FRONT_DESK, Role.OWNER)
        if idempotency_key:
            existing = self.repo.idempotent_order_no(idempotency_key)
            if existing:
                order = self.repo.order(existing)
                if order:
                    return order
        start, end = parse_date(check_in), parse_date(check_out)
        if start >= end:
            raise ValidationError("离店日期必须晚于入住日期")
        if start < today():
            raise ValidationError("入住日期不能早于今天")
        if rooms < 1:
            raise ValidationError("间数必须大于 0")
        if not guest_name.strip():
            raise ValidationError("入住人姓名不能为空")
        if len(guest_phone) < 7:
            raise ValidationError("入住人手机号不合法")
        room_type = self.repo.room_type(room_type_id)
        if not room_type:
            raise NotFoundError("房型不存在")
        hotel = self.repo.hotel(room_type["hotel_id"])
        if not hotel or hotel["status"] != HotelStatus.APPROVED.value:
            raise ValidationError("酒店未通过审核，暂不可预订")
        if actor.get("role") in (Role.FRONT_DESK.value, Role.OWNER.value):
            if actor.get("hotel_id") != hotel["id"]:
                raise PermissionDeniedError("前台只能为本酒店订单代订")
            if rooms > int(room_type["room_count"]):
                raise ValidationError("间数超过房型房间数")
            source = "DESK"
        if rooms > int(room_type["room_count"]):
            raise ValidationError("间数超过房型房间数")

        days = date_range(start, end)
        self.inventory.check_available(room_type, days, rooms, hotel_id=hotel["id"])
        quote = self.pricing.quote(room_type, check_in, check_out)
        order_no = self._new_order_no()
        customer_id = actor["id"] if actor.get("role") == Role.GUEST.value else None
        with self.repo.conn:
            self.inventory.deduct(room_type["id"], days, rooms)
            order_id = self.repo.create_order(
                order_no=order_no,
                customer_id=customer_id,
                hotel_id=hotel["id"],
                room_type_id=room_type["id"],
                check_in=check_in,
                check_out=check_out,
                rooms=rooms,
                guest_name=guest_name.strip(),
                guest_phone=guest_phone.strip(),
                eta=eta,
                status=OrderStatus.PENDING.value,
                source=source,
                idempotency_key=idempotency_key,
                created_at=now_text(),
            )
            for day, price in quote:
                self.repo.add_night(order_id, fmt_date(day), price)
            room_fee = sum(price for _, price in quote) * rooms
            self.repo.create_bill(order_id, room_fee=round(room_fee, 2), total=round(room_fee, 2))
            if idempotency_key:
                self.repo.save_idempotency(idempotency_key, order_no)
            self.audit.record(
                actor,
                "CREATE_ORDER",
                f"订单 {order_no}",
                after_value=f"{check_in}~{check_out} {rooms} 间",
                hotel_id=hotel["id"],
            )
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单创建失败")
        return order

    # ------------------------------------------------------------------
    # modify and cancel
    # ------------------------------------------------------------------
    def _load_order_for_guest(self, actor: dict, order_no: str) -> dict:
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if actor.get("role") == Role.GUEST.value and order["customer_id"] != actor["id"]:
            raise PermissionDeniedError("只能操作本人订单")
        return order

    def modify_order(
        self,
        actor: dict,
        order_no: str,
        new_check_in: str,
        new_check_out: str,
        new_rooms: int,
        guest_name: str | None = None,
        guest_phone: str | None = None,
    ) -> dict:
        """Modify dates/rooms; <=2 times and always all-or-nothing."""
        order = self._load_order_for_guest(actor, order_no)
        if order["status"] != OrderStatus.PENDING.value:
            raise InvalidStateError("只有待入住订单可以修改")
        if int(order["modify_count"]) >= 2:
            raise ValidationError("同一订单最多修改 2 次")
        start, end = parse_date(new_check_in), parse_date(new_check_out)
        if start >= end:
            raise ValidationError("离店日期必须晚于入住日期")
        if start < today():
            raise ValidationError("入住日期不能早于今天")
        if new_rooms < 1:
            raise ValidationError("间数必须大于 0")
        room_type = self.repo.room_type(order["room_type_id"])
        if not room_type:
            raise NotFoundError("房型不存在")
        if new_rooms > int(room_type["room_count"]):
            raise ValidationError("间数超过房型房间数")

        old_days = date_range(parse_date(order["check_in"]), parse_date(order["check_out"]))
        new_days = date_range(start, end)
        old_prices = {
            night["date"]: float(night["price"]) for night in self.repo.nights(order["id"])
        }
        quote = self.pricing.quote(room_type, new_check_in, new_check_out)
        with self.repo.conn:
            self.inventory.release(room_type["id"], old_days, int(order["rooms"]))
            self.inventory.check_available(
                room_type, new_days, new_rooms, hotel_id=order["hotel_id"]
            )
            self.inventory.deduct(room_type["id"], new_days, new_rooms)
            self.repo.clear_nights(order["id"])
            for day, current_price in quote:
                price = old_prices.get(fmt_date(day), current_price)
                self.repo.add_night(order["id"], fmt_date(day), price)
            self.repo.update_order(
                order["id"],
                check_in=new_check_in,
                check_out=new_check_out,
                rooms=new_rooms,
                guest_name=guest_name or order["guest_name"],
                guest_phone=guest_phone or order["guest_phone"],
                modify_count=int(order["modify_count"]) + 1,
            )
            self.billing.rebuild(order["id"], actor)
            self.audit.record(
                actor,
                "MODIFY_ORDER",
                f"订单 {order_no}",
                before_value=f"{order['check_in']}~{order['check_out']} {order['rooms']} 间",
                after_value=f"{new_check_in}~{new_check_out} {new_rooms} 间",
                hotel_id=order["hotel_id"],
            )
        return self.repo.order(order_no) or {}

    def cancel_fee(self, order: dict) -> float:
        """Charge the first night when cancelling after the deadline."""
        first_night = self.repo.nights(order["id"])
        if not first_night:
            return 0.0
        price = float(first_night[0]["price"]) * int(order["rooms"])
        deadline = datetime.combine(
            parse_date(order["check_in"]) - timedelta(days=1), time(hour=18)
        )
        return 0.0 if datetime.now() < deadline else round(price, 2)

    def cancel_order(self, actor: dict, order_no: str, by: str, reason: str = "") -> dict:
        """Cancel a pending order and release its inventory."""
        order = self._load_order_for_guest(actor, order_no)
        if order["status"] != OrderStatus.PENDING.value:
            raise InvalidStateError("只有待入住订单可以取消")
        if by not in (CancelBy.GUEST.value, CancelBy.HOTEL.value, CancelBy.PLATFORM.value):
            raise ValidationError("取消方不正确")
        if by != CancelBy.GUEST.value and not reason.strip():
            raise ValidationError("酒店或平台取消必须填写原因")
        fee = self.cancel_fee(order)
        days = date_range(parse_date(order["check_in"]), parse_date(order["check_out"]))
        with self.repo.conn:
            self.inventory.release(order["room_type_id"], days, int(order["rooms"]))
            self.repo.update_order(
                order["id"], status=OrderStatus.CANCELLED.value, cancel_by=by, cancel_fee=fee
            )
            self.repo.update_bill(order["id"], cancel_fee=fee)
            self.billing.rebuild(order["id"], actor)
            self.audit.record(
                actor,
                "CANCEL_ORDER",
                f"订单 {order_no}",
                before_value=order["status"],
                after_value=f"CANCELLED by {by} fee={money(fee)}",
                hotel_id=order["hotel_id"],
            )
        return self.repo.order(order_no) or {}

    # ------------------------------------------------------------------
    # front desk state changes
    # ------------------------------------------------------------------
    def _check_transition(self, order: dict, target: str) -> None:
        current = OrderStatus(order["status"])
        if OrderStatus(target) not in ORDER_TRANSITIONS.get(current, set()):
            raise InvalidStateError(f"订单不能从 {current.value} 变为 {target}")

    def check_in(self, actor: dict, order_no: str, room_no: str) -> dict:
        """Assign a room and move the order to CHECKED_IN."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if order["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能办理本酒店订单")
        if order["status"] != OrderStatus.PENDING.value:
            raise InvalidStateError("只有待入住订单可以办理入住")
        room = self.repo.room_by_no(order["hotel_id"], room_no)
        if not room:
            raise NotFoundError("房间不存在")
        if room["room_type_id"] != order["room_type_id"]:
            raise ValidationError("房间与订单房型不一致")
        if room["status"] not in (RoomStatus.FREE.value, RoomStatus.RESERVED.value):
            raise ValidationError("房间当前不可分配")
        if self.repo.room_conflicts(
            room["id"], order["check_in"], order["check_out"], exclude_order_id=order["id"]
        ):
            raise ValidationError("该房间在入住期间已分配给其他订单")
        self._check_transition(order, OrderStatus.CHECKED_IN.value)
        with self.repo.conn:
            self.repo.set_room_status(room["id"], RoomStatus.OCCUPIED.value)
            self.repo.add_order_room(order["id"], room["id"], room_no)
            self.repo.update_order(
                order["id"], status=OrderStatus.CHECKED_IN.value, checked_in_at=now_text()
            )
            self.audit.record(
                actor,
                "CHECK_IN",
                f"订单 {order_no}",
                before_value=order["status"],
                after_value=f"CHECKED_IN room {room_no}",
                hotel_id=order["hotel_id"],
            )
        return self.repo.order(order_no) or {}

    def check_out(self, actor: dict, order_no: str) -> dict:
        """Check out the order and mark its rooms dirty."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if order["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能办理本酒店订单")
        if order["status"] != OrderStatus.CHECKED_IN.value:
            raise InvalidStateError("只有已入住订单可以退房")
        self._check_transition(order, OrderStatus.CHECKED_OUT.value)
        with self.repo.conn:
            for item in self.repo.order_rooms(order["id"]):
                self.repo.set_room_status(item["room_id"], RoomStatus.DIRTY.value)
            self.repo.update_order(
                order["id"], status=OrderStatus.CHECKED_OUT.value, checked_out_at=now_text()
            )
            self.billing.rebuild(order["id"], actor)
            self.audit.record(
                actor,
                "CHECK_OUT",
                f"订单 {order_no}",
                before_value=order["status"],
                after_value="CHECKED_OUT",
                hotel_id=order["hotel_id"],
            )
        return self.repo.order(order_no) or {}

    def mark_no_show(self, actor: dict, order_no: str) -> dict:
        """Mark a pending order as no-show."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if order["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能处理本酒店订单")
        self._check_transition(order, OrderStatus.NO_SHOW.value)
        with self.repo.conn:
            self.repo.update_order(order["id"], status=OrderStatus.NO_SHOW.value)
            self.audit.record(
                actor,
                "NO_SHOW",
                f"订单 {order_no}",
                before_value=order["status"],
                after_value="NO_SHOW",
                hotel_id=order["hotel_id"],
            )
        return self.repo.order(order_no) or {}

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def my_orders(self, actor: dict) -> list[dict]:
        """Guest's own orders."""
        require_role(actor, Role.GUEST)
        return self.repo.orders_by_customer(actor["id"])

    def order_detail(self, actor: dict, order_no: str, view_full_phone: bool = False) -> dict:
        """Return an order with bill, consumptions and privacy masking."""
        order = self._load_order_for_guest(actor, order_no)
        if actor.get("role") in (Role.FRONT_DESK.value, Role.OWNER.value):
            if order["hotel_id"] != actor.get("hotel_id"):
                raise PermissionDeniedError("只能查看本酒店订单")
        if actor.get("role") in (Role.OWNER.value, Role.ADMIN.value):
            if order["hotel_id"] != actor.get("hotel_id") and actor.get("role") != Role.ADMIN.value:
                raise PermissionDeniedError("只能查看本酒店订单")
            if view_full_phone:
                if actor.get("role") == Role.ADMIN.value:
                    self.audit.record_privacy_view(actor, order_no, order["guest_phone"])
                elif actor.get("hotel_id") == order["hotel_id"]:
                    self.audit.record_privacy_view(actor, order_no, order["guest_phone"])
        detail = dict(order)
        if actor.get("role") in (Role.OWNER.value, Role.ADMIN.value) and not view_full_phone:
            detail["guest_phone"] = mask_phone(order["guest_phone"])
            detail["guest_name"] = mask_name(order["guest_name"])
        detail["nights"] = self.repo.nights(order["id"])
        detail["bill"] = self.billing.bill(order["id"])
        detail["consumptions"] = self.repo.consumptions(order["id"])
        detail["rooms"] = self.repo.order_rooms(order["id"])
        return detail

    def hotel_orders(self, actor: dict, status: str | None = None) -> list[dict]:
        """Orders of the actor's hotel."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        return self.repo.orders_by_hotel(actor["hotel_id"], status)

    def find_orders(self, actor: dict, keyword: str) -> list[dict]:
        """Search orders by order number, phone or guest name."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        return self.repo.find_orders(actor["hotel_id"], keyword)

    def add_consumption(
        self,
        actor: dict,
        order_no: str,
        product_name: str,
        qty: int,
        ctype: str = ConsumptionType.IN_HOUSE.value,
        confirmed_by: str = "FRONT_DESK",
    ) -> int:
        """Register a product purchase on an order."""
        require_role(actor, Role.FRONT_DESK, Role.OWNER)
        order = self.repo.order(order_no)
        if not order:
            raise NotFoundError("订单不存在")
        if order["hotel_id"] != actor.get("hotel_id"):
            raise PermissionDeniedError("只能处理本酒店订单")
        if order["status"] not in (OrderStatus.PENDING.value, OrderStatus.CHECKED_IN.value):
            raise InvalidStateError("订单当前不能登记消费")
        product = self.repo.product_by_name(order["hotel_id"], product_name)
        if not product:
            raise NotFoundError("商品不存在")
        if qty < 1:
            raise ValidationError("数量必须大于 0")
        amount = round(float(product["price"]) * qty, 2)
        with self.repo.conn:
            consumption_id = self.repo.add_consumption(
                order["id"],
                product["name"],
                ctype,
                qty,
                float(product["price"]),
                amount,
                confirmed_by,
                product["id"],
            )
            self.repo.change_stock(product["id"], -qty)
            self.billing.rebuild(order["id"], actor)
            self.audit.record(
                actor,
                "ADD_CONSUMPTION",
                f"订单 {order_no} {product['name']}",
                after_value=f"{qty} x {money(float(product['price']))}",
                hotel_id=order["hotel_id"],
            )
        return consumption_id
