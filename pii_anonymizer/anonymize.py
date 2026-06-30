#!/usr/bin/env python3
"""
מקודד קובץ אקסל: מצפין כל עמודה שמסומנת ידנית - הכותרת מכילה את המילה "תקודד"
(עם או בלי מרכאות), או שתא הכותרת צבוע במילוי רקע שחור עם גופן לבן - ומחליף את
כל הערכים שמתחתיה בקודים אנונימיים. שומר קובץ מיפוי מקומי (mapping.json) שאינו
עולה לשום מקום - יש להשתמש בו מאוחר יותר עם restore.py כדי לשחזר את הנתונים
המקוריים בקובץ שמתקבל בחזרה.

שימוש:
    python anonymize.py --in data.xlsx --out anon.xlsx --mapping mapping.json
"""
import argparse

import openpyxl

from core import anonymize_workbook


def anonymize(in_path: str, out_path: str, mapping_path: str):
    wb = openpyxl.load_workbook(in_path)
    mapper = anonymize_workbook(wb)

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
    args = parser.parse_args()
    anonymize(args.in_path, args.out_path, args.mapping_path)


if __name__ == "__main__":
    main()
