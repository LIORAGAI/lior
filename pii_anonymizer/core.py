"""לוגיקת ליבה משותפת ל-CLI ולממשק ה-Streamlit: זיהוי, הסתרה ושחזור של PII בקובצי אקסל."""
import re

from detector import has_force_encode_keyword, is_black_fill_white_font, strip_quoted_force_encode_keyword
from mapping import CodeMapper


def detect_force_encode_columns(ws):
    """
    מחזיר dict: אינדקס עמודה -> "GENERIC" עבור עמודות שהכותרת שלהן מסומנת ידנית
    להצפנה - או שמכילה את מילת המפתח "תקודד" (עם או בלי מרכאות), או שצבועה
    במילוי רקע שחור עם גופן לבן.
    """
    marked = {}
    for col_idx, cell in enumerate(ws[1], start=1):
        if has_force_encode_keyword(cell.value) or is_black_fill_white_font(cell):
            marked[col_idx] = "GENERIC"
    return marked


def anonymize_workbook(wb, manual_col_types=None, auto_detect=True):
    """
    מסתיר את כל העמודות המסומנות ידנית להצפנה (כותרת "תקודד" או צביעה שחורה
    עם גופן לבן), בכל הגיליונות של wb (in-place), ומחזירה את ה-CodeMapper שנוצר.
    manual_col_types: dict אופציונלי {sheet_title: {col_idx: pii_type}} עבור עמודות
    שאושרו ידנית (למשל דרך ממשק משתמש), בנוסף לסימון האוטומטי.
    auto_detect=False מבטל את הזיהוי לפי סימון בכותרת, כך שהבחירה שהועברה
    ב-manual_col_types היא הקובעת הבלעדית (למשל כשמשתמש ביטל סימון בממשק).
    """
    manual_col_types = manual_col_types or {}
    mapper = CodeMapper()

    for ws in wb.worksheets:
        if ws.max_row < 2:
            continue
        col_types = detect_force_encode_columns(ws) if auto_detect else {}
        col_types.update(manual_col_types.get(ws.title, {}))

        # אם מילת המפתח "תקודד" מופיעה במרכאות בכותרת, מסירים אותה ומשאירים
        # רק את שאר הכותרת
        for col_idx in col_types:
            header_cell = ws.cell(row=1, column=col_idx)
            header_cell.value = strip_quoted_force_encode_keyword(header_cell.value)

        for row in range(2, ws.max_row + 1):
            for col_idx, pii_type in col_types.items():
                cell = ws.cell(row=row, column=col_idx)
                if cell.value is None or str(cell.value).strip() == "":
                    continue
                cell.value = mapper.encode(pii_type, str(cell.value))

    return mapper


def build_replacer(code_to_value: dict):
    # ממיינים מהקוד הארוך לקצר כדי למנוע התאמות חלקיות שגויות
    codes = sorted(code_to_value.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(c) for c in codes)) if codes else None

    def replace_in_text(text: str) -> str:
        if pattern is None:
            return text
        return pattern.sub(lambda m: code_to_value[m.group(0)], text)

    return replace_in_text


def restore_workbook(wb, mapper: CodeMapper):
    """משחזר ערכים מקוריים בכל הגיליונות של wb (in-place) לפי המיפוי. מחזיר את מספר התאים שהוחלפו."""
    code_to_value = mapper.code_to_value_map()
    replace_in_text = build_replacer(code_to_value)

    replaced_count = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "[[" in cell.value:
                    new_value = replace_in_text(cell.value)
                    if new_value != cell.value:
                        replaced_count += 1
                        cell.value = new_value
    return replaced_count
