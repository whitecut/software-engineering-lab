"""End-to-end demo used for the experiment report run results."""

from __future__ import annotations

from datetime import timedelta

from .app import App
from .domain import CancelBy
from .utils import fmt_date, money, today


def title(text: str) -> None:
    """Print a section title."""
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def run_demo(app: App) -> None:
    """Exercise search, booking, modify, check-in, billing, cancel and reports."""
    guest = app.auth.login("13800000003", "guest123")
    desk = app.auth.login("13800000002", "desk123")
    owner = app.auth.login("13800000001", "owner123")
    admin = app.auth.login("13900000000", "admin123")

    check_in = fmt_date(today() + timedelta(days=1))
    check_out = fmt_date(today() + timedelta(days=3))

    title("1. 客人查询酒店")
    results = app.booking.search("上海", check_in, check_out, guests=1)
    for item in results:
        print(
            f"{item['hotel_name']} / {item['room_type']}：¥{money(item['total_price'])}，"
            f"剩余 {item['available']} 间"
        )
    target = next(item for item in results if item["hotel_name"].startswith("云澜"))
    type_id = target["room_type_id"]
    print(f"选择房型 {type_id}（{target['room_type']}）")

    title("2. 下单与幂等")
    order = app.booking.create_order(
        guest,
        type_id,
        check_in,
        check_out,
        1,
        "张伟",
        "13800000003",
        idempotency_key="demo-idem-1",
    )
    print(
        f"订单号 {order['order_no']}，状态 {order['status']}，"
        f"房费 ¥{money(app.billing.bill(order['id'])['total'])}"
    )
    again = app.booking.create_order(
        guest,
        type_id,
        check_in,
        check_out,
        1,
        "张伟",
        "13800000003",
        idempotency_key="demo-idem-1",
    )
    print(f"重复提交返回同一订单：{again['order_no'] == order['order_no']}")

    title("3. 修改订单（价格快照）")
    new_out = fmt_date(today() + timedelta(days=4))
    modified = app.booking.modify_order(guest, order["order_no"], check_in, new_out, 1)
    print(
        f"改为 {modified['check_in']} ~ {modified['check_out']}，"
        f"修改次数 {modified['modify_count']}"
    )
    detail = app.booking.order_detail(guest, order["order_no"])
    for night in detail["nights"]:
        print(f"  {night['date']} 单价 ¥{money(night['price'])}")

    title("4. 前台办理入住、登记消费、分次收款、退房")
    app.booking.check_in(desk, order["order_no"], "301")
    print("入住完成，房间 301 转为在住")
    app.booking.add_consumption(desk, order["order_no"], "洗衣服务", 1)
    bill = app.billing.add_payment(desk, order["order_no"], "CASH", 500)
    print(f"收款 500，未收 ¥{money(bill['unpaid'])}")
    app.booking.check_out(desk, order["order_no"])
    bill = app.billing.bill(order["id"])
    print(
        f"退房后账单：应收 ¥{money(bill['total'])}，已收 ¥{money(bill['paid'])}，"
        f"未收 ¥{money(bill['unpaid'])}"
    )
    app.billing.add_payment(desk, order["order_no"], "QR", bill["unpaid"])
    print(f"补收后未收 ¥{money(app.billing.bill(order['id'])['unpaid'])}")

    title("5. 取消订单与扣费")
    later_in = fmt_date(today() + timedelta(days=5))
    later_out = fmt_date(today() + timedelta(days=6))
    second = app.booking.create_order(guest, type_id, later_in, later_out, 1, "张伟", "13800000003")
    cancelled = app.booking.cancel_order(guest, second["order_no"], CancelBy.GUEST.value)
    print(f"订单 {cancelled['order_no']} 已取消，取消应扣 ¥{money(cancelled['cancel_fee'])}")

    title("6. 投诉与处理")
    complaint_id = app.governance.create_complaint(
        guest, order["order_no"], "卫生", "卫生间地面有积水"
    )
    print(f"投诉编号 {complaint_id}，状态 PENDING")
    app.governance.handle(admin, complaint_id, "RESOLVED", "已核实并完成整改")
    print("管理员处理完成，状态 RESOLVED")

    title("7. 报表与看板")
    month = fmt_date(today())[:7]
    revenue = app.reports.revenue(owner["hotel_id"], month)
    print(
        f"本月营收：房费 ¥{money(revenue['room_fee'])}，"
        f"早餐 ¥{money(revenue['breakfast_fee'])}，其他 ¥{money(revenue['other_fee'])}，"
        f"合计 ¥{money(revenue['total'])}"
    )
    for row in app.reports.occupancy(owner["hotel_id"], month):
        print(f"  {row['room_type']}：出租率 {row['occupancy']}%")
    overview = app.reports.dashboard(owner["hotel_id"])
    print(
        f"今日看板：新订单 {overview['new_orders']}，待入住 "
        f"{overview['pending_check_in']}，在住 {overview['in_house']}"
    )
    admin_data = app.reports.admin_overview(admin)
    print(
        f"平台概览：在营酒店 {admin_data['hotels']}，订单 {admin_data['orders']}，"
        f"待处理投诉 {admin_data['pending_complaints']}"
    )

    title("8. 审计日志（最近 5 条）")
    for log in app.governance.logs(admin, limit=5):
        print(f"{log['created_at']} {log['role']} {log['action']} {log['target']}")

    print("\n演示结束。演示账号可用 python main.py 进入交互式 CLI。")


if __name__ == "__main__":
    application = App(":memory:")
    run_demo(application)
    application.close()
