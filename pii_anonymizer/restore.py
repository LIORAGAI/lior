#!/usr/bin/env python3
"""
משחזר קובץ אקסל שחזר מקלוד (או כל עיבוד אחר) עם קודים אנונימיים, בחזרה לערכים המקוריים,
לפי קובץ המיפוי המקומי שנוצר ב-anonymize.py. הסריקה מתבצעת על כל תא, כולל קודים שמופיעים
בתוך משפט/טקסט חופשי (לא רק התאמה מדויקת של תא שלם).

שימוש:
    python restore.py --in result.xlsx --out final.xlsx --mapping mapping.json
"""
import argparse
import re

import openpyxl

from mapping import CodeMapper


def build_replacer(code_to_value: dict):
    # ממיינים מהקוד הארוך לקצר כדי למנוע התאמות חלקיות שגויות
    codes = sorted(code_to_value.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(c) for c in codes)) if codes else None

    def replace_in_text(text: str) -> str:
        if pattern is None:
            return text
        return pattern.sub(lambda m: code_to_value[m.group(0)], text)

    return replace_in_text


def restore(in_path: str, out_path: str, mapping_path: str):
    mapper = CodeMapper.load(mapping_path)
    code_to_value = mapper.code_to_value_map()
    replace_in_text = build_replacer(code_to_value)

    wb = openpyxl.load_workbook(in_path)
    replaced_count = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "[[" in cell.value:
                    new_value = replace_in_text(cell.value)
                    if new_value != cell.value:
                        replaced_count += 1
                        cell.value = new_value

    wb.save(out_path)
    print(f"\nנשמר קובץ משוחזר: {out_path}")
    print(f"הוחלפו {replaced_count} תאים שהכילו קודים מזהים")


def main():
    parser = argparse.ArgumentParser(description="שחזור מידע מזהה (PII) בקובץ אקסל לפי קובץ מיפוי")
    parser.add_argument("--in", dest="in_path", required=True, help="קובץ אקסל מקודד (לאחר עיבוד)")
    parser.add_argument("--out", dest="out_path", required=True, help="קובץ אקסל משוחזר לפלט")
    parser.add_argument("--mapping", dest="mapping_path", default="mapping.json",
                         help="נתיב לקובץ מיפוי (ברירת מחדל: mapping.json)")
    args = parser.parse_args()
    restore(args.in_path, args.out_path, args.mapping_path)


if __name__ == "__main__":
    main()
