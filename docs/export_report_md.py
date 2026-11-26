"""Export the final DOCX report to Markdown, preserving order, tables and figures."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(r"C:\study\rjgc\lab3\实验3_241220081_刘子健")
DOCX = ROOT / "docs" / "实验报告.docx"
OUT = ROOT / "实验报告.md"

IMAGE_MAP = {
    "图 2-1": "UML/UML类图.png",
    "图 2-2": "UML/UML用例图.png",
    "图 2-3": "UML/UML组件图.png",
    "图 2-4": "UML/UML时序图_并发下单.png",
    "图 3-1": "docs/gui_login.png",
    "图 3-2": "docs/gui_desk.png",
}


def is_image(paragraph: Paragraph) -> bool:
    return bool(paragraph._element.findall(".//" + qn("w:drawing")))


def is_code(paragraph: Paragraph) -> bool:
    runs = [run for run in paragraph.runs if run.text.strip()]
    return bool(runs) and all((run.font.name or "") == "Consolas" for run in runs)


def heading_level(text: str) -> int | None:
    if text in ("摘  要", "摘 要"):
        return 2
    if re.match(r"^[一二三四五六七八]、", text):
        return 2
    if re.match(r"^\d+\.\d+ ", text):
        return 3
    if text.startswith("附录 "):
        return 2
    return None


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>").strip()


def table_md(table: Table) -> list[str]:
    rows = []
    for row in table.rows:
        rows.append([escape_cell(cell.text) for cell in row.cells])
    if not rows:
        return []
    width = max(len(row) for row in rows)
    for row in rows:
        row.extend([""] * (width - len(row)))
    lines = ["| " + " | ".join(rows[0]) + " |",
             "|" + "|".join(["---"] * width) + "|"]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def build() -> None:
    doc = Document(DOCX)
    children = list(doc.element.body.iterchildren())
    lines: list[str] = []
    code_buffer: list[str] = []
    cover_done = False
    cover_table_done = False

    def flush_code() -> None:
        if code_buffer:
            lines.append("```text")
            lines.extend(code_buffer)
            lines.append("```")
            lines.append("")
            code_buffer.clear()

    index = 0
    while index < len(children):
        child = children[index]
        if child.tag == qn("w:tbl"):
            flush_code()
            table = Table(child, doc)
            # The first table is the cover metadata; keep it as a compact table.
            if not cover_table_done and not cover_done:
                lines.extend(table_md(table))
                lines.append("")
                cover_table_done = True
                index += 1
                continue
            lines.extend(table_md(table))
            lines.append("")
            index += 1
            continue
        if child.tag != qn("w:p"):
            index += 1
            continue

        paragraph = Paragraph(child, doc)
        text = paragraph.text.strip()

        if is_image(paragraph):
            flush_code()
            caption = ""
            if index + 1 < len(children) and children[index + 1].tag == qn("w:p"):
                caption = Paragraph(children[index + 1], doc).text.strip()
            target = ""
            for prefix, path in IMAGE_MAP.items():
                if caption.startswith(prefix):
                    target = path
                    break
            alt = caption or "运行截图"
            if target:
                lines.append(f"![{alt}]({target})")
            else:
                lines.append(f"![{alt}]()")
            if caption:
                lines.append(f"*{caption}*")
                index += 1
            lines.append("")
            index += 1
            continue

        if is_code(paragraph):
            code_buffer.append(paragraph.text.rstrip())
            index += 1
            continue
        flush_code()

        if not text:
            index += 1
            continue

        level = heading_level(text)
        if level:
            lines.append("#" * level + " " + text)
            lines.append("")
            if text in ("摘  要", "摘 要"):
                cover_done = True
            index += 1
            continue

        if not cover_done and text.startswith("实验三"):
            lines.append("# " + text)
            lines.append("")
            index += 1
            continue
        if not cover_done and text.startswith("——"):
            lines.append("## " + text)
            lines.append("")
            index += 1
            continue

        if text.startswith("图 "):
            lines.append(f"*{text}*")
        else:
            lines.append(text)
        lines.append("")
        index += 1

    flush_code()
    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("saved", OUT, "lines", len(lines))


if __name__ == "__main__":
    build()
