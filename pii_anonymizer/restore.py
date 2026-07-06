#!/usr/bin/env python3
"""
משחזר קובץ אקסל שחזר מקלוד (או כל עיבוד אחר) עם קודים אנונימיים, בחזרה לערכים המקוריים,
לפי קובץ המיפוי המקומי שנוצר ב-anonymize.py. הסריקה מתבצעת על כל תא, כולל קודים שמופיעים
בתוך משפט/טקסט חופשי (לא רק התאמה מדויקת של תא שלם).

שימוש:
    python restore.py --in result.xlsx --out final.xlsx --mapping mapping.json
"""
import argparse

import openpyxl

from core import restore_workbook
from mapping import CodeMapper


def restore(in_path: str, out_path: str, mapping_path: str):
    mapper = CodeMapper.load(mapping_path)
    wb = openpyxl.load_workbook(in_path)
    replaced_count = restore_workbook(wb, mapper)
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
