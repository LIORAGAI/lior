#!/usr/bin/env python3
"""
ממשק Streamlit להסתרה ושחזור של מידע מזהה (PII) בקבצי אקסל.
כל העיבוד מתבצע מקומית בתהליך הזה בלבד - שום קובץ לא נשלח לשום שרת חיצוני.

הרצה:
    streamlit run streamlit_app.py
"""
import json
from io import BytesIO

import openpyxl
import streamlit as st

from core import anonymize_workbook, detect_columns, find_ambiguous_columns, restore_workbook
from mapping import CodeMapper

PII_TYPES = ["GENERIC", "NAME", "COMPANY_NAME", "ID", "COMPANY_ID", "PHONE", "EMAIL", "ADDRESS"]

st.set_page_config(page_title="הסתרת מידע מזהה באקסל", layout="centered")
st.title("הסתרה ושחזור של מידע מזהה (PII) בקבצי אקסל")
st.caption("כל העיבוד מתבצע מקומית בדפדפן/בתהליך הזה בלבד. שום קובץ לא נשלח לשום שרת חיצוני.")

tab_anon, tab_restore = st.tabs(["1. הסתרת מידע לפני העלאה", "2. שחזור קובץ שחזר מעובד"])

with tab_anon:
    st.subheader("שלב 1: הסתרת מידע מזהה")
    uploaded = st.file_uploader("העלה קובץ אקסל מקורי", type=["xlsx"], key="anon_upload")

    if uploaded:
        file_bytes = uploaded.getvalue()
        wb = openpyxl.load_workbook(BytesIO(file_bytes))
        manual_col_types: dict[str, dict[int, str]] = {}

        for ws in wb.worksheets:
            if ws.max_row < 2:
                continue
            auto_detected = detect_columns(ws)
            if auto_detected:
                names = ", ".join(
                    f"'{ws.cell(row=1, column=c).value}' ({t})" for c, t in auto_detected.items()
                )
                st.info(f"גיליון **{ws.title}** - זוהו אוטומטית: {names}")

            ambiguous = find_ambiguous_columns(ws, auto_detected)
            if ambiguous:
                st.markdown(f"**גיליון '{ws.title}' - עמודות לא ודאיות, אנא בדוק:**")
                sheet_manual = {}
                for col_idx, header, sample in ambiguous:
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        hide = st.checkbox(
                            f"'{header}' - דוגמאות: {sample}",
                            key=f"hide_{uploaded.name}_{ws.title}_{col_idx}",
                        )
                    with c2:
                        pii_type = st.selectbox(
                            "סוג", PII_TYPES, key=f"type_{uploaded.name}_{ws.title}_{col_idx}"
                        )
                    if hide:
                        sheet_manual[col_idx] = pii_type
                if sheet_manual:
                    manual_col_types[ws.title] = sheet_manual

        if st.button("בצע הסתרה", type="primary"):
            mapper = anonymize_workbook(wb, manual_col_types)

            out_buf = BytesIO()
            wb.save(out_buf)
            out_buf.seek(0)

            mapping_str = mapper.to_json_str()

            st.success("ההסתרה הושלמה. הקובץ המקודד בטוח להעלאה לקלוד.")
            st.warning(
                "קובץ המיפוי (mapping.json) הוא היחיד שמקשר בין הקודים לערכים האמיתיים - "
                "שמור אותו אצלך בלבד, **אל תעלה אותו לשום מקום**."
            )
            st.download_button(
                "הורד קובץ מקודד (בטוח להעלאה)",
                data=out_buf,
                file_name=f"anon_{uploaded.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.download_button(
                "הורד קובץ מיפוי (שמור פרטי!)",
                data=mapping_str,
                file_name="mapping.json",
                mime="application/json",
            )

with tab_restore:
    st.subheader("שלב 2: שחזור הקובץ שחזר מעובד מקלוד")
    proc_file = st.file_uploader("העלה את הקובץ המעובד (עם הקודים)", type=["xlsx"], key="restore_upload")
    mapping_file = st.file_uploader("העלה את קובץ המיפוי (mapping.json)", type=["json"], key="mapping_upload")

    if proc_file and mapping_file:
        if st.button("שחזר נתונים מקוריים", type="primary"):
            mapper = CodeMapper.from_dict(json.loads(mapping_file.getvalue()))
            wb = openpyxl.load_workbook(BytesIO(proc_file.getvalue()))
            replaced_count = restore_workbook(wb, mapper)

            out_buf = BytesIO()
            wb.save(out_buf)
            out_buf.seek(0)

            st.success(f"השחזור הושלם. הוחלפו {replaced_count} תאים שהכילו קודים מזהים.")
            st.download_button(
                "הורד קובץ סופי עם הנתונים המקוריים",
                data=out_buf,
                file_name=f"final_{proc_file.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
