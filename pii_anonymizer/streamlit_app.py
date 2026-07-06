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
from openpyxl.utils import get_column_letter

from core import anonymize_workbook, detect_force_encode_columns, restore_workbook
from detector import suggest_pii_type
from mapping import CodeMapper

# סוגי מידע לבחירה בממשק: סוג פנימי -> תווית בעברית (הסוג קובע את תחילית הקוד,
# למשל NAME -> [[NAME_0001]], כך שהקובץ המקודד נשאר קריא)
PII_TYPE_LABELS = {
    "NAME": "שם",
    "ID": "ת.ז",
    "COMPANY_ID": "ח.פ / עוסק מורשה",
    "COMPANY_NAME": "שם חברה",
    "PHONE": "טלפון",
    "EMAIL": "מייל",
    "ADDRESS": "כתובת",
    "GENERIC": "כללי",
}
PII_TYPE_ORDER = list(PII_TYPE_LABELS)

st.set_page_config(page_title="המקודד של ליאור", layout="centered")
st.title("המקודד של ליאור")
st.subheader("הסתרה ושחזור של מידע מזהה (PII) בקבצי אקסל")
st.caption("כל העיבוד מתבצע מקומית בדפדפן/בתהליך הזה בלבד. שום קובץ לא נשלח לשום שרת חיצוני.")

tab_anon, tab_restore = st.tabs(["1. הסתרת מידע לפני העלאה", "2. שחזור קובץ שחזר מעובד"])

with tab_anon:
    st.subheader("שלב 1: הסתרת מידע מזהה")
    st.caption(
        "העלו קובץ ובחרו מהרשימה אילו עמודות להצפין - אין צורך לערוך את הקובץ מראש. "
        "עמודות שכבר סומנו בקובץ (המילה \"תקודד\" בכותרת, או תא כותרת עם מילוי שחור "
        "וגופן לבן) יופיעו מסומנות מראש, ואפשר להוסיף או להסיר בחירה חופשי. "
        "לכל עמודה שנבחרה אפשר לקבוע את סוג המידע (שם, ת.ז, טלפון וכו') - הסוג נקבע "
        "אוטומטית לפי הכותרת וניתן לשינוי, והוא קובע את צורת הקוד בקובץ המקודד "
        "(למשל [[NAME_0001]] במקום [[VAL_0001]])."
    )
    uploaded = st.file_uploader("העלה קובץ אקסל מקורי", type=["xlsx"], key="anon_upload")

    if uploaded:
        file_bytes = uploaded.getvalue()
        wb = openpyxl.load_workbook(BytesIO(file_bytes))

        selected_col_types = {}
        for ws in wb.worksheets:
            if ws.max_row < 2:
                continue
            detected = detect_force_encode_columns(ws)
            headers = {
                col_idx: ws.cell(row=1, column=col_idx).value
                for col_idx in range(1, ws.max_column + 1)
            }

            def format_col(col_idx, headers=headers):
                letter = get_column_letter(col_idx)
                header = headers[col_idx]
                if header is None or str(header).strip() == "":
                    return f"עמודה {letter} (ללא כותרת)"
                return f"{letter} - {header}"

            chosen = st.multiselect(
                f"גיליון \"{ws.title}\" - בחרו עמודות להצפנה:",
                options=list(headers),
                default=[col_idx for col_idx in detected if col_idx in headers],
                format_func=format_col,
                key=f"anon_cols_{ws.title}",
            )
            if chosen:
                sheet_col_types = {}
                for col_idx in chosen:
                    suggested = suggest_pii_type(headers[col_idx])
                    sheet_col_types[col_idx] = st.selectbox(
                        f"סוג המידע בעמודה \"{format_col(col_idx)}\":",
                        options=PII_TYPE_ORDER,
                        index=PII_TYPE_ORDER.index(suggested),
                        format_func=lambda t: PII_TYPE_LABELS[t],
                        key=f"anon_type_{ws.title}_{col_idx}",
                    )
                selected_col_types[ws.title] = sheet_col_types

        if st.button("בצע הסתרה", type="primary"):
            if not selected_col_types:
                st.error("לא נבחרו עמודות להצפנה - בחרו לפחות עמודה אחת ונסו שוב.")
            else:
                mapper = anonymize_workbook(wb, manual_col_types=selected_col_types, auto_detect=False)

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
