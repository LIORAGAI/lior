#!/usr/bin/env python3
"""
מקודד קובץ אקסל: מזהה עמודות/תאים עם מידע מזהה (ת.ז, שם, ח.פ, טלפון, מייל וכו')
ומחליף אותם בקודים אנונימיים. שומר קובץ מיפוי מקומי (mapping.json) שאינו עולה לשום מקום -
יש להשתמש בו מאוחר יותר עם restore.py כדי לשחזר את הנתונים המקוריים בקובץ שמתקבל בחזרה.

שימוש:
    python anonymize.py --in data.xlsx --out anon.xlsx --mapping mapping.json
"""
import argparse

import openpyxl

from detector import classify_cell_content, match_column_keyword
from mapping import CodeMapper


def detect_columns(ws):
    """מחזיר dict: אינדקס עמודה -> סוג PII, על סמך שם הכותרת (שורה ראשונה)."""
    detected = {}
    for col_idx, cell in enumerate(ws[1], start=1):
        if cell.value is None:
            continue
        pii_type = match_column_keyword(cell.value)
        if pii_type:
            detected[col_idx] = pii_type
    return detected


def find_ambiguous_columns(ws, already_detected):
    """מאתר עמודות טקסט עם ערכים ייחודיים ברובם, שלא זוהו לפי כותרת - מועמדות לבדיקה ידנית."""
    ambiguous = []
    n_rows = ws.max_row - 1
    if n_rows <= 0:
        return ambiguous
    for col_idx in range(1, ws.max_column + 1):
        if col_idx in already_detected:
            continue
        header = ws.cell(row=1, column=col_idx).value
        values = [ws.cell(row=r, column=col_idx).value for r in range(2, ws.max_row + 1)]
        text_values = [v for v in values if isinstance(v, str) and v.strip()]
        if not text_values:
            continue
        uniqueness = len(set(text_values)) / len(text_values)
        # ערכי טקסט עם גיוון גבוה (לא קטגוריאליים) עשויים להיות מזהים אישיים
        if uniqueness > 0.6 and len(text_values) >= 3:
            ambiguous.append((col_idx, header))
    return ambiguous


def ask_user_about_columns(ws, ambiguous_columns):
    """שואל את המשתמש באופן אינטראקטיבי לגבי עמודות לא ודאיות, ומחזיר dict נוסף לעמודות שאושרו."""
    confirmed = {}
    for col_idx, header in ambiguous_columns:
        sample = [ws.cell(row=r, column=col_idx).value for r in range(2, min(ws.max_row, 4) + 1)]
        sample = [s for s in sample if s]
        print(f"\nעמודה '{header}' (טור {col_idx}) - דוגמאות: {sample}")
        answer = input("האם זו עמודת מידע מזהה שיש להסתיר? [y/N]: ").strip().lower()
        if answer == "y":
            print("איזה סוג מידע זה? (NAME / COMPANY_NAME / ID / COMPANY_ID / PHONE / EMAIL / ADDRESS / GENERIC)")
            pii_type = input("סוג [GENERIC]: ").strip().upper() or "GENERIC"
            confirmed[col_idx] = pii_type
    return confirmed


def anonymize(in_path: str, out_path: str, mapping_path: str, auto_yes: bool):
    wb = openpyxl.load_workbook(in_path)
    mapper = CodeMapper()

    for ws in wb.worksheets:
        if ws.max_row < 2:
            continue
        col_types = detect_columns(ws)

        if not auto_yes:
            ambiguous = find_ambiguous_columns(ws, col_types)
            if ambiguous:
                col_types.update(ask_user_about_columns(ws, ambiguous))

        for row in range(2, ws.max_row + 1):
            for col_idx, pii_type in col_types.items():
                cell = ws.cell(row=row, column=col_idx)
                if cell.value is None or str(cell.value).strip() == "":
                    continue
                cell.value = mapper.encode(pii_type, str(cell.value))

        # זיהוי תוכן מזהה גם בעמודות שלא סומנו (למשל ת.ז שמופיעה בעמודה ללא כותרת מתאימה)
        for row in range(2, ws.max_row + 1):
            for col_idx in range(1, ws.max_column + 1):
                if col_idx in col_types:
                    continue
                cell = ws.cell(row=row, column=col_idx)
                if cell.value is None:
                    continue
                pii_type = classify_cell_content(cell.value)
                if pii_type:
                    cell.value = mapper.encode(pii_type, str(cell.value))

    wb.save(out_path)
    mapper.save(mapping_path)
    print(f"\nנשמר קובץ מקודד: {out_path}")
    print(f"נשמר קובץ מיפוי (שמור מקומית, לא להעלות לשום מקום!): {mapping_path}")


def main():
    parser = argparse.ArgumentParser(description="הסתרת מידע מזהה (PII) בקובץ אקסל")
    parser.add_argument("--in", dest="in_path", required=True, help="קובץ אקסל מקור")
    parser.add_argument("--out", dest="out_path", required=True, help="קובץ אקסל מקודד לפלט")
    parser.add_argument("--mapping", dest="mapping_path", default="mapping.json",
                         help="נתיב לקובץ מיפוי (ברירת מחדל: mapping.json)")
    parser.add_argument("--yes", action="store_true",
                         help="דלג על שאלות אינטראקטיביות לגבי עמודות לא ודאיות")
    args = parser.parse_args()
    anonymize(args.in_path, args.out_path, args.mapping_path, args.yes)


if __name__ == "__main__":
    main()
