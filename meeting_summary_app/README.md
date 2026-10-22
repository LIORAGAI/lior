# סיכום ישיבה – תוכנה להתקנה ב-Windows

גוררים קובץ שמע (ואופציונלית מסמכי רקע: txt / docx / pdf) אל האייקון "סיכום ישיבה". התוכנה מתמללת את ההקלטה מקומית (מודל ivrit-ai), Claude כותב סיכום, והתוצאה נשמרת כמסמך Word (David 12, מימין לשמאל) על שולחן העבודה.

## התקנה במחשב חדש

1. מורידים את `MeetingSummary-Setup-<גרסה>.exe` (מעמוד Actions או Releases של המאגר).
2. מפעילים אותו. אין צורך בהרשאות מנהל ואין צורך להתקין Python.
3. בסוף ההתקנה משאירים מסומן "הכנה ראשונית". שלב זה מתקין את Claude Code, פותח דפדפן להתחברות לחשבון Claude, מוריד את מודל התמלול (כ-1.5GB) ומתקין האצת GPU אם יש כרטיס NVIDIA. השלב מתבצע פעם אחת בלבד.

ייתכן ש-Windows SmartScreen יציג אזהרה, מאחר שהקובץ אינו חתום דיגיטלית. במקרה כזה בוחרים "מידע נוסף" ← "הפעל בכל זאת".

## שימוש

1. גרירת קובץ שמע (ומסמכי רקע) אל האייקון שעל שולחן העבודה.
2. לחיצה ימנית על קובץ ← "שלח אל" ← "סיכום ישיבה".
3. לחיצה כפולה על האייקון פותחת חלון לבחירת קבצים.

## קבצים ונתונים

| תוכן | מיקום |
|---|---|
| התוכנה | `%LOCALAPPDATA%\Programs\MeetingSummary` |
| הנחיות הסיכום (ניתנות לעריכה; קיצור דרך בתפריט התחל) | `%LOCALAPPDATA%\MeetingSummary\summary_prompt.txt` |
| תמלולים וטיוטות | `%LOCALAPPDATA%\MeetingSummary\transcripts` |
| היסטוריית טוקנים | `%LOCALAPPDATA%\MeetingSummary\token_log.csv` |

## בניית קובץ ההתקנה

קובץ ההתקנה נבנה אוטומטית ב-GitHub Actions (`.github/workflows/build-meeting-summary.yml`) על מחשב Windows, בכל דחיפה של שינוי לתיקייה זו. הבנייה כוללת בדיקה עצמית של התוכנה הארוזה. לפרסום גרסה בעמוד Releases דוחפים תגית בפורמט `meeting-summary-v1.0.0`.

בנייה ידנית ב-Windows:

```powershell
cd meeting_summary_app
python -m pip install -r requirements.txt pyinstaller
cd packaging
python -m PyInstaller --noconfirm --distpath ..\dist --workpath ..\build MeetingSummary.spec
iscc installer.iss
```
