"""זיהוי עמודות שיש להצפין בקובץ אקסל, לפי סימון ידני בכותרת."""
import re

# המילה "תקודד" עטופה במרכאות (רגילות או מעוצבות), עם רווחים אופציונליים סביבה
_QUOTED_KEYWORD_RE = re.compile(r'\s*["“”״]תקודד["“”״]\s*')


def has_force_encode_keyword(column_name) -> bool:
    """בודק אם כותרת העמודה מכילה את מילת המפתח "תקודד" (עם או בלי מרכאות) -
    סימון ידני של המשתמש שיש להצפין את כל העמודה הזו."""
    if column_name is None:
        return False
    return "תקודד" in str(column_name)


def strip_quoted_force_encode_keyword(column_name):
    """אם הכותרת מכילה את המילה "תקודד" בתוך מרכאות, מחזיר את הכותרת בלי המילה
    (ובלי המרכאות סביבה). אם אין התאמה במרכאות, מחזיר את הכותרת המקורית."""
    if column_name is None:
        return column_name
    text = str(column_name)
    cleaned = _QUOTED_KEYWORD_RE.sub(" ", text).strip()
    return cleaned if cleaned else text


def _is_black(color) -> bool:
    return color is not None and color.type == "rgb" and isinstance(color.rgb, str) \
        and color.rgb.upper().endswith("000000")


def _is_white(color) -> bool:
    return color is not None and color.type == "rgb" and isinstance(color.rgb, str) \
        and color.rgb.upper().endswith("FFFFFF")


def is_black_fill_white_font(cell) -> bool:
    """בודק אם לתא כותרת יש מילוי רקע שחור וגופן בצבע לבן - סימון ידני של המשתמש
    שיש להצפין את כל העמודה שמתחת לכותרת הזו."""
    fill = cell.fill
    if fill is None or fill.fill_type != "solid" or not _is_black(fill.fgColor):
        return False
    font = cell.font
    return font is not None and _is_white(font.color)
