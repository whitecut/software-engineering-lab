"""Build the fill-in report template for lab 3 (facts + placeholders, no prose)."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(r"C:\study\rjgc\lab3\实验3_241220081_刘子健")
DOCS = ROOT / "docs"
UML = ROOT / "UML"
OUT = DOCS / "实验报告_可填写模板.docx"

BODY_FONT = "宋体"
HEAD_FONT = "微软雅黑"
INK = RGBColor(0x33, 0x33, 0x33)
ACCENT = RGBColor(0xB0, 0x3A, 0x5B)
GRAY = RGBColor(0x66, 0x66, 0x66)


def set_run_font(run, name: str = BODY_FONT, size: float | None = None,
                 bold: bool | None = None, color: RGBColor | None = None) -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def shade(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def add_table(doc, headers: list[str], rows: list[list[str]], widths: list[float],
              font_size: float = 9) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for index, head in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = ""
        run = cell.paragraphs[0].add_run(head)
        set_run_font(run, HEAD_FONT, font_size, True)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        shade(cell, "F8E1EA")
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = ""
            run = cells[index].paragraphs[0].add_run(str(value))
            set_run_font(run, BODY_FONT, font_size)
    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Cm(width)
    doc.add_paragraph()


def add_image(doc, path: Path, caption: str, width: float = 15.5) -> None:
    if not path.exists():
        return
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(path), width=Cm(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(caption)
    set_run_font(run, BODY_FONT, 9, False, GRAY)


def placeholder(doc, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Pt(21)
    run = paragraph.add_run("【" + text + "】")
    set_run_font(run, BODY_FONT, 10.5, False, ACCENT)


def body(doc, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Pt(21)
    run = paragraph.add_run(text)
    set_run_font(run, BODY_FONT, 10.5, False, INK)


def heading(doc, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(text)
    set_run_font(run, HEAD_FONT, 16 if level == 1 else 12.5, True,
                 ACCENT if level == 1 else INK)
    if level == 1:
        paragraph.paragraph_format.page_break_before = True


def setup(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.4)
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    normal.paragraph_format.line_spacing = 1.35
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("实验三 软件实现与构建 · 241220081 刘子健  ·  第 ")
    set_run_font(run, BODY_FONT, 8.5, False, GRAY)
    page_run = footer.add_run()
    set_run_font(page_run, BODY_FONT, 8.5, False, GRAY)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    page_run._r.append(begin)
    page_run._r.append(instr)
    page_run._r.append(end)
    tail = footer.add_run(" 页")
    set_run_font(tail, BODY_FONT, 8.5, False, GRAY)


def cover(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("实验三  软件实现与构建")
    set_run_font(run, HEAD_FONT, 26, True, ACCENT)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run("——酒店预订系统的 UML 实现与工程化构建")
    set_run_font(run, HEAD_FONT, 15, False, INK)
    for _ in range(3):
        doc.add_paragraph()
    info = doc.add_table(rows=4, cols=2)
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    data = [("学    院", "计算机学院"), ("专    业", "软件工程"),
            ("学    号", "241220081"), ("姓    名", "刘子健")]
    for row, (key, value) in zip(info.rows, data):
        row.cells[0].text = ""
        row.cells[1].text = ""
        r1 = row.cells[0].paragraphs[0].add_run(key)
        r2 = row.cells[1].paragraphs[0].add_run(value)
        set_run_font(r1, BODY_FONT, 12, False, GRAY)
        set_run_font(r2, BODY_FONT, 12, True, INK)
    for _ in range(5):
        doc.add_paragraph()
    date = doc.add_paragraph()
    date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date.add_run("2026 年 11 月")
    set_run_font(run, BODY_FONT, 11, False, GRAY)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def notice(doc: Document) -> None:
    heading(doc, "使用说明（提交前请删除本页）", 1)
    body(doc, "本文件是按实验三 3.1 节要求排版的可填写模板：封面、章节、图表、"
              "数据表已经准备好，正文中以【】标出的位置需要由本人撰写。")
    body(doc, "实验三 PDF 第 3.1 节明确写着“实验报告的书写不允许使用大模型的辅助”。"
              "因此本模板只提供结构、事实数据和图表，不包含可直接提交的正文；"
              "请用自己的话补全【】中的内容，删除本页后再导出最终 PDF。")
    body(doc, "模板中的代码规模、测试、pylint、Git 提交、界面截图均来自本仓库的实际运行结果，"
              "数据来源见 docs/报告素材.md。")


def build() -> None:
    doc = Document()
    setup(doc)
    cover(doc)
    notice(doc)

    heading(doc, "摘  要", 1)
    placeholder(doc, "请写 200~300 字：项目背景、实现了哪些角色与业务、代码规模、测试与运行结果、"
                     "你觉得最值得说明的一点")
    body(doc, "关键词：酒店预订；UML；Python；SQLite；Tkinter；单元测试")

    heading(doc, "一、实验任务与项目概述", 1)
    placeholder(doc, "用自己的话说明实验三的任务：把实验二的 UML 设计落地为可运行软件，"
                     "并完成编译、测试、Git 管理与报告")
    placeholder(doc, "介绍酒店预订系统的业务范围：客人、前台、老板、平台管理员四类角色，"
                     "以及查询、预订、接待、结算、治理五块业务")
    placeholder(doc, "说明技术选型及理由：Python 3.12 + SQLite + Tkinter，为什么适合本次实验")

    heading(doc, "二、UML 设计回顾", 1)
    body(doc, "实验二共保留 4 张核心 UML 图：类图、用例图、组件图、时序图（并发下单）。")
    add_image(doc, UML / "UML类图.png", "图 2-1  类图（实验二最终版）")
    add_image(doc, UML / "UML用例图.png", "图 2-2  用例图（实验二最终版）")
    add_image(doc, UML / "UML组件图.png", "图 2-3  组件图（实验二最终版）")
    add_image(doc, UML / "UML时序图_并发下单.png", "图 2-4  并发下单时序图（实验二最终版）")
    placeholder(doc, "用 1~2 段说明这 4 张图分别约束了实现的哪些方面，以及实验三是否对设计做了微调")

    heading(doc, "三、从 UML 到代码的实现", 1)
    heading(doc, "3.1 总体实现思路", 2)
    placeholder(doc, "描述你的落地顺序：先实体与表结构，再仓储与领域规则，再服务，最后界面；"
                     "说明为什么这样排序")
    placeholder(doc, "说明分层：界面层、服务层、领域/数据层各自负责什么，依赖方向如何")

    heading(doc, "3.2 类图 → 领域模型与数据表", 2)
    add_table(doc,
              ["实验二类图中的元素", "代码落点", "实现说明"],
              [["账号、酒店、房型、房间", "db.py 的 accounts/hotels/room_types/rooms 表", "唯一键与外键按类图约束"],
               ["每日库存", "inventory 表（room_type_id + date 主键）", "total/sold/version 支持条件扣减"],
               ["订单、订单夜、订单房间", "orders/order_nights/order_rooms", "order_nights 保存价格快照"],
               ["账单、支付、消费", "bills/payments/consumptions", "已收 + 未收 = 应收"],
               ["投诉、日志、快照", "complaints/operation_logs/snapshots", "日志只增不改"],
               ["订单状态机", "domain.py 的 ORDER_TRANSITIONS", "服务层统一校验状态转换"]],
              [4.2, 7.0, 5.0])
    placeholder(doc, "挑 1~2 个类，说明字段/约束是如何从类图推出来的；"
                     "例如订单状态为什么需要状态机、库存为什么按天建行")
    placeholder(doc, "说明枚举与状态机放在 domain.py 的好处，以及你遇到的建模取舍")

    heading(doc, "3.3 用例图 → 界面与用例实现", 2)
    add_image(doc, DOCS / "gui_login.png", "图 3-1  桌面端登录页（实际运行截图）", 13.5)
    add_image(doc, DOCS / "gui_desk.png", "图 3-2  前台接待工作台（实际运行截图）", 15.0)
    add_table(doc,
              ["用例", "界面入口", "服务方法"],
              [["查询酒店/房型", "客人 → 查询与预订", "BookingService.search"],
               ["下单/改单/取消", "客人 → 我的订单", "create_order / modify_order / cancel_order"],
               ["入住/退房", "前台 → 接待工作台", "check_in / check_out / mark_no_show"],
               ["消费/收款", "前台 → 消费与收款", "add_consumption / BillingService.add_payment"],
               ["房型/价格/停售", "老板 → 房型与房间、价格与停售", "HotelAdminService"],
               ["审核/投诉/审批", "管理员 → 入驻审核、投诉处理、调价审批", "review / handle / approve_price"]],
              [4.0, 6.0, 6.2])
    placeholder(doc, "说明你如何把用例图中的参与者映射为角色权限，"
                     "以及界面上的哪些按钮对应哪些服务方法")
    placeholder(doc, "举一个“界面只做收集参数、业务规则放服务层”的例子")

    heading(doc, "3.4 组件图 → 模块划分", 2)
    add_table(doc,
              ["组件", "文件", "职责"],
              [["预订组件", "booking.py", "下单、改单、取消、入住、退房"],
               ["库存组件", "inventory.py", "每日可售校验、扣减、释放"],
               ["价格组件", "pricing.py", "单日 > 区间 > 周末 > 基础价"],
               ["结算组件", "billing.py", "账单重算、收款、作废"],
               ["接待组件", "frontdesk.py", "房态、消费退款"],
               ["酒店维护组件", "hotel_admin.py", "房型、价格、停售、员工、审核"],
               ["治理组件", "governance.py / audit.py", "投诉、操作日志"],
               ["报表组件", "reports.py", "营收、出租率、看板、快照"]],
              [3.6, 5.0, 7.6])
    placeholder(doc, "说明组件之间的依赖关系，为什么库存/价格/结算要被多个组件复用")
    placeholder(doc, "说明 Repository 在组件之间起什么作用，是否出现过循环依赖")

    heading(doc, "3.5 时序图 → 事务与并发控制", 2)
    placeholder(doc, "按并发下单时序图，描述一次下单的调用链：界面 → BookingService → InventoryService → Repository → SQLite")
    placeholder(doc, "重点解释：为什么用 UPDATE ... WHERE total - sold >= ? 的条件更新，"
                     "而不是先查再改；失败时如何回滚")
    placeholder(doc, "说明幂等键、改单先释放再扣减、取消释放库存分别解决什么问题")
    add_table(doc,
              ["并发/一致性问题", "实现手段", "对应时序图消息"],
              [["同一晚超卖", "条件 UPDATE + 事务", "reserveInventory"],
               ["重复提交", "idempotency 表 + 唯一键", "createOrder"],
               ["改单部分成功", "with conn 整单事务", "release / reserve"],
               ["取消后库存不释放", "cancel_order 中逐晚 release", "releaseInventory"],
               ["账单金额不一致", "每次变更后 rebuild", "recalculateBill"]],
              [4.2, 7.0, 5.0])

    heading(doc, "3.6 源代码规模", 2)
    body(doc, "统计口径：hotel_booking 包内 .py 文件的非空行；不含空行。")
    add_table(doc,
              ["文件", "非空行", "物理行", "说明"],
              [["gui.py", "1,402", "1,519", "Tkinter 桌面界面"],
               ["cli.py", "484", "520", "命令行界面"],
               ["booking.py", "494", "520", "预订与订单状态"],
               ["hotel_admin.py", "459", "490", "酒店维护与审核"],
               ["db.py", "394", "441", "建表与演示数据"],
               ["repository.py", "655", "738", "数据访问"],
               ["reports.py", "165", "179", "报表"],
               ["billing.py", "132", "142", "账单与收款"],
               ["其他 13 个文件", "699", "873", "领域、工具、服务等"],
               ["合计", "4,884", "5,422", "不含测试与第三方库"]],
              [5.0, 3.0, 3.0, 5.2])
    placeholder(doc, "说明这个规模是否达到 1,500 行要求，"
                     "以及你如何统计（工具/命令）、是否包含自动生成代码")
    body(doc, "测试代码：tests/test_booking.py、tests/test_admin.py，共 25 个测试，非空 353 行。")

    heading(doc, "四、大模型辅助代码实现", 1)
    heading(doc, "4.1 使用了哪些工具、怎么用", 2)
    placeholder(doc, "写清楚工具名称、使用方式（对话/补全）、你给它的输入（UML、需求、错误日志）")
    placeholder(doc, "说明你如何拆任务：先让它生成什么，再生成什么，哪些部分坚持自己写")
    heading(doc, "4.2 大模型具体帮你做了哪些工作", 2)
    add_table(doc,
              ["次数", "场景", "生成内容", "你的处理"],
              [["1", "领域模型与建表", "实体字段、SQLite 建表、仓储草稿", "补 price_approvals 表；调整价格快照"],
               ["2", "服务层", "预订/改单/取消/入住/结算初版", "补权限校验、回滚、幂等"],
               ["3", "单元测试", "15 个测试草稿", "修正周末价/取消时限假设，补 10 个管理端测试"],
               ["4", "代码风格", "black 格式化、pylint 修复建议", "删未用导入、拆长行、补 docstring"],
               ["5", "演示与文档", "演示脚本、README、报告素材", "修正跨酒店入住、核对账单口径"],
               ["6", "桌面界面", "Tkinter 页面骨架与表单", "修登录后旧导航引用，补演示订单"],
               ["7", "界面主题", "粉色渐变、小兔子、表头与按钮配色", "修侧边栏/表头样式，补渐变与兔子"],
               ["8", "可执行文件", "cmd/vbs/pyw 启动器与打包命令", "改 ASCII 启动器，实测 exe 窗口"]],
              [1.2, 3.2, 6.5, 5.8], 8.5)
    heading(doc, "4.3 生成不符合预期时怎么处理", 2)
    placeholder(doc, "至少写 2 个具体例子：大模型生成了什么、哪里不对、你怎么定位、最后怎么改")
    placeholder(doc, "可以写：测试假设错误、跨酒店权限缺失、取消账单未清零、"
                     "cmd 中文路径编码错误等")
    placeholder(doc, "总结你对“大模型能做什么、不能做什么”的判断")

    heading(doc, "五、编译与运行结果", 1)
    body(doc, "环境：Windows 11 / Python 3.12.14 / SQLite 3.53.1 / pytest 9.2.0 / pylint 4.1.4。")
    add_table(doc,
              ["检查", "命令", "结果"],
              [["语法编译", "python -m compileall -q hotel_booking main.py", "退出码 0"],
               ["单元测试", "python -m pytest -q", "25 passed，约 8 秒"],
               ["代码风格", "python -m pylint hotel_booking", "10.00/10"],
               ["演示运行", "python main.py --demo --db :memory:", "完整流程正常结束"],
               ["桌面启动", "双击 启动界面.cmd / 酒店预订系统.exe", "窗口正常打开"]],
              [3.2, 8.0, 5.0])
    add_image(doc, DOCS / "gui_guest_search.png", "图 5-1  查询与预订运行截图", 15.0)
    placeholder(doc, "贴 10~20 行关键运行输出（下单、改单、入住、收款、取消），并解释输出说明什么")
    placeholder(doc, "说明测试覆盖了哪些风险点，有没有还没覆盖的部分")
    placeholder(doc, "如果运行失败过，写失败现象、定位过程、修复结果")

    heading(doc, "六、Git 远程代码管理", 1)
    body(doc, "仓库：https://github.com/whitecut/software-engineering-lab.git；分支：lab3；标签：lab3-final。")
    add_table(doc,
              ["提交", "说明"],
              [["66b5408", "领域模型、SQLite 表结构与数据访问层"],
               ["425cda5", "业务服务、CLI 交互与 25 个单元测试"],
               ["b1eb053", "UML 副本、运行结果、测试与代码风格数据"],
               ["1155d1e", "补充推送脚本与 Git 说明"],
               ["2542185", "记录编译结果"],
               ["a4a92d9", "增加 Tkinter 桌面界面与界面截图"],
               ["14139f2", "界面改为粉色少女心主题"],
               ["4da7bbf", "增加双击启动器与独立 exe"],
               ["f9e9764", "清理临时截图"],
               ["def878a", "增加可填写实验报告模板与 PDF"]],
              [4.0, 11.0])
    placeholder(doc, "说明你如何分阶段提交、提交信息怎么写、有没有用分支/标签")
    placeholder(doc, "贴 GitHub 仓库页面或 git log 截图；如果还没推送，写清楚当前状态和原因")

    heading(doc, "七、遇到的问题与改进方向", 1)
    placeholder(doc, "列 3~4 个实现中遇到的问题：现象、原因、解决方式、学到什么")
    placeholder(doc, "写当前原型的不足：单房型订单、SQLite、未接真实支付、未做 Web 端等")
    placeholder(doc, "如果继续做，下一步优先做什么")

    heading(doc, "八、总结", 1)
    placeholder(doc, "用 2~3 段总结：UML 对实现的帮助、大模型辅助的边界、工程化收获")
    placeholder(doc, "写你认为本次实验最有价值的一次修改，以及为什么")

    heading(doc, "附录 A  25 个测试覆盖点", 1)
    body(doc, "价格优先级；搜索排序；下单扣库存/幂等/取消释放；逐晚扣减失败回滚；"
              "改单价格快照/2 次上限/无房原子失败；取消扣费；重复分房拦截；"
              "账单与分次收款；停售拦截；房态转换；投诉流程；手机号脱敏与留痕；"
              "角色越权；报表与快照；酒店审核；调价审批与过期；前台代订；"
              "未到店；消费退款；账单作废；员工子账号。")
    heading(doc, "附录 B  运行输出节选", 1)
    body(doc, "完整输出见 docs/运行结果.txt；测试输出见 docs/pytest结果.txt；"
              "代码风格输出见 docs/pylint结果.txt。")
    placeholder(doc, "粘贴你认为最能说明问题的一段输出")

    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    build()
