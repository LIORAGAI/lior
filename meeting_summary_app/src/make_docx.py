"""המרת סיכום (Markdown פשוט) למסמך Word בעברית: David 12, ימין לשמאל.

שימוש:  python make_docx.py <summary.md> <output.docx>

תחביר נתמך:  # כותרת | ## כותרת סעיף | ### תת-כותרת | - תבליט | 1. מספור
             ☐ משימה | שורות טבלה |a|b| | **מודגש**
"""
import re
import sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

FONT = "David"


def set_rtl_par(p):
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = p._p.get_or_add_pPr()
    if pPr.find(qn("w:bidi")) is None:
        pPr.append(OxmlElement("w:bidi"))


def style_run(run, size=12, bold=False):
    run.bold = bold
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    rPr = run._r.get_or_add_rPr()
    fonts = rPr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rPr.insert(0, fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), FONT)
    rPr.append(OxmlElement("w:rtl"))
    szCs = OxmlElement("w:szCs")
    szCs.set(qn("w:val"), str(size * 2))
    rPr.append(szCs)
    if bold:
        rPr.append(OxmlElement("w:bCs"))


def add_text(p, text, size=12, bold=False):
    # **מודגש** בתוך שורה
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if part:
            style_run(p.add_run(part), size, bold or i % 2 == 1)


def add_par(doc, text, style=None, size=12, bold=False):
    p = doc.add_paragraph(style=style)
    set_rtl_par(p)
    add_text(p, text, size, bold)
    return p


def add_table(doc, rows):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table._tbl.tblPr.append(OxmlElement("w:bidiVisual"))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            p = table.cell(r, c).paragraphs[0]
            set_rtl_par(p)
            add_text(p, val, 12, bold=(r == 0))
    doc.add_paragraph()


def main(src, dst):
    doc = Document()
    doc.sections[0]._sectPr.append(OxmlElement("w:bidi"))
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(12)

    table_rows = []
    lines = open(src, encoding="utf-8-sig").read().splitlines()
    for line in lines + [""]:
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                table_rows.append(cells)
            continue
        if table_rows:
            add_table(doc, table_rows)
            table_rows = []
        if not s:
            continue
        if s.startswith("# "):
            p = add_par(doc, s[2:], size=16, bold=True)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif s.startswith("## "):
            add_par(doc, s[3:], size=14, bold=True)
        elif s.startswith("### "):
            add_par(doc, s[4:], size=12, bold=True)
        elif s.startswith("- "):
            add_par(doc, s[2:], style="List Bullet")
        elif re.match(r"\d+\.\s", s):
            add_par(doc, re.sub(r"^\d+\.\s+", "", s), style="List Number")
        else:
            add_par(doc, s)

    doc.save(dst)
    print(dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
