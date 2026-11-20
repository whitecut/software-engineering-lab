# 实验三：酒店预订系统（Python + SQLite 原型）

软件工程实验三的实现部分。按照实验二的 UML 设计，用 Python 3.12 标准库实现了酒店预订的主要业务，
提供 Tkinter 桌面界面（`--gui`）与命令行界面（CLI），SQLite 持久化，配套 25 个单元测试。

## 直接打开（推荐）

不需要命令行：

- 双击项目根目录的 `启动界面.cmd`；
- 或双击 `启动界面.vbs`（不显示黑色控制台窗口）；
- 或直接双击 `code\dist\酒店预订系统.exe`（PyInstaller 打包，无需安装 Python）。

exe 首次运行会在 `code\dist` 下创建 `hotel.db` 演示数据库；删除该文件即可恢复初始数据。

## 用源码运行

```bash
cd code
python main.py --gui           # Tkinter 桌面界面
python main.py                 # 交互式 CLI
python main.py --demo          # 运行完整演示流程
python main.py --db demo.db    # 指定数据库文件
```

演示账号：

| 角色 | 手机号 | 密码 |
|---|---|---|
| 平台管理员 | 13900000000 | admin123 |
| 酒店老板 | 13800000001 | owner123 |
| 酒店前台 | 13800000002 | desk123 |
| 客人 | 13800000003 | guest123 |

## 目录

```
code/
├── main.py                 入口
├── hotel_booking/
│   ├── domain.py           枚举、状态机与转换规则
│   ├── db.py               SQLite 建表与演示数据
│   ├── repository.py       数据访问层
│   ├── pricing.py          价格优先级计算
│   ├── inventory.py        每日库存与停售校验
│   ├── booking.py          下单、改单、取消、入住、退房
│   ├── billing.py          账单、收款、作废
│   ├── frontdesk.py        房态、消费退款
│   ├── hotel_admin.py      入驻审核、房型价格、停售、员工
│   ├── governance.py       投诉与日志
│   ├── reports.py          报表、看板、间夜快照
│   ├── auth.py             登录与注册
│   ├── cli.py              交互式菜单
│   └── demo.py             演示流程
└── tests/                  pytest 单元测试
```

## 已实现功能

- 四类角色：客人、酒店前台、酒店老板、平台管理员；子账号上限 10 个。
- 酒店入驻/审核/下架/封禁；房型、房间、每日库存、基础价与周末价/区间价/单日价。
- 按城市、日期、人数、房型、价格查询；下单立即生效，逐晚条件扣减库存。
- 幂等键防重复下单；改单不超过 2 次且整单原子；取消按取消规则计费。
- 分房入住、房态流转、在店消费、分次收款、退房结算、账单作废。
- 投诉提交与处理、操作日志、隐私脱敏与查看全号留痕。
- 营收、出租率、消费明细、城市汇总、实时看板与间夜快照。

## 质量

```bash
python -m pytest -q          # 25 passed
python -m pylint hotel_booking   # 10.00/10（.pylintrc 仅关闭设计类检查）
```

源码规模：`hotel_booking` 包约 **4,884 行非空代码**（5,422 行物理行），测试约 353 行；
不含任何 GUI 工具自动生成的代码（界面为手写 Tkinter）。

## 界面

`python main.py --gui` 打开桌面客户端：粉色渐变登录页、手绘小兔子、粉色表头与按角色切换的侧边栏。
客人可查询/下单/看账单，前台可接待、看房态、登记消费与收款，老板可维护房型价格、停售、商品员工与报表，
管理员可审核、处理投诉、审批调价。界面截图见 `docs/gui_login.png`、`docs/gui_guest_search.png`、
`docs/gui_desk.png`、`docs/gui_owner.png`。

## 与实验二设计的关系

- 类图 → `domain.py` + `db.py` 表结构 + `repository.py`。
- 用例图 → `gui.py` 的页面与 `cli.py` 的菜单，均对应各服务方法。
- 组件图 → 按模块拆分的 `pricing/inventory/booking/billing/frontdesk/hotel_admin/governance/reports`。
- 时序图 → `booking.create_order`/`modify_order`/`cancel_order` 中的事务与条件更新。

为便于单机运行，实现与设计做了少量取舍：数据库使用 SQLite 而不是 MySQL；桌面界面用 Tkinter 实现
（未使用 Figma/亿图设计稿逐像素还原）；一个订单只包含一个房型，多房型订单留作扩展；平台调价审批
按 7 天有效期实现，未做独立的审批页面。
