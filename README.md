# סיכום שיחות מקבצי שמע

CLI שמתמלל קובץ שמע (OpenAI Whisper) ומפיק ממנו מסמך סיכום מובנה בעברית (GPT), בפורמט Word עם יישור RTL וגופן David.

## התקנה

```bash
pip install -r requirements.txt
```

לקבצים גדולים מ-25MB נדרש גם `ffmpeg` מותקן במערכת (לצורך פיצול הקובץ עם pydub).

## הגדרת מפתח API

```bash
export OPENAI_API_KEY="sk-..."
```

או צרו קובץ `.env` עם השורה:

```
OPENAI_API_KEY=sk-...
```

## שימוש

```bash
python audio_summary/main.py --audio meeting.mp3
```

עם רקע נוסף:

```bash
python audio_summary/main.py --audio meeting.mp3 --background "פגישה עם עו״ד בנושא חוזה שכירות"
# או
python audio_summary/main.py --audio meeting.mp3 --background-file notes.txt
```

קביעת נתיב פלט ושמירת התמלול הגולמי:

```bash
python audio_summary/main.py --audio meeting.mp3 --out summary.docx --keep-transcript
```
