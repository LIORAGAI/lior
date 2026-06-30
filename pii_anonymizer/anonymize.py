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

from core import anonymize_workbook, detect_black_marked_columns, detect_columns, find_ambiguous_columns


def ask_user_about_columns(ws, ambiguous_columns):
    """שואל את המשתמש באופן אינטראקטיבי לגבי עמודות לא ודאיות, ומחזיר dict נוסף לעמודות שאושרו."""
    confirmed = {}
    for col_idx, header, sample in ambiguous_columns:
        print(f"\nעמודה '{header}' (טור {col_idx}) - דוגמאות: {sample}")
        answer = input("האם זו עמודת מידע מזהה שיש להסתיר? [y/N]: ").strip().lower()
        if answer == "y":
            print("איזה סוג מידע זה? (NAME / COMPANY_NAME / ID / COMPANY_ID / PHONE / EMAIL / ADDRESS / GENERIC)")
            pii_type = input("סוג [GENERIC]: ").strip().upper() or "GENERIC"
            confirmed[col_idx] = pii_type
    return confirmed


def anonymize(in_path: str, out_path: str, mapping_path: str, auto_yes: bool):
    wb = openpyxl.load_workbook(in_path)
    manual_col_types = {}

    if not auto_yes:
        for ws in wb.worksheets:
            if ws.max_row < 2:
                continue
            already_detected = detect_columns(ws)
            already_detected.update(detect_black_marked_columns(ws))
            ambiguous = find_ambiguous_columns(ws, already_detected)
            if ambiguous:
                manual_col_types[ws.title] = ask_user_about_columns(ws, ambiguous)

    mapper = anonymize_workbook(wb, manual_col_types)

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
