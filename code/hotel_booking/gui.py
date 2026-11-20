"""Tkinter desktop interface matching the lab-2 UI design."""

from __future__ import annotations

import tkinter as tk
from datetime import timedelta
from tkinter import messagebox, ttk

from .app import App
from .domain import CancelBy, Role, RoomStatus
from .errors import DomainError
from .utils import fmt_date, money, today

FONT = ("Microsoft YaHei", 10)
FONT_BOLD = ("Microsoft YaHei", 10, "bold")
FONT_TITLE = ("Microsoft YaHei", 17, "bold")
FONT_CARD = ("Microsoft YaHei", 18, "bold")
NAVY = "#6D4C5C"
BLUE = "#F06292"
BG = "#FFF7FA"
WHITE = "#FFFFFF"
GRAY = "#A17888"
LINE = "#F8BBD0"
SIDEBAR = "#FBE4EE"
PINK = "#F06292"
PINK_DEEP = "#D81B60"
PINK_LIGHT = "#FCE4EC"
LAVENDER = "#CE93D8"
MINT = "#80CBC4"


class FormDialog(tk.Toplevel):
    """Small modal form driven by a field specification."""

    def __init__(self, parent, title, fields, on_submit) -> None:
        super().__init__(parent)
        self.title(title)
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_submit = on_submit
        self.vars: dict[str, tk.StringVar] = {}
        body = tk.Frame(self, bg=WHITE, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=title, bg=WHITE, fg=NAVY, font=FONT_BOLD).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        for index, (key, label, default, kind, options) in enumerate(fields, start=1):
            tk.Label(body, text=label, bg=WHITE, fg=GRAY, font=FONT).grid(
                row=index, column=0, sticky="w", pady=4
            )
            var = tk.StringVar(value=str(default))
            self.vars[key] = var
            if kind == "choice":
                widget = ttk.Combobox(
                    body, textvariable=var, values=options, width=26, state="readonly"
                )
            else:
                widget = tk.Entry(body, textvariable=var, width=28, font=FONT, relief="solid", bd=1)
            widget.grid(row=index, column=1, sticky="w", pady=4)
        buttons = tk.Frame(body, bg=WHITE)
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(14, 0), sticky="e")
        tk.Button(
            buttons,
            text="取消",
            command=self.destroy,
            bg=WHITE,
            fg=GRAY,
            relief="solid",
            bd=1,
            padx=14,
        ).pack(side="left", padx=6)
        tk.Button(
            buttons, text="确定", command=self._submit, bg=BLUE, fg=WHITE, relief="flat", padx=18
        ).pack(side="left")
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _submit(self) -> None:
        values = {key: var.get().strip() for key, var in self.vars.items()}
        try:
            self.on_submit(values)
        except DomainError as exc:
            messagebox.showerror("操作失败", str(exc), parent=self)
            return
        except ValueError as exc:
            messagebox.showerror("输入有误", str(exc), parent=self)
            return
        self.destroy()


class HotelGUI(tk.Tk):
    """Desktop application shell with role based navigation."""

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.actor: dict | None = None
        self.section_defs: list[tuple[str, callable]] = []
        self.nav_buttons: list[tk.Button] = []
        self.title("酒店预订系统 · 软件工程实验三")
        self.geometry("1280x820")
        self.minsize(1120, 720)
        self.configure(bg=BG)
        self._style()
        self.show_login()

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            font=FONT,
            rowheight=28,
            background=WHITE,
            fieldbackground=WHITE,
            foreground=NAVY,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            font=FONT_BOLD,
            background=PINK_LIGHT,
            foreground=PINK_DEEP,
            relief="flat",
        )
        style.map("Treeview", background=[("selected", PINK)], foreground=[("selected", WHITE)])
        style.configure("TCombobox", font=FONT, fieldbackground=WHITE)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=FONT, padding=(14, 6))

    # ------------------------------------------------------------------
    # shell and login
    # ------------------------------------------------------------------
    def _clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def show_login(self) -> None:
        """Render the cute login screen."""
        self._clear()
        self.actor = None
        left = tk.Canvas(self, width=440, highlightthickness=0, bg=PINK_LIGHT)
        left.pack(side="left", fill="y")
        self._gradient(left, 440, 900, "#FFD9E6", "#E9D5F5")
        # 一只趴在右上角的小兔子
        left.create_oval(330, 56, 352, 122, fill="#FFF7FA", outline=PINK, width=2)
        left.create_oval(358, 56, 380, 122, fill="#FFF7FA", outline=PINK, width=2)
        left.create_oval(318, 102, 395, 184, fill="#FFF7FA", outline=PINK, width=2)
        left.create_oval(340, 130, 348, 138, fill=NAVY, outline="")
        left.create_oval(365, 130, 373, 138, fill=NAVY, outline="")
        left.create_oval(352, 146, 360, 153, fill=PINK_DEEP, outline="")
        left.create_oval(328, 143, 342, 154, fill="#FFD1DC", outline="")
        left.create_oval(370, 143, 384, 154, fill="#FFD1DC", outline="")
        left.create_text(38, 78, text="❀", font=("Microsoft YaHei", 46), fill=PINK_DEEP, anchor="w")
        left.create_text(
            38, 138, text="酒店云", font=("Microsoft YaHei", 36, "bold"), fill=PINK_DEEP, anchor="w"
        )
        left.create_text(
            40, 196, text="HOTEL CONSOLE", font=("Microsoft YaHei", 10), fill="#B07A8E", anchor="w"
        )
        left.create_text(
            40,
            262,
            text="今天也要元气满满哦～\n查一查、订一订，去想去的地方 ♡",
            font=("Microsoft YaHei", 13),
            fill=NAVY,
            anchor="w",
            justify="left",
        )
        left.create_text(
            40,
            350,
            text="♡    ✿    ♡    ✿    ♡",
            font=("Microsoft YaHei", 18),
            fill="#F48FB1",
            anchor="w",
        )
        left.create_text(
            40,
            760,
            text="酒店预订系统 · 软件工程实验三",
            font=("Microsoft YaHei", 9),
            fill="#B07A8E",
            anchor="w",
        )

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        shadow = tk.Frame(right, bg="#F3D9E4")
        shadow.place(relx=0.5, rely=0.46, anchor="center", width=430, height=446)
        card = tk.Frame(
            right, bg=WHITE, padx=36, pady=28, highlightbackground=LINE, highlightthickness=2
        )
        card.place(relx=0.5, rely=0.455, anchor="center", width=430, height=446)
        tk.Label(card, text="欢迎回来～", bg=WHITE, fg=PINK_DEEP, font=FONT_TITLE).pack(anchor="w")
        tk.Label(card, text="挑一个身份，开始今天的小旅行吧 ♡", bg=WHITE, fg=GRAY, font=FONT).pack(
            anchor="w", pady=(4, 18)
        )
        self.login_phone = tk.StringVar(value="13800000003")
        self.login_password = tk.StringVar(value="guest123")
        tk.Label(card, text="手机号", bg=WHITE, fg=GRAY, font=FONT).pack(anchor="w")
        tk.Entry(card, textvariable=self.login_phone, font=FONT, relief="solid", bd=1).pack(
            fill="x", ipady=6, pady=(2, 10)
        )
        tk.Label(card, text="密码", bg=WHITE, fg=GRAY, font=FONT).pack(anchor="w")
        tk.Entry(
            card, textvariable=self.login_password, show="*", font=FONT, relief="solid", bd=1
        ).pack(fill="x", ipady=6, pady=(2, 14))
        tk.Button(
            card,
            text="登 录",
            bg=PINK,
            fg=WHITE,
            relief="flat",
            activebackground=PINK_DEEP,
            activeforeground=WHITE,
            font=FONT_BOLD,
            cursor="hand2",
            command=self._do_login,
        ).pack(fill="x", ipady=7)
        tk.Button(
            card,
            text="还没有账号？注册一个吧",
            bg=WHITE,
            fg=PINK_DEEP,
            relief="flat",
            font=FONT,
            cursor="hand2",
            command=self._register_dialog,
        ).pack(pady=(10, 0))
        demo = tk.Frame(card, bg=WHITE)
        demo.pack(fill="x", pady=(16, 0))
        for index, (label, phone, password) in enumerate(
            [
                ("客人 ♡", "13800000003", "guest123"),
                ("前台 ✿", "13800000002", "desk123"),
                ("老板 ☆", "13800000001", "owner123"),
                ("管理员 ✦", "13900000000", "admin123"),
            ]
        ):
            tk.Button(
                demo,
                text=label,
                bg="#FFF0F6",
                fg=NAVY,
                relief="flat",
                width=8,
                activebackground=PINK_LIGHT,
                cursor="hand2",
                command=lambda p=phone, w=password: self._demo_login(p, w),
            ).grid(row=0, column=index, padx=2, pady=2)

    @staticmethod
    def _gradient(canvas: tk.Canvas, width: int, height: int, start: str, end: str) -> None:
        """Paint a vertical pastel gradient on a canvas."""
        start_rgb = tuple(int(start[i : i + 2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(end[i : i + 2], 16) for i in (1, 3, 5))
        for y in range(height):
            ratio = y / max(1, height - 1)
            color = "#" + "".join(
                f"{int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * ratio):02x}" for i in range(3)
            )
            canvas.create_line(0, y, width, y, fill=color)

    def _demo_login(self, phone: str, password: str) -> None:
        self.login_phone.set(phone)
        self.login_password.set(password)
        self._do_login()

    def _do_login(self) -> None:
        try:
            actor = self.app.auth.login(
                self.login_phone.get().strip(), self.login_password.get().strip()
            )
        except DomainError as exc:
            messagebox.showerror("登录失败", str(exc), parent=self)
            return
        self.actor = actor
        self._build_shell()

    def _register_dialog(self) -> None:
        fields = [
            ("phone", "手机号", "", "text", []),
            ("name", "姓名", "", "text", []),
            ("password", "密码", "", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.auth.register_guest(values["phone"], values["password"], values["name"])
            messagebox.showinfo("注册成功", "请使用新账号登录", parent=self)
            self.login_phone.set(values["phone"])

        FormDialog(self, "注册客人账号", fields, submit)

    def _build_shell(self) -> None:
        self._clear()
        self.nav_buttons = []
        sidebar = tk.Frame(self, bg=SIDEBAR, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(
            sidebar, text="❀ 酒店云", bg=SIDEBAR, fg=PINK_DEEP, font=("Microsoft YaHei", 20, "bold")
        ).pack(anchor="w", padx=20, pady=(24, 0))
        tk.Label(
            sidebar, text="HOTEL CONSOLE", bg=SIDEBAR, fg="#B07A8E", font=("Microsoft YaHei", 8)
        ).pack(anchor="w", padx=22)
        self.nav_frame = tk.Frame(sidebar, bg=SIDEBAR)
        self.nav_frame.pack(fill="x", padx=10, pady=22)
        tk.Label(
            sidebar,
            text=f"{self.actor['name']} ♡\n{self._role_name()}",
            bg=SIDEBAR,
            fg=NAVY,
            font=FONT,
            justify="left",
        ).pack(side="bottom", anchor="w", padx=20, pady=(0, 10))
        tk.Button(
            sidebar,
            text="退出登录",
            bg=SIDEBAR,
            fg="#B07A8E",
            relief="flat",
            activebackground=PINK_LIGHT,
            activeforeground=PINK_DEEP,
            cursor="hand2",
            command=self.show_login,
        ).pack(side="bottom", anchor="w", padx=16)
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg=WHITE, height=58)
        top.pack(fill="x")
        top.pack_propagate(False)
        self.page_title = tk.Label(top, text="", bg=WHITE, fg=NAVY, font=FONT_BOLD)
        self.page_title.pack(side="left", padx=22)
        tk.Label(
            top, text=f"今天也要开心呀 ♡  {fmt_date(today())}", bg=WHITE, fg=GRAY, font=FONT
        ).pack(side="right", padx=22)
        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=18, pady=16)
        self.section_defs = self._sections()
        for index, (label, _builder) in enumerate(self.section_defs):
            button = tk.Button(
                self.nav_frame,
                text=label,
                bg=SIDEBAR,
                fg=NAVY,
                activebackground=PINK_LIGHT,
                activeforeground=PINK_DEEP,
                relief="flat",
                anchor="w",
                padx=14,
                pady=8,
                cursor="hand2",
                font=FONT,
                command=lambda i=index: self.show_section(i),
            )
            button.pack(fill="x", pady=2)
            self.nav_buttons.append(button)
        self.show_section(0)

    def _role_name(self) -> str:
        names = {
            Role.GUEST.value: "客人",
            Role.FRONT_DESK.value: "酒店前台",
            Role.OWNER.value: "酒店老板",
            Role.ADMIN.value: "平台管理员",
        }
        return names.get(self.actor["role"], "")

    def show_section(self, index: int) -> None:
        """Switch the content area to one navigation section."""
        for child in self.content.winfo_children():
            child.destroy()
        label, builder = self.section_defs[index]
        self.page_title.config(text=label)
        for i, button in enumerate(self.nav_buttons):
            button.configure(
                bg=WHITE if i == index else SIDEBAR,
                fg=PINK_DEEP if i == index else NAVY,
            )
        builder(self.content)

    # ------------------------------------------------------------------
    # shared widgets
    # ------------------------------------------------------------------
    def _section(self, parent, title: str, subtitle: str = "") -> tk.Frame:
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="✿ " + title, bg=BG, fg=PINK_DEEP, font=FONT_TITLE).pack(anchor="w")
        if subtitle:
            tk.Label(frame, text=subtitle, bg=BG, fg=GRAY, font=FONT).pack(anchor="w", pady=(2, 8))
        return frame

    def _card(self, parent, title: str, value: str, color: str = BLUE) -> tk.Frame:
        card = tk.Frame(parent, bg="#FFF0F6", highlightbackground=LINE, highlightthickness=2)
        tk.Label(card, text=title, bg="#FFF0F6", fg="#A17888", font=FONT).pack(
            anchor="w", padx=14, pady=(10, 0)
        )
        tk.Label(card, text=value, bg="#FFF0F6", fg=color, font=FONT_CARD).pack(
            anchor="w", padx=14, pady=(2, 12)
        )
        return card

    def _tree(self, parent, columns, headings, widths, height: int = 12) -> ttk.Treeview:
        holder = tk.Frame(parent, bg=BG)
        holder.pack(fill="both", expand=True, pady=(6, 6))
        tree = ttk.Treeview(holder, columns=columns, show="headings", height=height)
        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="w")
        scroll = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    @staticmethod
    def _fill(tree: ttk.Treeview, rows: list[list[str]]) -> None:
        for item in tree.get_children():
            tree.delete(item)
        tree.tag_configure("odd", background="#FFF0F6")
        for index, row in enumerate(rows):
            tags = ("odd",) if index % 2 else ()
            tree.insert("", "end", iid=str(index), values=row, tags=tags)

    @staticmethod
    def _selected(tree: ttk.Treeview) -> int | None:
        selection = tree.selection()
        return int(selection[0]) if selection else None

    def _button_row(self, parent) -> tk.Frame:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(2, 0))
        return row

    @staticmethod
    def _button(parent, text, command, primary: bool = False) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=BLUE if primary else WHITE,
            fg=WHITE if primary else NAVY,
            relief="flat" if primary else "solid",
            bd=0 if primary else 1,
            font=FONT,
            padx=14,
            pady=5,
        )

    def _guard(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DomainError as exc:
            messagebox.showerror("操作失败", str(exc), parent=self)
        except ValueError as exc:
            messagebox.showerror("输入有误", str(exc), parent=self)
        return None

    # ------------------------------------------------------------------
    # sections by role
    # ------------------------------------------------------------------
    def _sections(self) -> list[tuple[str, callable]]:
        if self.actor["role"] == Role.GUEST.value:
            return [
                ("查询与预订", self._guest_search),
                ("我的订单", self._guest_orders),
                ("我的账单", self._guest_bills),
            ]
        if self.actor["role"] == Role.FRONT_DESK.value:
            return [
                ("接待工作台", self._desk_reception),
                ("房态看板", self._desk_rooms),
                ("消费与收款", self._desk_charge),
            ]
        if self.actor["role"] == Role.OWNER.value:
            return [
                ("房型与房间", self._owner_rooms),
                ("价格与停售", self._owner_pricing),
                ("商品与员工", self._owner_goods),
                ("报表看板", self._owner_reports),
                ("操作日志", self._owner_logs),
            ]
        return [
            ("入驻审核", self._admin_review),
            ("投诉处理", self._admin_complaints),
            ("调价审批", self._admin_prices),
            ("平台概览", self._admin_overview),
        ]

    # ------------------------------------------------------------------
    # guest
    # ------------------------------------------------------------------
    def _guest_search(self, parent) -> None:
        frame = self._section(parent, "查询酒店与预订", "按城市、日期、人数查询可直接下单")
        form = tk.Frame(frame, bg=BG)
        form.pack(fill="x")
        self.city = tk.StringVar(value="上海")
        self.check_in = tk.StringVar(value=fmt_date(today() + timedelta(days=1)))
        self.check_out = tk.StringVar(value=fmt_date(today() + timedelta(days=3)))
        self.guests = tk.StringVar(value="2")
        self.keyword = tk.StringVar()
        specs = [
            ("城市", self.city, 12),
            ("入住", self.check_in, 12),
            ("离店", self.check_out, 12),
            ("人数", self.guests, 6),
            ("房型关键字", self.keyword, 14),
        ]
        for index, (label, var, width) in enumerate(specs):
            tk.Label(form, text=label, bg=BG, fg=GRAY, font=FONT).grid(
                row=0, column=index * 2, padx=(0, 4), sticky="e"
            )
            tk.Entry(form, textvariable=var, width=width, font=FONT, relief="solid", bd=1).grid(
                row=0, column=index * 2 + 1, padx=(0, 10), ipady=3
            )
        self._button(form, "查询", self._search, primary=True).grid(
            row=0, column=len(specs) * 2, padx=4
        )
        self.result_tree = self._tree(
            frame,
            ("id", "hotel", "type", "price", "left", "total"),
            ("房型ID", "酒店", "房型", "起价/晚", "剩余", "总价"),
            (70, 190, 130, 100, 80, 110),
        )
        self._button(self._button_row(frame), "预订选中房型", self._book_dialog, True).pack(
            side="left", padx=4
        )
        self._search()

    def _search(self) -> None:
        results = self._guard(
            self.app.booking.search,
            self.city.get().strip(),
            self.check_in.get().strip(),
            self.check_out.get().strip(),
            int(self.guests.get() or 1),
            self.keyword.get().strip(),
        )
        if results is None:
            return
        self.search_results = results
        self._fill(
            self.result_tree,
            [
                [
                    str(item["room_type_id"]),
                    item["hotel_name"],
                    item["room_type"],
                    money(item["nightly_from"]),
                    str(item["available"]),
                    money(item["total_price"]),
                ]
                for item in results
            ],
        )

    def _book_dialog(self) -> None:
        index = self._selected(self.result_tree)
        if index is None or index >= len(getattr(self, "search_results", [])):
            messagebox.showinfo("提示", "请先查询并选择房型", parent=self)
            return
        item = self.search_results[index]
        fields = [
            ("check_in", "入住日期", item.get("check_in", self.check_in.get()), "text", []),
            ("check_out", "离店日期", self.check_out.get(), "text", []),
            ("rooms", "间数", "1", "text", []),
            ("name", "入住人", self.actor["name"], "text", []),
            ("phone", "手机号", self.actor["phone"], "text", []),
            ("eta", "预计到店", "20:00", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.booking.create_order(
                self.actor,
                item["room_type_id"],
                values["check_in"],
                values["check_out"],
                int(values["rooms"]),
                values["name"],
                values["phone"],
                values["eta"],
            )
            messagebox.showinfo("下单成功", "订单已生成，可在“我的订单”查看", parent=self)
            self.show_section(1)

        FormDialog(self, f"预订 {item['hotel_name']} · {item['room_type']}", fields, submit)

    def _guest_orders(self, parent) -> None:
        frame = self._section(parent, "我的订单", "查看状态、账单，修改或取消订单")
        self.order_tree = self._tree(
            frame,
            ("no", "in", "out", "status", "total"),
            ("订单号", "入住", "离店", "状态", "应收"),
            (190, 100, 100, 90, 100),
        )
        self.order_detail = tk.Text(
            frame, height=7, font=FONT, bg=WHITE, fg=NAVY, relief="solid", bd=1
        )
        self.order_detail.pack(fill="x", pady=(4, 6))
        row = self._button_row(frame)
        self._button(row, "刷新", self._load_orders).pack(side="left", padx=4)
        self._button(row, "查看账单", self._view_order, True).pack(side="left", padx=4)
        self._button(row, "修改订单", self._modify_order).pack(side="left", padx=4)
        self._button(row, "取消订单", self._cancel_order).pack(side="left", padx=4)
        self._button(row, "提交投诉", self._complain).pack(side="left", padx=4)
        self._load_orders()

    def _load_orders(self) -> None:
        orders = self._guard(self.app.booking.my_orders, self.actor) or []
        self.guest_orders_list = orders
        rows = []
        for order in orders:
            bill = self.app.billing.bill(order["id"])
            rows.append(
                [
                    order["order_no"],
                    order["check_in"],
                    order["check_out"],
                    order["status"],
                    money(bill["total"]),
                ]
            )
        self._fill(self.order_tree, rows)
        self.order_detail.delete("1.0", "end")

    def _selected_order(self):
        index = self._selected(self.order_tree)
        if index is None or index >= len(getattr(self, "guest_orders_list", [])):
            messagebox.showinfo("提示", "请先选择订单", parent=self)
            return None
        return self.guest_orders_list[index]

    def _view_order(self) -> None:
        order = self._selected_order()
        if not order:
            return
        detail = self._guard(self.app.booking.order_detail, self.actor, order["order_no"])
        if not detail:
            return
        bill = detail["bill"]
        text = (
            f"订单 {detail['order_no']}  状态 {detail['status']}\n"
            f"入住人 {detail['guest_name']} {detail['guest_phone']}\n"
            f"房费 {money(bill['room_fee'])}  早餐 {money(bill['breakfast_fee'])}  "
            f"在店 {money(bill['other_fee'])}  取消应扣 {money(bill['cancel_fee'])}\n"
            f"应收 {money(bill['total'])}  已收 {money(bill['paid'])}  "
            f"未收 {money(bill['unpaid'])}"
        )
        self.order_detail.delete("1.0", "end")
        self.order_detail.insert("1.0", text)

    def _modify_order(self) -> None:
        order = self._selected_order()
        if not order:
            return
        fields = [
            ("check_in", "新入住日期", order["check_in"], "text", []),
            ("check_out", "新离店日期", order["check_out"], "text", []),
            ("rooms", "间数", str(order["rooms"]), "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.booking.modify_order(
                self.actor,
                order["order_no"],
                values["check_in"],
                values["check_out"],
                int(values["rooms"]),
            )
            messagebox.showinfo("修改成功", "订单已更新", parent=self)
            self._load_orders()

        FormDialog(self, "修改订单", fields, submit)

    def _cancel_order(self) -> None:
        order = self._selected_order()
        if not order:
            return
        if not messagebox.askyesno("确认", "确定取消该订单吗？", parent=self):
            return
        self._guard(
            self.app.booking.cancel_order, self.actor, order["order_no"], CancelBy.GUEST.value
        )
        self._load_orders()

    def _complain(self) -> None:
        order = self._selected_order()
        if not order:
            return
        fields = [
            (
                "type",
                "问题类型",
                "卫生",
                "choice",
                ["卫生", "服务态度", "设施故障", "收费问题", "其他"],
            ),
            ("content", "投诉内容", "", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.governance.create_complaint(
                self.actor, order["order_no"], values["type"], values["content"]
            )
            messagebox.showinfo("提交成功", "投诉已提交", parent=self)

        FormDialog(self, "提交投诉", fields, submit)

    def _guest_bills(self, parent) -> None:
        frame = self._section(parent, "我的账单", "选择订单查看明细，账单由酒店线下收款")
        self.bill_tree = self._tree(
            frame,
            ("no", "room", "breakfast", "other", "total", "paid", "unpaid"),
            ("订单号", "房费", "早餐", "在店", "应收", "已收", "未收"),
            (190, 90, 80, 80, 90, 90, 90),
        )
        row = self._button_row(frame)
        self._button(row, "刷新", self._load_bills, True).pack(side="left", padx=4)
        self._load_bills()

    def _load_bills(self) -> None:
        orders = self._guard(self.app.booking.my_orders, self.actor) or []
        rows = []
        for order in orders:
            bill = self.app.billing.bill(order["id"])
            rows.append(
                [
                    order["order_no"],
                    money(bill["room_fee"]),
                    money(bill["breakfast_fee"]),
                    money(bill["other_fee"]),
                    money(bill["total"]),
                    money(bill["paid"]),
                    money(bill["unpaid"]),
                ]
            )
        self._fill(self.bill_tree, rows)

    # ------------------------------------------------------------------
    # front desk
    # ------------------------------------------------------------------
    def _desk_reception(self, parent) -> None:
        frame = self._section(parent, "接待工作台", "查单、分房、办理入住与退房")
        data = self._guard(self.app.reports.dashboard, self.actor["hotel_id"]) or {}
        cards = tk.Frame(frame, bg=BG)
        cards.pack(fill="x", pady=(0, 8))
        values = [
            ("今日新订单", str(data.get("new_orders", 0)), BLUE),
            ("今日待入住", str(data.get("pending_check_in", 0)), "#A16207"),
            ("今日在住", str(data.get("in_house", 0)), "#12805C"),
        ]
        for index, (label, value, color) in enumerate(values):
            card = self._card(cards, label, value, color)
            card.grid(row=0, column=index, sticky="we", padx=(0, 8))
        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)
        cards.grid_columnconfigure(2, weight=1)

        form = tk.Frame(frame, bg=BG)
        form.pack(fill="x", pady=(0, 4))
        self.desk_keyword = tk.StringVar()
        tk.Label(form, text="订单号 / 手机号 / 姓名", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        tk.Entry(
            form, textvariable=self.desk_keyword, width=32, font=FONT, relief="solid", bd=1
        ).pack(side="left", padx=8, ipady=3)
        self._button(form, "查询", self._desk_load, True).pack(side="left", padx=4)
        self.desk_tree = self._tree(
            frame,
            ("no", "name", "phone", "in", "out", "status"),
            ("订单号", "入住人", "手机", "入住", "离店", "状态"),
            (190, 90, 130, 100, 100, 90),
        )
        row = self._button_row(frame)
        self._button(row, "办理入住", self._desk_check_in, True).pack(side="left", padx=4)
        self._button(row, "办理退房", self._desk_check_out).pack(side="left", padx=4)
        self._button(row, "标记未到店", self._desk_no_show).pack(side="left", padx=4)
        self._button(row, "刷新", self._desk_load).pack(side="left", padx=4)
        self._desk_load()

    def _desk_load(self) -> None:
        keyword = self.desk_keyword.get().strip()
        if keyword:
            orders = self._guard(self.app.booking.find_orders, self.actor, keyword) or []
        else:
            orders = self._guard(self.app.booking.hotel_orders, self.actor) or []
        self.desk_orders = orders
        self._fill(
            self.desk_tree,
            [
                [
                    item["order_no"],
                    item["guest_name"],
                    item["guest_phone"],
                    item["check_in"],
                    item["check_out"],
                    item["status"],
                ]
                for item in orders
            ],
        )

    def _desk_selected(self):
        index = self._selected(self.desk_tree)
        if index is None or index >= len(getattr(self, "desk_orders", [])):
            messagebox.showinfo("提示", "请先选择订单", parent=self)
            return None
        return self.desk_orders[index]

    def _desk_check_in(self) -> None:
        order = self._desk_selected()
        if not order:
            return
        rooms = self.app.repo.rooms(self.actor["hotel_id"], order["room_type_id"])
        free = [
            room["room_no"]
            for room in rooms
            if room["status"] in (RoomStatus.FREE.value, RoomStatus.RESERVED.value)
        ]
        if not free:
            messagebox.showinfo("提示", "该房型暂无可分配空房", parent=self)
            return

        def submit(values: dict) -> None:
            self.app.booking.check_in(self.actor, order["order_no"], values["room_no"])
            messagebox.showinfo("入住完成", f"已分配到 {values['room_no']}", parent=self)
            self._desk_load()

        FormDialog(
            self,
            f"办理入住 · {order['order_no']}",
            [("room_no", "房间号", free[0], "choice", free)],
            submit,
        )

    def _desk_check_out(self) -> None:
        order = self._desk_selected()
        if not order:
            return
        if not messagebox.askyesno("确认", "办理退房后房间转为待打扫，是否继续？", parent=self):
            return
        self._guard(self.app.booking.check_out, self.actor, order["order_no"])
        self._desk_load()

    def _desk_no_show(self) -> None:
        order = self._desk_selected()
        if not order:
            return
        if not messagebox.askyesno("确认", "将该订单标记为未到店？", parent=self):
            return
        self._guard(self.app.booking.mark_no_show, self.actor, order["order_no"])
        self._desk_load()

    def _desk_rooms(self, parent) -> None:
        frame = self._section(parent, "房态看板", "空房、已预订、在住、待打扫、维修中")
        self.room_tree = self._tree(
            frame,
            ("no", "type", "status", "guest", "order"),
            ("房间", "房型", "状态", "在住客人", "订单"),
            (80, 140, 100, 100, 190),
        )
        row = self._button_row(frame)
        self._button(row, "刷新", self._load_rooms, True).pack(side="left", padx=4)
        self._button(row, "修改房态", self._room_status_dialog).pack(side="left", padx=4)
        self._load_rooms()

    def _load_rooms(self) -> None:
        board = self._guard(self.app.frontdesk.room_board, self.actor) or []
        types = {item["id"]: item["name"] for item in self.app.hotel_admin.room_types(self.actor)}
        self.rooms = board
        self._fill(
            self.room_tree,
            [
                [
                    room["room_no"],
                    types.get(room["room_type_id"], ""),
                    room["status"],
                    room["guest"],
                    room["order_no"],
                ]
                for room in board
            ],
        )

    def _room_status_dialog(self) -> None:
        index = self._selected(self.room_tree)
        if index is None or index >= len(getattr(self, "rooms", [])):
            messagebox.showinfo("提示", "请先选择房间", parent=self)
            return
        room = self.rooms[index]
        fields = [
            ("status", "目标状态", "FREE", "choice", ["FREE", "DIRTY", "MAINTENANCE"]),
            ("reason", "原因（维修必填）", "", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.frontdesk.change_room_status(
                self.actor, room["room_no"], values["status"], values["reason"]
            )
            messagebox.showinfo("成功", "房态已更新", parent=self)
            self._load_rooms()

        FormDialog(self, f"修改房态 · {room['room_no']}", fields, submit)

    def _desk_charge(self, parent) -> None:
        frame = self._section(parent, "消费与收款", "登记在店消费，按次记录现金/扫码收款")
        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x", pady=(0, 6))
        self.charge_order = tk.StringVar()
        tk.Label(top, text="订单号", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        tk.Entry(
            top, textvariable=self.charge_order, width=24, font=FONT, relief="solid", bd=1
        ).pack(side="left", padx=8, ipady=3)
        self._button(top, "载入", self._load_charge, True).pack(side="left")
        self.charge_info = tk.Label(frame, text="", bg=BG, fg=NAVY, font=FONT, justify="left")
        self.charge_info.pack(anchor="w", pady=(0, 4))
        self.charge_tree = self._tree(
            frame,
            ("name", "qty", "price", "amount", "status"),
            ("商品", "数量", "单价", "金额", "状态"),
            (150, 70, 90, 90, 90),
            height=7,
        )
        form = tk.Frame(frame, bg=BG)
        form.pack(fill="x", pady=(0, 4))
        self.product_var = tk.StringVar()
        self.qty_var = tk.StringVar(value="1")
        products = self._guard(self.app.repo.products, self.actor["hotel_id"]) or []
        names = [item["name"] for item in products]
        tk.Label(form, text="商品", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        ttk.Combobox(
            form, textvariable=self.product_var, values=names, width=14, state="readonly"
        ).pack(side="left", padx=6)
        tk.Label(form, text="数量", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        tk.Entry(form, textvariable=self.qty_var, width=5, font=FONT, relief="solid", bd=1).pack(
            side="left", padx=6
        )
        self._button(form, "登记消费", self._add_charge).pack(side="left", padx=4)
        pay = tk.Frame(frame, bg=BG)
        pay.pack(fill="x")
        self.pay_method = tk.StringVar(value="CASH")
        self.pay_amount = tk.StringVar()
        tk.Label(pay, text="收款方式", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        ttk.Combobox(
            pay, textvariable=self.pay_method, values=["CASH", "QR"], width=8, state="readonly"
        ).pack(side="left", padx=6)
        tk.Label(pay, text="金额", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        tk.Entry(pay, textvariable=self.pay_amount, width=10, font=FONT, relief="solid", bd=1).pack(
            side="left", padx=6
        )
        self._button(pay, "确认收款", self._add_payment, True).pack(side="left", padx=4)

    def _load_charge(self) -> None:
        order = self._guard(self.app.repo.order, self.charge_order.get().strip())
        if not order:
            return
        self.charge_order_id = order["id"]
        bill = self.app.billing.bill(order["id"])
        self.charge_info.config(
            text=f"订单 {order['order_no']}  状态 {order['status']}  "
            f"应收 {money(bill['total'])}  已收 {money(bill['paid'])}  "
            f"未收 {money(bill['unpaid'])}"
        )
        items = self.app.repo.consumptions(order["id"])
        self._fill(
            self.charge_tree,
            [
                [
                    item["name"],
                    item["qty"],
                    money(item["unit_price"]),
                    money(item["amount"]),
                    item["status"],
                ]
                for item in items
            ],
        )

    def _add_charge(self) -> None:
        order = self._guard(self.app.repo.order, self.charge_order.get().strip())
        if not order:
            messagebox.showinfo("提示", "请先载入订单", parent=self)
            return
        name = self.product_var.get()
        if not name:
            messagebox.showinfo("提示", "请选择商品", parent=self)
            return
        self._guard(
            self.app.booking.add_consumption,
            self.actor,
            order["order_no"],
            name,
            int(self.qty_var.get() or 1),
        )
        self._load_charge()

    def _add_payment(self) -> None:
        order = self._guard(self.app.repo.order, self.charge_order.get().strip())
        if not order:
            messagebox.showinfo("提示", "请先载入订单", parent=self)
            return
        self._guard(
            self.app.billing.add_payment,
            self.actor,
            order["order_no"],
            self.pay_method.get(),
            float(self.pay_amount.get() or 0),
        )
        self._load_charge()

    # ------------------------------------------------------------------
    # owner
    # ------------------------------------------------------------------
    def _owner_rooms(self, parent) -> None:
        frame = self._section(parent, "房型与房间", "维护房型、含早份数、基础价与房间号")
        self.type_tree = self._tree(
            frame,
            ("id", "name", "count", "price", "breakfast"),
            ("ID", "房型", "房间数", "基础价", "含早"),
            (60, 200, 90, 100, 80),
        )
        row = self._button_row(frame)
        self._button(row, "刷新", self._load_types, True).pack(side="left", padx=4)
        self._button(row, "新增房型", self._add_type).pack(side="left", padx=4)
        self._button(row, "改基础价", self._change_price).pack(side="left", padx=4)
        self._button(row, "查看房间", self._show_rooms).pack(side="left", padx=4)
        self._load_types()

    def _load_types(self) -> None:
        types = self._guard(self.app.hotel_admin.room_types, self.actor) or []
        self.types = types
        self._fill(
            self.type_tree,
            [
                [
                    item["id"],
                    item["name"],
                    item["room_count"],
                    money(item["base_price"]),
                    item["breakfast"],
                ]
                for item in types
            ],
        )

    def _add_type(self) -> None:
        fields = [
            ("name", "房型名称", "新房间", "text", []),
            ("count", "房间数", "5", "text", []),
            ("price", "基础价", "428", "text", []),
            ("breakfast", "含早份数", "2", "text", []),
            ("cancel", "取消规则", "入住前一天 18:00 前免费", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.hotel_admin.add_room_type(
                self.actor,
                values["name"],
                int(values["breakfast"]),
                int(values["count"]),
                float(values["price"]),
                values["cancel"],
            )
            messagebox.showinfo("成功", "房型已新增", parent=self)
            self._load_types()

        FormDialog(self, "新增房型", fields, submit)

    def _change_price(self) -> None:
        index = self._selected(self.type_tree)
        if index is None or index >= len(getattr(self, "types", [])):
            messagebox.showinfo("提示", "请先选择房型", parent=self)
            return
        room_type = self.types[index]
        fields = [("price", "新基础价", str(room_type["base_price"]), "text", [])]

        def submit(values: dict) -> None:
            message = self.app.hotel_admin.set_base_price(
                self.actor, room_type["id"], float(values["price"])
            )
            messagebox.showinfo("提示", message, parent=self)
            self._load_types()

        FormDialog(self, f"修改基础价 · {room_type['name']}", fields, submit)

    def _show_rooms(self) -> None:
        index = self._selected(self.type_tree)
        if index is None or index >= len(getattr(self, "types", [])):
            messagebox.showinfo("提示", "请先选择房型", parent=self)
            return
        room_type = self.types[index]
        rooms = self.app.repo.rooms(self.actor["hotel_id"], room_type["id"])
        text = "、".join(f"{room['room_no']}({room['status']})" for room in rooms)
        messagebox.showinfo(room_type["name"], text or "暂无房间", parent=self)

    def _owner_pricing(self, parent) -> None:
        frame = self._section(parent, "价格与停售", "周末价/区间价/单日价，停售立即生效")
        types = self._guard(self.app.hotel_admin.room_types, self.actor) or []
        self.price_type = tk.StringVar(value=types[0]["name"] if types else "")
        self.price_types = {item["name"]: item for item in types}
        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="房型", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        combo = ttk.Combobox(
            top,
            textvariable=self.price_type,
            values=list(self.price_types),
            width=18,
            state="readonly",
        )
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._load_rules())
        self._button(top, "添加价格规则", self._add_rule).pack(side="left", padx=4)
        self._button(top, "设置停售", self._stop_sale).pack(side="left", padx=4)
        self.rule_tree = self._tree(
            frame,
            ("id", "type", "start", "end", "price"),
            ("ID", "类型", "开始", "结束", "价格"),
            (60, 110, 110, 110, 90),
        )
        self._load_rules()

    def _load_rules(self) -> None:
        item = self.price_types.get(self.price_type.get())
        rules = self.app.repo.price_rules(item["id"]) if item else []
        self._fill(
            self.rule_tree,
            [
                [
                    rule["id"],
                    rule["rule_type"],
                    rule["start_date"],
                    rule["end_date"],
                    money(rule["price"]),
                ]
                for rule in rules
            ],
        )

    def _add_rule(self) -> None:
        item = self.price_types.get(self.price_type.get())
        if not item:
            messagebox.showinfo("提示", "请先选择房型", parent=self)
            return
        fields = [
            ("type", "类型", "SINGLE", "choice", ["SINGLE", "RANGE", "WEEKEND"]),
            ("start", "开始日期", fmt_date(today() + timedelta(days=3)), "text", []),
            ("end", "结束日期", fmt_date(today() + timedelta(days=3)), "text", []),
            ("price", "价格", "488", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.hotel_admin.add_price_rule(
                self.actor,
                item["id"],
                values["type"],
                values["start"],
                values["end"],
                float(values["price"]),
            )
            messagebox.showinfo("成功", "价格规则已添加", parent=self)
            self._load_rules()

        FormDialog(self, "添加价格规则", fields, submit)

    def _stop_sale(self) -> None:
        item = self.price_types.get(self.price_type.get())
        if not item:
            messagebox.showinfo("提示", "请先选择房型", parent=self)
            return
        fields = [
            ("scope", "范围", "ROOM_TYPE", "choice", ["HOTEL", "ROOM_TYPE", "ROOM"]),
            ("room", "房间号（单间时）", "", "text", []),
            ("start", "开始日期", fmt_date(today() + timedelta(days=3)), "text", []),
            ("end", "结束日期", fmt_date(today() + timedelta(days=3)), "text", []),
            ("reason", "原因", "维修", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.hotel_admin.stop_sale(
                self.actor,
                values["scope"],
                values["start"],
                values["end"],
                values["reason"],
                item["id"],
                values["room"] or None,
            )
            messagebox.showinfo("成功", "停售已生效", parent=self)

        FormDialog(self, "设置停售", fields, submit)

    def _owner_goods(self, parent) -> None:
        frame = self._section(parent, "商品与员工", "附加商品与前台子账号")
        product_box = tk.LabelFrame(frame, text="附加商品", bg=BG, fg=NAVY, font=FONT_BOLD)
        product_box.pack(fill="both", expand=True, pady=(0, 8))
        self.product_tree = self._tree(
            product_box,
            ("id", "name", "price", "stock"),
            ("ID", "商品", "单价", "库存"),
            (60, 160, 100, 80),
            height=5,
        )
        row = self._button_row(product_box)
        self._button(row, "刷新商品", self._load_products, True).pack(side="left", padx=4)
        self._button(row, "新增商品", self._add_product).pack(side="left", padx=4)
        staff_box = tk.LabelFrame(frame, text="员工账号", bg=BG, fg=NAVY, font=FONT_BOLD)
        staff_box.pack(fill="both", expand=True)
        self.staff_tree = self._tree(
            staff_box,
            ("id", "name", "phone", "role", "status"),
            ("ID", "姓名", "手机", "角色", "状态"),
            (60, 110, 130, 100, 80),
            height=5,
        )
        row = self._button_row(staff_box)
        self._button(row, "刷新员工", self._load_staff, True).pack(side="left", padx=4)
        self._button(row, "新增前台", self._add_staff).pack(side="left", padx=4)
        self._button(row, "停用选中", self._disable_staff).pack(side="left", padx=4)
        self._load_products()
        self._load_staff()

    def _load_products(self) -> None:
        products = self._guard(self.app.repo.products, self.actor["hotel_id"]) or []
        self._fill(
            self.product_tree,
            [[item["id"], item["name"], money(item["price"]), item["stock"]] for item in products],
        )

    def _add_product(self) -> None:
        fields = [
            ("name", "商品名称", "", "text", []),
            ("price", "单价", "38", "text", []),
            ("stock", "库存", "100", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.hotel_admin.add_product(
                self.actor, values["name"], float(values["price"]), int(values["stock"])
            )
            messagebox.showinfo("成功", "商品已新增", parent=self)
            self._load_products()

        FormDialog(self, "新增商品", fields, submit)

    def _load_staff(self) -> None:
        staff = self._guard(self.app.hotel_admin.staff, self.actor) or []
        self.staff = staff
        self._fill(
            self.staff_tree,
            [
                [item["id"], item["name"], item["phone"], item["role"], item["status"]]
                for item in staff
            ],
        )

    def _add_staff(self) -> None:
        fields = [
            ("phone", "手机号", "", "text", []),
            ("name", "姓名", "", "text", []),
            ("password", "初始密码", "staff123", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.hotel_admin.add_staff(
                self.actor, values["phone"], values["name"], values["password"]
            )
            messagebox.showinfo("成功", "前台子账号已创建", parent=self)
            self._load_staff()

        FormDialog(self, "新增前台子账号", fields, submit)

    def _disable_staff(self) -> None:
        index = self._selected(self.staff_tree)
        if index is None or index >= len(getattr(self, "staff", [])):
            messagebox.showinfo("提示", "请先选择员工", parent=self)
            return
        account = self.staff[index]
        if not messagebox.askyesno("确认", f"停用 {account['name']}？", parent=self):
            return
        self._guard(self.app.hotel_admin.disable_staff, self.actor, account["id"])
        self._load_staff()

    def _owner_reports(self, parent) -> None:
        frame = self._section(parent, "报表看板", "营收、出租率、消费明细与间夜快照")
        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x")
        self.report_month = tk.StringVar(value=fmt_date(today())[:7])
        tk.Label(top, text="月份", bg=BG, fg=GRAY, font=FONT).pack(side="left")
        tk.Entry(
            top, textvariable=self.report_month, width=10, font=FONT, relief="solid", bd=1
        ).pack(side="left", padx=8, ipady=3)
        self._button(top, "营收", self._show_revenue, True).pack(side="left", padx=4)
        self._button(top, "出租率", self._show_occupancy).pack(side="left", padx=4)
        self._button(top, "保存快照", self._snapshot).pack(side="left", padx=4)
        self.report_text = tk.Text(
            frame, height=22, font=FONT, bg=WHITE, fg=NAVY, relief="solid", bd=1
        )
        self.report_text.pack(fill="both", expand=True, pady=(8, 0))
        self._show_revenue()

    def _show_revenue(self) -> None:
        data = self._guard(
            self.app.reports.revenue, self.actor["hotel_id"], self.report_month.get().strip()
        )
        if not data:
            return
        self.report_text.delete("1.0", "end")
        self.report_text.insert(
            "1.0",
            f"{data['month']} 营收\n"
            f"房费：{money(data['room_fee'])}\n"
            f"早餐：{money(data['breakfast_fee'])}\n"
            f"在店消费：{money(data['other_fee'])}\n"
            f"合计：{money(data['total'])}",
        )

    def _show_occupancy(self) -> None:
        rows = (
            self._guard(
                self.app.reports.occupancy, self.actor["hotel_id"], self.report_month.get().strip()
            )
            or []
        )
        self.report_text.delete("1.0", "end")
        for row in rows:
            self.report_text.insert(
                "end",
                f"{row['room_type']}：已售 {row['sold_nights']} 间夜 / "
                f"可售 {row['available_nights']}，出租率 "
                f"{row['occupancy']}%\n",
            )

    def _snapshot(self) -> None:
        count = self._guard(self.app.reports.snapshot)
        messagebox.showinfo("快照", f"已保存 {count} 条间夜快照", parent=self)

    def _owner_logs(self, parent) -> None:
        frame = self._section(parent, "操作日志", "只增不改，保留 3 年")
        self.log_tree = self._tree(
            frame,
            ("time", "role", "action", "target"),
            ("时间", "角色", "操作", "对象"),
            (150, 90, 130, 240),
            height=16,
        )
        self._button(self._button_row(frame), "刷新", self._load_logs, True).pack(
            side="left", padx=4
        )
        self._load_logs()

    def _load_logs(self) -> None:
        logs = self._guard(self.app.governance.logs, self.actor, None, 100) or []
        self._fill(
            self.log_tree,
            [[item["created_at"], item["role"], item["action"], item["target"]] for item in logs],
        )

    # ------------------------------------------------------------------
    # admin
    # ------------------------------------------------------------------
    def _admin_review(self, parent) -> None:
        frame = self._section(parent, "入驻审核", "3 个工作日内完成，退回必须填写原因")
        self.pending_tree = self._tree(
            frame,
            ("id", "name", "city", "owner", "status"),
            ("ID", "酒店", "城市", "负责人", "状态"),
            (60, 190, 90, 90, 90),
        )
        row = self._button_row(frame)
        self._button(row, "刷新", self._load_pending, True).pack(side="left", padx=4)
        self._button(row, "审核通过", lambda: self._review(True)).pack(side="left", padx=4)
        self._button(row, "退回修改", lambda: self._review(False)).pack(side="left", padx=4)
        self._load_pending()

    def _load_pending(self) -> None:
        hotels = self._guard(self.app.hotel_admin.pending_hotels) or []
        self.pending = hotels
        self._fill(
            self.pending_tree,
            [
                [item["id"], item["name"], item["city"], item["owner_name"], item["status"]]
                for item in hotels
            ],
        )

    def _review(self, approve: bool) -> None:
        index = self._selected(self.pending_tree)
        if index is None or index >= len(getattr(self, "pending", [])):
            messagebox.showinfo("提示", "请先选择酒店", parent=self)
            return
        hotel = self.pending[index]
        fields = [("reason", "原因（退回必填）", "", "text", [])]

        def submit(values: dict) -> None:
            self.app.hotel_admin.review(self.actor, hotel["id"], approve, values["reason"])
            messagebox.showinfo("完成", "审核完成", parent=self)
            self._load_pending()

        FormDialog(self, f"{'通过' if approve else '退回'} · {hotel['name']}", fields, submit)

    def _admin_complaints(self, parent) -> None:
        frame = self._section(parent, "投诉处理", "待处理、处理中、已处理、已驳回")
        self.complaint_tree = self._tree(
            frame,
            ("id", "order", "type", "status", "content"),
            ("ID", "订单ID", "类型", "状态", "内容"),
            (60, 80, 100, 90, 280),
        )
        row = self._button_row(frame)
        self._button(row, "刷新", self._load_complaints, True).pack(side="left", padx=4)
        self._button(row, "处理投诉", self._handle_complaint).pack(side="left", padx=4)
        self._load_complaints()

    def _load_complaints(self) -> None:
        items = self._guard(self.app.governance.complaints, self.actor) or []
        self.complaints = items
        self._fill(
            self.complaint_tree,
            [
                [item["id"], item["order_id"], item["ctype"], item["status"], item["content"][:30]]
                for item in items
            ],
        )

    def _handle_complaint(self) -> None:
        index = self._selected(self.complaint_tree)
        if index is None or index >= len(getattr(self, "complaints", [])):
            messagebox.showinfo("提示", "请先选择投诉", parent=self)
            return
        complaint = self.complaints[index]
        fields = [
            ("status", "处理状态", "RESOLVED", "choice", ["PROCESSING", "RESOLVED", "REJECTED"]),
            ("result", "处理结果", "", "text", []),
        ]

        def submit(values: dict) -> None:
            self.app.governance.handle(
                self.actor, complaint["id"], values["status"], values["result"]
            )
            messagebox.showinfo("完成", "投诉已处理", parent=self)
            self._load_complaints()

        FormDialog(self, f"处理投诉 {complaint['id']}", fields, submit)

    def _admin_prices(self, parent) -> None:
        frame = self._section(parent, "调价审批", "超过原价 5 倍的调价，7 天未审批自动失效")
        self.approval_tree = self._tree(
            frame,
            ("id", "type", "old", "new"),
            ("ID", "房型ID", "原价", "新价"),
            (60, 90, 100, 100),
        )
        row = self._button_row(frame)
        self._button(row, "刷新", self._load_approvals, True).pack(side="left", padx=4)
        self._button(row, "通过", lambda: self._approve(True)).pack(side="left", padx=4)
        self._button(row, "驳回", lambda: self._approve(False)).pack(side="left", padx=4)
        self._load_approvals()

    def _load_approvals(self) -> None:
        approvals = self._guard(self.app.hotel_admin.pending_approvals) or []
        self.approvals = approvals
        self._fill(
            self.approval_tree,
            [
                [
                    item["id"],
                    item["room_type_id"],
                    money(item["old_price"]),
                    money(item["new_price"]),
                ]
                for item in approvals
            ],
        )

    def _approve(self, approve: bool) -> None:
        index = self._selected(self.approval_tree)
        if index is None or index >= len(getattr(self, "approvals", [])):
            messagebox.showinfo("提示", "请先选择审批", parent=self)
            return
        approval = self.approvals[index]
        self._guard(self.app.hotel_admin.approve_price, self.actor, approval["id"], approve)
        self._load_approvals()

    def _admin_overview(self, parent) -> None:
        frame = self._section(parent, "平台概览", "全平台酒店、订单、投诉与最新日志")
        data = self._guard(self.app.reports.admin_overview, self.actor) or {}
        cards = tk.Frame(frame, bg=BG)
        cards.pack(fill="x", pady=(0, 8))
        values = [
            ("在营酒店", str(data.get("hotels", 0))),
            ("订单总数", str(data.get("orders", 0))),
            ("取消订单", str(data.get("cancelled", 0))),
            ("待处理投诉", str(data.get("pending_complaints", 0))),
        ]
        for index, (label, value) in enumerate(values):
            card = self._card(cards, label, value)
            card.grid(row=0, column=index, sticky="we", padx=(0, 8))
            cards.grid_columnconfigure(index, weight=1)
        self.admin_log_tree = self._tree(
            frame,
            ("time", "role", "action", "target"),
            ("时间", "角色", "操作", "对象"),
            (150, 90, 140, 240),
            height=12,
        )
        logs = self._guard(self.app.governance.logs, self.actor, None, 50) or []
        self._fill(
            self.admin_log_tree,
            [[item["created_at"], item["role"], item["action"], item["target"]] for item in logs],
        )

    def run(self) -> None:
        """Start the Tk event loop."""
        self.mainloop()
