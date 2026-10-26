"""שליחת שם סיכום חדש במייל (כותרת בלבד, בלי קובץ) מחשבון Gmail אל עצמו.

הכתובת וסיסמת האפליקציה של Gmail נשמרות רק במחשב, והסיסמה מוצפנת בהצפנת Windows (DPAPI)
של המשתמש הנוכחי - כך שגם מי שמעתיק את הקובץ למחשב אחר לא יכול לקרוא אותה.
"""
import base64
import ctypes
import json
import os
import smtplib
import ssl
from ctypes import wintypes
from email.message import EmailMessage

import app

CONFIG = app.DATA / "email.json"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data, protect):
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in, blob_out = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), _Blob()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def protect(data):
    return _dpapi(data, True)


def unprotect(data):
    return _dpapi(data, False)


def load():
    if not CONFIG.exists():
        return None
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    return cfg["address"], unprotect(base64.b64decode(cfg["password"])).decode("utf-8")


def send_subject(subject):
    """שולח מייל שכל תוכנו הוא הכותרת. מחזיר True אם נשלח."""
    cfg = load()
    if not cfg:
        return False
    address, password = cfg
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, address, address
    msg.set_content("")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=30) as s:
        s.login(address, password)
        s.send_message(msg)
    return True


def configure():
    # שלב בהכנה הראשונית: כתובת Gmail + סיסמת אפליקציה, עם בדיקת התחברות
    if CONFIG.exists():
        print(f"מייל מוגדר: {json.loads(CONFIG.read_text(encoding='utf-8'))['address']}", flush=True)
        if input("להגדיר מחדש? (כ/ל): ").strip() not in ("כ", "y", "Y"):
            return
    address = input("כתובת Gmail שאליה יישלח שם כל סיכום חדש (Enter לדילוג): ").strip()
    if not address:
        print("ללא מייל.", flush=True)
        return
    print("נדרשת 'סיסמת אפליקציה' של Gmail (16 תווים) - לא הסיסמה הרגילה.\n"
          "יוצרים אותה בכתובת https://myaccount.google.com/apppasswords (נדרש אימות דו-שלבי בחשבון).", flush=True)
    password = input("סיסמת האפליקציה: ").replace(" ", "").strip()
    if os.name == "nt":
        os.system("cls")  # לא להשאיר את הסיסמה על המסך
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=30) as s:
            s.login(address, password)
    except Exception as e:
        print(f"ההתחברות ל-Gmail נכשלה ({e}). המייל לא הוגדר; אפשר לנסות שוב ב'הכנה ראשונית'.", flush=True)
        return
    CONFIG.write_text(json.dumps({"address": address,
                                  "password": base64.b64encode(protect(password.encode("utf-8"))).decode()}),
                      encoding="utf-8")
    print(f"המייל הוגדר: {address}", flush=True)
