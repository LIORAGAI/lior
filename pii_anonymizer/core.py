"""לוגיקת ליבה משותפת ל-CLI ולממשק ה-Streamlit: זיהוי, הסתרה ושחזור של PII בקובצי אקסל."""
import re

from detector import classify_cell_content, is_black_fill, match_column_keyword
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


def detect_black_marked_columns(ws):
    """
    מחזיר dict: אינדקס עמודה -> "GENERIC" עבור עמודות שכל התאים בהן (כותרת ונתונים)
    צבועים ברקע שחור - סימון ידני של המשתמש שיש להסתיר את כל העמודה.
    """
    marked = {}
    for col_idx in range(1, ws.max_column + 1):
        cells = [ws.cell(row=r, column=col_idx) for r in range(1, ws.max_row + 1)]
        non_empty = [c for c in cells if c.value is not None and str(c.value).strip() != ""]
        if non_empty and all(is_black_fill(c) for c in non_empty):
            marked[col_idx] = "GENERIC"
    return marked


def anonymize_workbook(wb, manual_col_types=None):
    """
    מסתיר PII בכל הגיליונות של wb (in-place) ומחזירה את ה-CodeMapper שנוצר.
    manual_col_types: dict אופציונלי {sheet_title: {col_idx: pii_type}} עבור עמודות
    שאושרו ידנית (למשל דרך ממשק משתמש), בנוסף לזיהוי האוטומטי.
    """
    manual_col_types = manual_col_types or {}
    mapper = CodeMapper()

    for ws in wb.worksheets:
        if ws.max_row < 2:
            continue
        col_types = detect_columns(ws)
        col_types.update(detect_black_marked_columns(ws))
        col_types.update(manual_col_types.get(ws.title, {}))

        for row in range(2, ws.max_row + 1):
            for col_idx, pii_type in col_types.items():
                cell = ws.cell(row=row, column=col_idx)
                if cell.value is None or str(cell.value).strip() == "":
                    continue
                cell.value = mapper.encode(pii_type, str(cell.value))

        # זיהוי תוכן מזהה גם בעמודות שלא סומנו (למשל ת.ז שמופיעה בעמודה ללא כותרת מתאימה),
        # וגם תאים בודדים שצבועים ברקע שחור ידנית גם אם שאר העמודה לא צבועה
        for row in range(2, ws.max_row + 1):
            for col_idx in range(1, ws.max_column + 1):
                if col_idx in col_types:
                    continue
                cell = ws.cell(row=row, column=col_idx)
                if cell.value is None:
                    continue
                pii_type = classify_cell_content(cell.value)
                if pii_type is None and is_black_fill(cell):
                    pii_type = "GENERIC"
                if pii_type:
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
