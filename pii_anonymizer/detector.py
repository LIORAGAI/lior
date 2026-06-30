"""זיהוי עמודות שיש להצפין בקובץ אקסל, לפי סימון ידני בכותרת."""


def has_force_encode_keyword(column_name) -> bool:
    """בודק אם כותרת העמודה מכילה את מילת המפתח "תקודד" (עם או בלי מרכאות) -
    סימון ידני של המשתמש שיש להצפין את כל העמודה הזו."""
    if column_name is None:
        return False
    return "תקודד" in str(column_name)
