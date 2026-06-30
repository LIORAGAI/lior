"""הפקת סיכום מובנה מתוך תמלול, לפי פורמט קבוע, באמצעות GPT."""
import os
from openai import OpenAI

_PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "system_prompt.txt")

_STRUCTURE_NOTE = """

לצורך עיבוד אוטומטי של המסמך, פרמט את הפלט שלך כ-Markdown לפי הכללים הבאים, בנוסף לכל ההנחיות שלעיל:
- כותרת ראשית בשורה שמתחילה ב-"# " (שיחה: ...).
- שורות "תאריך:" ו"משתתפים:" כטקסט רגיל מתחת לכותרת.
- כותרות סעיפים (נושאי דיון, רקע, עמדות..., ניתוח מקצועי..., החלטות..., פעולות נדרשות, שאלות פתוחות, סוגיות לבדיקה נוספת, נספח, חתימה) בשורה שמתחילה ב-"## ".
- פריטי "פעולות נדרשות" בשורות שמתחילות ב-"- [ ] ".
- טבלת "שאלות פתוחות" כטבלת Markdown רגילה עם כותרות עמודות: אחראי | הקשר | שאלה.
- אל תוסיף הסברים מחוץ למסמך עצמו.
"""


def load_system_prompt() -> str:
    with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read() + _STRUCTURE_NOTE


def summarize_transcript(client: OpenAI, transcript: str, background: str = "", model: str = "gpt-4o") -> str:
    user_content = f"להלן תמלול של קובץ השמע:\n\n{transcript}"
    if background.strip():
        user_content += f"\n\nרקע נוסף שסופק על ידי המשתמש (לא חלק מהשיחה עצמה):\n\n{background.strip()}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
