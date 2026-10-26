"""מצב מעקב: קבצי שמע שמועלים לתיקייה ב-OneDrive מסוכמים אוטומטית, לפי אותם כללים כמו בגרירה לאייקון.

משימה מתוזמנת של Windows מפעילה כל חצי שעה, בין 08:00 ל-22:00, את MeetingSummaryWatch.exe --watch (בלי חלון).
כל הרצה בודקת את התיקייה פעם אחת ומסתיימת. רק הקלטה חדשה מסוכמת; הקלטה שכבר סוכמה (לפי תוכן הקובץ)
לא מסוכמת שוב. אחרי הסיכום, או כשההקלטה כבר סוכמה, קובץ השמע עובר לתת-תיקייה "קבצים שנמחקו".
קובץ שנכשל עובר ל"נכשלו". על כל סיכום חדש נשלח מייל אחד שכותרתו שם הסיכום.
"""
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path
from xml.sax.saxutils import escape

import app
import mailer
import transcribe

WATCH_DIR = app.ONEDRIVE_DIR / "הקלטות לסיכום"
DONE_DIR = WATCH_DIR / "קבצים שנמחקו"
OLD_DONE_DIR = WATCH_DIR / "עובדו"  # גרסה 2.7
FAILED_DIR = WATCH_DIR / "נכשלו"
LOG = app.DATA / "watch.log"
LOCK = app.DATA / "watch.lock"
LOGIN_ALERT = app.DATA / "login_alert"  # מונע התראה חוזרת כל כמה דקות כש-Claude לא מחובר
TASK_NAME = "MeetingSummary OneDrive Watch"
FIRST_RUN, INTERVAL, WINDOW = "08:00:00", "PT30M", "PT14H1M"  # כל חצי שעה מ-08:00 עד 22:00 (כולל)
BACKGROUND_EXT = {".txt", ".docx", ".pdf"}


def log(msg):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def open_log():
    # בלי חלון אין לאן להדפיס - הכול נכתב ליומן (שמתחיל מחדש כשהוא גדל)
    if LOG.exists() and LOG.stat().st_size > 2_000_000:
        LOG.replace(LOG.with_suffix(".old.log"))
    sys.stdout = sys.stderr = open(LOG, "a", encoding="utf-8", buffering=1)


def take_lock():
    # הרצה אחת בכל פעם; נעילה ישנה (הרצה שקרסה) משתחררת אחרי 12 שעות
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime > 12 * 3600:
        LOCK.unlink()
    try:
        os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL))
        return True
    except FileExistsError:
        return False


def ready_files():
    """קבצי שמע שהעלאתם הסתיימה (הגודל לא משתנה במשך 15 שניות)."""
    audios = [f for f in WATCH_DIR.iterdir() if f.is_file() and f.suffix.lower() in app.AUDIO_EXT]
    if not audios:
        return []
    sizes = {f: f.stat().st_size for f in audios}
    time.sleep(15)
    return sorted((f for f in audios if f.exists() and f.stat().st_size == sizes[f] > 0),
                  key=lambda f: f.stat().st_mtime)


def background_for(audio):
    # מסמכי רקע באותו שם כמו ההקלטה (למשל "ישיבה.m4a" + "ישיבה.pdf")
    return [f for f in WATCH_DIR.iterdir() if f.is_file() and f.stem == audio.stem and f.suffix.lower() in BACKGROUND_EXT]


def move(files, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.exists():
            f.replace(app.free_path(folder / f.name))


def claude_ready():
    claude = app.find_claude() or app.install_claude()
    if app.claude_logged_in(claude):
        LOGIN_ALERT.unlink(missing_ok=True)
        return claude
    log("Claude לא מחובר - ההקלטות ממתינות בתיקייה")
    if not LOGIN_ALERT.exists() or time.time() - LOGIN_ALERT.stat().st_mtime > 12 * 3600:
        app.notify("Claude לא מחובר במחשב. הקלטות ממתינות לסיכום.\nבמחשב: תפריט התחל > הכנה ראשונית.")
        LOGIN_ALERT.touch()
    return None


def migrate_old_done():
    # גרסה 2.7 העבירה הקלטות שסוכמו ל"עובדו": רושמים אותן כמסוכמות ומעבירים ל"קבצים שנמחקו"
    if not OLD_DONE_DIR.is_dir():
        return
    for f in OLD_DONE_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in app.AUDIO_EXT and not app.already_done(f):
            app.remember(f, "(סוכם בגרסה 2.7)")
        move([f], DONE_DIR)
    if not any(OLD_DONE_DIR.iterdir()):
        OLD_DONE_DIR.rmdir()


def send_email(doc_name):
    try:
        if mailer.send_subject(Path(doc_name).stem):
            log(f"נשלח מייל: {Path(doc_name).stem}")
    except Exception as e:
        log(f"שליחת המייל נכשלה: {e}")


def check_folder():
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    migrate_old_done()
    audios = ready_files()
    if not audios:
        return
    log(f"נמצאו {len(audios)} הקלטות: {', '.join(f.name for f in audios)}")
    new = []
    for audio in audios:
        if app.already_done(audio):
            log(f"כבר סוכם - לא מסוכם שוב: {audio.name}")
            move([audio, *background_for(audio)], DONE_DIR)
        else:
            new.append(audio)
    if not new:
        return
    claude = claude_ready()
    if not claude:
        return
    for audio in new:
        bg_files = background_for(audio)
        try:
            background = [(f.name, app.read_background(f)) for f in bg_files]
            usage = app.process(claude, audio, background)
            move([audio, *bg_files], DONE_DIR)
            log(f"הסתיים: {audio.name} ({usage['total']:,} טוקנים, ${usage['cost_usd']:.4f})")
            send_email(usage["doc"])
        except Exception as e:
            log(f"שגיאה בעיבוד {audio.name}: {e}")
            move([audio, *bg_files], FAILED_DIR)
            app.notify(f"סיכום ההקלטה נכשל:\n{audio.name}\nהקובץ הועבר לתיקייה 'נכשלו'. להרצה חוזרת - מעבירים אותו חזרה.")


def task_xml(exe):
    start = f"{datetime.date.today().isoformat()}T{FIRST_RUN}"
    user = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}".lstrip("\\")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>מסכם הישיבות: סיכום אוטומטי של הקלטות מתיקיית OneDrive</Description></RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition><Interval>{INTERVAL}</Interval><Duration>{WINDOW}</Duration><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author"><UserId>{escape(user)}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT12H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>"{escape(str(exe))}"</Command><Arguments>--watch</Arguments></Exec>
  </Actions>
</Task>
"""


def install_task():
    exe = Path(sys.executable).with_name("MeetingSummaryWatch.exe")
    xml = app.DATA / "watch_task.xml"
    xml.write_text(task_xml(exe), encoding="utf-16")
    r = subprocess.run(["schtasks", "/Create", "/F", "/TN", TASK_NAME, "/XML", str(xml)],
                       capture_output=True, text=True, creationflags=app.NO_WINDOW)
    print(r.stdout or r.stderr, flush=True)
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    LOG.touch()
    return r.returncode


def remove_task():
    r = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME],
                       capture_output=True, text=True, creationflags=app.NO_WINDOW)
    print(r.stdout or r.stderr, flush=True)
    return 0  # משימה שלא קיימת אינה שגיאה


def main(mode):
    if mode == "--install-watch":
        sys.exit(install_task())
    if mode == "--remove-watch":
        sys.exit(remove_task())
    if mode == "--open-watch":
        WATCH_DIR.mkdir(parents=True, exist_ok=True)
        return os.startfile(WATCH_DIR)

    app.QUIET = True
    transcribe.SHOW_PROGRESS = False
    open_log()
    if not take_lock():
        return
    try:
        check_folder()
    except (Exception, SystemExit) as e:
        log(f"שגיאה: {e}")
    finally:
        LOCK.unlink(missing_ok=True)
