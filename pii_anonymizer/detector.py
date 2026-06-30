"""זיהוי עמודות ותאים שעשויים להכיל מידע מזהה (PII) בקובץ אקסל."""
import re

# מילות מפתח בכותרות עמודות שמעידות על תוכן מזהה, לפי סוג
COLUMN_KEYWORDS = {
    "ID": ["ת.ז", "תז", "תעודת זהות", "מספר זהות", "ת\"ז", "id number", "national id", "ssn"],
    "COMPANY_ID": ["ח.פ", "חפ", "ח\"פ", "מספר עוסק", "עוסק מורשה", "עוסק פטור", "מספר חברה",
                   "company number", "business id", "vat number"],
    "NAME": ["שם פרטי", "שם משפחה", "שם מלא", "שם לקוח", "שם פרטי ומשפחה", "full name",
             "first name", "last name", "customer name"],
    "COMPANY_NAME": ["שם חברה", "שם עסק", "שם ספק", "company name", "business name", "vendor name"],
    "PHONE": ["טלפון", "נייד", "פלאפון", "phone", "mobile", "cell"],
    "EMAIL": ["מייל", "אימייל", "דוא\"ל", "email", "e-mail"],
    "ADDRESS": ["כתובת", "רחוב", "עיר מגורים", "address", "street"],
}

# ביטויים רגולריים לזיהוי תוכן מזהה בתוך תא, ללא תלות בכותרת העמודה
CONTENT_PATTERNS = {
    "PHONE": re.compile(r"^0\d{1,2}-?\d{6,7}$|^\+972-?\d{8,9}$"),
    "EMAIL": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "ID_OR_COMPANY": re.compile(r"^\d{8,9}$"),  # ת.ז / ח.פ / עוסק מורשה - 8-9 ספרות
}


def israeli_id_checksum_valid(value: str) -> bool:
    """בודק ספרת ביקורת תקנית של תעודת זהות ישראלית (9 ספרות)."""
    digits = value.strip()
    if not digits.isdigit() or len(digits) > 9:
        return False
    digits = digits.zfill(9)
    total = 0
    for i, ch in enumerate(digits):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        total += d if d < 10 else d - 9
    return total % 10 == 0


def match_column_keyword(column_name: str):
    """מחזיר את סוג ה-PII אם שם העמודה תואם מילת מפתח ידועה, אחרת None."""
    name = str(column_name).strip().lower()
    for pii_type, keywords in COLUMN_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return pii_type
    return None


def has_force_encode_keyword(column_name) -> bool:
    """בודק אם כותרת העמודה מכילה את מילת המפתח "תקודד" - סימון ידני של המשתמש
    שיש להצפין את העמודה הזו אוטומטית גם אם לא זוהתה אוטומטית."""
    if column_name is None:
        return False
    return "תקודד" in str(column_name)


def classify_cell_content(value) -> str | None:
    """מנסה לזהות סוג PII לפי תוכן התא בלבד (ללא תלות בכותרת)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if CONTENT_PATTERNS["EMAIL"].match(text):
        return "EMAIL"
    if CONTENT_PATTERNS["PHONE"].match(text):
        return "PHONE"
    if CONTENT_PATTERNS["ID_OR_COMPANY"].match(text) and israeli_id_checksum_valid(text):
        return "ID"
    return None
