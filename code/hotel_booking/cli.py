"""Interactive command line interface for the hotel booking system."""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from .app import App
from .demo import run_demo
from .domain import CancelBy, Role
from .errors import DomainError
from .utils import fmt_date, money, parse_date, today

LINE = "=" * 78


def table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a simple fixed-width table."""
    if not rows:
        print("（暂无数据）")
        return
    widths = [len(head) for head in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(str(cell)))
    fmt = "  ".join(f"{{:<{width}}}" for width in widths)
    print(fmt.format(*headers))
    print("-" * (sum(widths) + 2 * (len(widths) - 1)))
    for row in rows:
        print(fmt.format(*[str(cell) for cell in row]))


def ask(prompt: str, default: str = "") -> str:
    """Read a string with a default value."""
    value = input(f"{prompt}" + (f" [{default}]" if default else "") + "：").strip()
    return value or default


def ask_int(prompt: str, default: int = 0) -> int:
    """Read an integer, keeping the default on invalid input."""
    raw = ask(prompt, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def ask_date(prompt: str, default: str | None = None) -> str:
    """Read an ISO date, retrying on invalid input."""
    fallback = default or fmt_date(today() + timedelta(days=1))
    while True:
        raw = ask(prompt, fallback)
        try:
            return fmt_date(parse_date(raw))
        except ValueError:
            print("日期格式应为 YYYY-MM-DD")


class Cli:
    """Menu driven shell for the four roles."""

    def __init__(self, app: App) -> None:
        """Handle the   init   command."""
        self.app = app
        self.actor: dict | None = None

    def run(self) -> None:
        """Start the main loop."""
        print(LINE)
        print("酒店预订系统 · 软件工程实验三原型")
        print(
            "演示账号：admin 13900000000/admin123，老板 13800000001/owner123，"
            "前台 13800000002/desk123，客人 13800000003/guest123"
        )
        print(LINE)
        while True:
            if not self.actor:
                self.login_menu()
                if self.actor is None:
                    return
            try:
                role = self.actor["role"]
                if role == Role.GUEST.value:
                    self.guest_menu()
                elif role == Role.FRONT_DESK.value:
                    self.frontdesk_menu()
                elif role == Role.OWNER.value:
                    self.owner_menu()
                else:
                    self.admin_menu()
            except DomainError as exc:
                print(f"[业务错误] {exc}")
            except (EOFError, KeyboardInterrupt):
                print("\n再见")
                return

    def login_menu(self) -> None:
        """Login/register/exit menu."""
        print("\n1 登录  2 注册客人  0 退出")
        choice = ask("请选择", "1")
        if choice == "0":
            self.actor = None
            raise SystemExit(0)
        if choice == "2":
            phone = ask("手机号")
            name = ask("姓名")
            password = ask("密码")
            self.app.auth.register_guest(phone, password, name)
            print("注册成功，请登录")
            return
        phone = ask("手机号")
        password = ask("密码")
        try:
            self.actor = self.app.auth.login(phone, password)
        except DomainError as exc:
            print(f"登录失败：{exc}")

    def header(self, title: str) -> None:
        """Handle the header command."""
        print(f"\n{LINE}\n{title}（{self.actor['name']} / {self.actor['role']}）\n{LINE}")

    # ------------------------------------------------------------------
    # guest
    # ------------------------------------------------------------------
    def guest_menu(self) -> None:
        """Handle the guest menu command."""
        self.header("客人菜单")
        print("1 查询酒店  2 预订  3 我的订单  4 订单详情  5 修改订单")
        print("6 取消订单  7 投诉  0 退出登录")
        choice = ask("请选择")
        if choice == "0":
            self.actor = None
        elif choice == "1":
            self.search()
        elif choice == "2":
            self.book()
        elif choice == "3":
            self.my_orders()
        elif choice == "4":
            self.order_detail()
        elif choice == "5":
            self.modify_order()
        elif choice == "6":
            self.cancel_order()
        elif choice == "7":
            self.complain()

    def search(self) -> None:
        """Handle the search command."""
        city = ask("城市", "上海")
        check_in = ask_date("入住日期", fmt_date(today() + timedelta(days=1)))
        check_out = ask_date("离店日期", fmt_date(today() + timedelta(days=3)))
        guests = ask_int("人数", 2)
        keyword = ask("房型关键字（可空）")
        results = self.app.booking.search(city, check_in, check_out, guests, keyword)
        rows = [
            [
                item["room_type_id"],
                item["hotel_name"],
                item["room_type"],
                f"¥{money(item['nightly_from'])}",
                item["available"],
                f"¥{money(item['total_price'])}",
            ]
            for item in results
        ]
        table(["房型ID", "酒店", "房型", "起价/晚", "剩余", "总价"], rows)

    def book(self) -> None:
        """Handle the book command."""
        room_type_id = ask_int("房型ID")
        check_in = ask_date("入住日期", fmt_date(today() + timedelta(days=1)))
        check_out = ask_date("离店日期", fmt_date(today() + timedelta(days=3)))
        rooms = ask_int("间数", 1)
        name = ask("入住人姓名", self.actor["name"])
        phone = ask("入住人手机号", self.actor["phone"])
        eta = ask("预计到店", "20:00")
        order = self.app.booking.create_order(
            self.actor,
            room_type_id,
            check_in,
            check_out,
            rooms,
            name,
            phone,
            eta,
        )
        print(f"下单成功：{order['order_no']}，状态 {order['status']}")

    def my_orders(self) -> None:
        """Handle the my orders command."""
        rows = [
            [
                item["order_no"],
                item["check_in"],
                item["check_out"],
                item["status"],
                money(self.app.billing.bill(item["id"])["total"]),
            ]
            for item in self.app.booking.my_orders(self.actor)
        ]
        table(["订单号", "入住", "离店", "状态", "应收"], rows)

    def order_detail(self) -> None:
        """Handle the order detail command."""
        order_no = ask("订单号")
        detail = self.app.booking.order_detail(self.actor, order_no)
        print(f"订单 {detail['order_no']} 状态 {detail['status']}")
        print(f"客人 {detail['guest_name']} {detail['guest_phone']}")
        table(
            ["项目", "金额"],
            [
                ["房费", money(detail["bill"]["room_fee"])],
                ["早餐", money(detail["bill"]["breakfast_fee"])],
                ["在店消费", money(detail["bill"]["other_fee"])],
                ["取消应扣", money(detail["bill"]["cancel_fee"])],
                ["应收合计", money(detail["bill"]["total"])],
                ["已收", money(detail["bill"]["paid"])],
                ["未收", money(detail["bill"]["unpaid"])],
            ],
        )

    def modify_order(self) -> None:
        """Handle the modify order command."""
        order_no = ask("订单号")
        check_in = ask_date("新入住日期")
        check_out = ask_date("新离店日期")
        rooms = ask_int("新间数", 1)
        order = self.app.booking.modify_order(self.actor, order_no, check_in, check_out, rooms)
        print(f"改单成功，已修改 {order['modify_count']} 次")

    def cancel_order(self) -> None:
        """Handle the cancel order command."""
        order_no = ask("订单号")
        order = self.app.booking.cancel_order(self.actor, order_no, CancelBy.GUEST.value)
        print(f"已取消，取消应扣 ¥{money(order['cancel_fee'])}")

    def complain(self) -> None:
        """Handle the complain command."""
        order_no = ask("订单号")
        ctype = ask("问题类型", "卫生")
        content = ask("投诉内容")
        complaint_id = self.app.governance.create_complaint(self.actor, order_no, ctype, content)
        print(f"投诉已提交，编号 {complaint_id}")

    # ------------------------------------------------------------------
    # front desk
    # ------------------------------------------------------------------
    def frontdesk_menu(self) -> None:
        """Handle the frontdesk menu command."""
        self.header("前台工作台")
        print("1 房态看板  2 查单  3 办理入住  4 办理退房  5 登记消费")
        print("6 收款  7 退款  8 改房态  9 今日看板  0 退出登录")
        choice = ask("请选择")
        if choice == "0":
            self.actor = None
        elif choice == "1":
            rows = [
                [room["room_no"], room["status"], room["guest"]]
                for room in self.app.frontdesk.room_board(self.actor)
            ]
            table(["房间", "状态", "在住客人"], rows)
        elif choice == "2":
            keyword = ask("订单号/手机号/姓名")
            rows = [
                [
                    item["order_no"],
                    item["guest_name"],
                    item["guest_phone"],
                    item["check_in"],
                    item["status"],
                ]
                for item in self.app.booking.find_orders(self.actor, keyword)
            ]
            table(["订单号", "入住人", "手机", "入住", "状态"], rows)
        elif choice == "3":
            order_no = ask("订单号")
            room_no = ask("房间号")
            self.app.booking.check_in(self.actor, order_no, room_no)
            print("入住办理完成")
        elif choice == "4":
            order_no = ask("订单号")
            self.app.booking.check_out(self.actor, order_no)
            print("退房完成，房间已转待打扫")
        elif choice == "5":
            order_no = ask("订单号")
            product = ask("商品名称")
            qty = ask_int("数量", 1)
            self.app.booking.add_consumption(self.actor, order_no, product, qty)
            print("消费已登记")
        elif choice == "6":
            order_no = ask("订单号")
            method = ask("方式 CASH/QR", "CASH")
            amount = float(ask("金额", "0") or 0)
            bill = self.app.billing.add_payment(self.actor, order_no, method, amount)
            print(f"收款成功，未收 ¥{money(bill['unpaid'])}")
        elif choice == "7":
            consumption_id = ask_int("消费记录ID")
            reason = ask("退款原因")
            self.app.frontdesk.refund_consumption(self.actor, consumption_id, reason)
            print("退款完成")
        elif choice == "8":
            room_no = ask("房间号")
            target = ask("目标状态 FREE/DIRTY/MAINTENANCE", "FREE")
            self.app.frontdesk.change_room_status(self.actor, room_no, target)
            print("房态已更新")
        elif choice == "9":
            data = self.app.reports.dashboard(self.actor["hotel_id"])
            print(
                f"{data['date']} 新订单 {data['new_orders']}，待入住 "
                f"{data['pending_check_in']}，在住 {data['in_house']}"
            )
            table(
                ["房型", "剩余可售"],
                [[item["room_type"], item["left"]] for item in data["remaining"]],
            )

    # ------------------------------------------------------------------
    # owner
    # ------------------------------------------------------------------
    def owner_menu(self) -> None:
        """Handle the owner menu command."""
        self.header("酒店老板菜单")
        print("1 房型  2 新增房型  3 改房价  4 价格规则  5 停售")
        print("6 商品  7 员工  8 营收报表  9 出租率  10 日志  0 退出登录")
        choice = ask("请选择")
        if choice == "0":
            self.actor = None
        elif choice == "1":
            rows = [
                [
                    item["id"],
                    item["name"],
                    item["room_count"],
                    money(item["base_price"]),
                    item["breakfast"],
                ]
                for item in self.app.hotel_admin.room_types(self.actor)
            ]
            table(["ID", "房型", "房间数", "基础价", "含早"], rows)
        elif choice == "2":
            name = ask("房型名称")
            count = ask_int("房间数", 5)
            price = float(ask("基础价", "428") or 428)
            breakfast = ask_int("含早份数", 2)
            type_id = self.app.hotel_admin.add_room_type(
                self.actor, name, breakfast, count, price, "入住前一天 18:00 前免费"
            )
            print(f"已新增房型 {type_id}")
        elif choice == "3":
            type_id = ask_int("房型ID")
            price = float(ask("新基础价", "428") or 428)
            print(self.app.hotel_admin.set_base_price(self.actor, type_id, price))
        elif choice == "4":
            type_id = ask_int("房型ID")
            rule_type = ask("类型 SINGLE/RANGE/WEEKEND", "SINGLE")
            start = ask_date("开始日期")
            end = ask_date("结束日期", start)
            price = float(ask("价格", "488") or 488)
            self.app.hotel_admin.add_price_rule(self.actor, type_id, rule_type, start, end, price)
            print("价格规则已添加")
        elif choice == "5":
            scope = ask("范围 HOTEL/ROOM_TYPE/ROOM", "ROOM_TYPE")
            type_id = ask_int("房型ID（整店可填0）", 0) or None
            room_no = ask("房间号（单间时）") or None
            start = ask_date("开始日期")
            end = ask_date("结束日期", start)
            reason = ask("原因")
            self.app.hotel_admin.stop_sale(self.actor, scope, start, end, reason, type_id, room_no)
            print("停售已生效")
        elif choice == "6":
            rows = [
                [item["id"], item["name"], money(item["price"]), item["stock"]]
                for item in self.app.repo.products(self.actor["hotel_id"])
            ]
            table(["ID", "商品", "单价", "库存"], rows)
        elif choice == "7":
            rows = [
                [item["id"], item["name"], item["phone"], item["role"], item["status"]]
                for item in self.app.hotel_admin.staff(self.actor)
            ]
            table(["ID", "姓名", "手机", "角色", "状态"], rows)
        elif choice == "8":
            month = ask("月份 YYYY-MM", fmt_date(today())[:7])
            data = self.app.reports.revenue(self.actor["hotel_id"], month)
            print(
                f"房费 {money(data['room_fee'])}，早餐 {money(data['breakfast_fee'])}，"
                f"其他 {money(data['other_fee'])}，合计 {money(data['total'])}"
            )
        elif choice == "9":
            month = ask("月份 YYYY-MM", fmt_date(today())[:7])
            rows = [
                [
                    item["room_type"],
                    item["sold_nights"],
                    item["available_nights"],
                    f"{item['occupancy']}%",
                ]
                for item in self.app.reports.occupancy(self.actor["hotel_id"], month)
            ]
            table(["房型", "已售间夜", "可售间夜", "出租率"], rows)
        elif choice == "10":
            rows = [
                [item["created_at"], item["role"], item["action"], item["target"]]
                for item in self.app.governance.logs(self.actor, limit=20)
            ]
            table(["时间", "角色", "操作", "对象"], rows)

    # ------------------------------------------------------------------
    # admin
    # ------------------------------------------------------------------
    def admin_menu(self) -> None:
        """Handle the admin menu command."""
        self.header("平台管理员菜单")
        print("1 待审核酒店  2 审核  3 处罚  4 待处理投诉  5 处理投诉")
        print("6 调价审批  7 审批  8 城市汇总  9 平台概览  10 日志  0 退出登录")
        choice = ask("请选择")
        if choice == "0":
            self.actor = None
        elif choice == "1":
            rows = [
                [item["id"], item["name"], item["city"], item["status"]]
                for item in self.app.hotel_admin.pending_hotels()
            ]
            table(["ID", "酒店", "城市", "状态"], rows)
        elif choice == "2":
            hotel_id = ask_int("酒店ID")
            approve = ask("通过 y/n", "y").lower() == "y"
            reason = ask("原因（退回必填）")
            self.app.hotel_admin.review(self.actor, hotel_id, approve, reason)
            print("审核完成")
        elif choice == "3":
            hotel_id = ask_int("酒店ID")
            status = ask("状态 OFFLINE/BANNED/APPROVED", "OFFLINE")
            reason = ask("原因")
            self.app.hotel_admin.change_status(self.actor, hotel_id, status, reason)
            print("处罚已执行")
        elif choice == "4":
            rows = [
                [item["id"], item["order_id"], item["ctype"], item["status"], item["content"][:20]]
                for item in self.app.governance.complaints(self.actor, status="PENDING")
            ]
            table(["ID", "订单ID", "类型", "状态", "内容"], rows)
        elif choice == "5":
            complaint_id = ask_int("投诉ID")
            status = ask("状态 RESOLVED/REJECTED", "RESOLVED")
            result = ask("处理结果")
            self.app.governance.handle(self.actor, complaint_id, status, result)
            print("投诉已处理")
        elif choice == "6":
            rows = [
                [
                    item["id"],
                    item["room_type_id"],
                    money(item["old_price"]),
                    money(item["new_price"]),
                ]
                for item in self.app.hotel_admin.pending_approvals()
            ]
            table(["ID", "房型ID", "原价", "新价"], rows)
        elif choice == "7":
            approval_id = ask_int("审批ID")
            approve = ask("通过 y/n", "y").lower() == "y"
            self.app.hotel_admin.approve_price(self.actor, approval_id, approve)
            print("审批完成")
        elif choice == "8":
            month = ask("月份 YYYY-MM", fmt_date(today())[:7])
            rows = [
                [item["city"], item["orders"], money(item["room_fee"])]
                for item in self.app.reports.city_summary(month)
            ]
            table(["城市", "订单数", "房费"], rows)
        elif choice == "9":
            data = self.app.reports.admin_overview(self.actor)
            print(
                f"在营酒店 {data['hotels']}，订单 {data['orders']}，"
                f"取消 {data['cancelled']}，待处理投诉 {data['pending_complaints']}"
            )
        elif choice == "10":
            rows = [
                [item["created_at"], item["role"], item["action"], item["target"]]
                for item in self.app.governance.logs(self.actor, limit=20)
            ]
            table(["时间", "角色", "操作", "对象"], rows)


def build_parser() -> argparse.ArgumentParser:
    """Command line options."""
    parser = argparse.ArgumentParser(description="酒店预订系统 CLI")
    parser.add_argument("--db", default=None, help="SQLite 数据库路径")
    parser.add_argument("--demo", action="store_true", help="运行演示流程后退出")
    parser.add_argument("--gui", action="store_true", help="启动 Tkinter 桌面界面")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = build_parser().parse_args(argv)
    app = App(args.db)
    try:
        if args.gui:
            from .gui import HotelGUI
            HotelGUI(app).run()
            return
        if args.demo:

            run_demo(app)
            return
        Cli(app).run()
    except SystemExit:
        pass
    except (EOFError, KeyboardInterrupt):
        print("\n再见")
    finally:
        app.close()


if __name__ == "__main__":
    main(sys.argv[1:])
