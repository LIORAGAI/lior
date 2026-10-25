"""מסכם הישיבות של ליאור אגאי: קובץ שמע (ואופציונלית מסמכי רקע: txt / docx / pdf) -> תמלול -> סיכום של Claude
-> Word על שולחן העבודה + עותק ב-OneDrive + התראה לאייפון.

שימוש:
    MeetingSummary.exe <קובץ שמע> [קבצי רקע...]   עיבוד קבצים (גם בגרירה לאייקון או "שלח אל")
    MeetingSummary.exe                            פתיחת חלון לבחירת קבצים
    MeetingSummary.exe --setup                    הכנה ראשונית: Claude Code, התחברות, מודל תמלול, האצת GPU
    MeetingSummary.exe --selftest                 בדיקה עצמית של רכיבי התוכנה (ללא Claude)
"""
import csv
import ctypes
import datetime
import json
import time
from concurrent.futures import ThreadPoolExecutor
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import make_docx
import transcribe

APP_NAME = "מסכם הישיבות של ליאור אגאי"
VERSION = "2.6"
FROZEN = getattr(sys, "frozen", False)
# קבצים שמגיעים עם התוכנה (בתוכנה מותקנת: תיקיית _internal)
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
# נתוני משתמש - תיקייה שניתנת לכתיבה גם כשהתוכנה מותקנת
DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MeetingSummary"
WORK = DATA / "transcripts"  # תמלולים וטיוטות (לא על שולחן העבודה)
TOKEN_LOG = DATA / "token_log.csv"
PROMPT = DATA / "summary_prompt.txt"  # עותק שניתן לעריכה של הנחיות הסיכום
CUDA_DIR = DATA / "cuda"
NTFY_TOPIC = DATA / "ntfy_topic.txt"  # ערוץ ההתראות לאייפון (ntfy)
OLD_INSTALL = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / "LIOR MEETINGS"  # גרסאות 2.x בסקריפטים
ONEDRIVE_DIR = Path(os.environ.get("OneDrive") or Path.home() / "OneDrive") / "סיכומי ישיבות"
AUDIO_EXT = {".m4a", ".mp3", ".wav", ".ogg", ".opus", ".aac", ".flac", ".wma", ".mp4", ".webm", ".amr", ".3gp"}
CUDA_PACKAGES = [("nvidia-cublas-cu12", ""), ("nvidia-cudnn-cu12", "9.")]  # (חבילה, קידומת גרסה)

FORMAT_RULES = """
החזר את הסיכום בלבד, בפורמט Markdown פשוט לפי הכללים הבאים (הוא יומר אוטומטית ל-Word):
- "# " לכותרת המסמך, "## " לכותרת סעיף, "### " לתת-כותרת.
- "- " לתבליט, "1. " לרשימה ממוספרת, "☐ " בתחילת שורה למשימה.
- טבלאות בפורמט | עמודה | עמודה |, כשהעמודה הראשונה היא הימנית (שאלה | הקשר | אחראי).
- **טקסט** להדגשה. ללא תבליטים מקוננים, ללא קוד, ללא הקדמה או הערות לפני הסיכום או אחריו.
- התמלול נוצר אוטומטית ועלול לשבש שמות ומונחים; סמן פרטים מפוקפקים כ"נדרש אימות".

בנוסף, השורה הראשונה של הפלט (לפני הסיכום) תהיה שם לקובץ, בדיוק במבנה הזה:
שם-קובץ: <נושא הישיבה בכמה מילים> - <שמות פרטיים של המשתתפים, מופרדים בפסיק> - <תאריך DD.MM.YYYY>
- נושא: קצר וברור (עד 6 מילים).
- משתתפים: רק שמות פרטיים שזוהו בוודאות סבירה; אם לא זוהו שמות - השמט את החלק הזה.
- תאריך: תאריך הישיבה אם נאמר או ניתן להסיק משם הקובץ או מהרקע; אחרת - תאריך יצירת קובץ ההקלטה שמסרתי.
- בלי התווים / \\ : * ? " < > |
"""
FILENAME_PREFIX = "שם-קובץ:"


def init():
    # עברית בחלון הפקודה, ותיקיות עבודה
    if os.name == "nt":
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleTitleW(APP_NAME)
    for stream in (sys.stdout, sys.stderr):
        if stream:
            stream.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    WORK.mkdir(parents=True, exist_ok=True)
    if not PROMPT.exists():
        shutil.copy(BUNDLE / "summary_prompt.txt", PROMPT)
    # מעבר מגרסת הסקריפטים (2.x): ערוץ ההתראות והיסטוריית הטוקנים
    for name in ("ntfy_topic.txt", "token_log.csv"):
        old = OLD_INSTALL / name
        if old.exists() and not (DATA / name).exists():
            shutil.copy2(old, DATA / name)
    transcribe.CUDA_DIRS.append(CUDA_DIR)
    transcribe.USE_GPU = not FROZEN or any(CUDA_DIR.glob("cudnn*.dll"))


def find_claude():
    # מחפשים בכל המקומות שבהם Claude Code עשוי להיות מותקן (מתקין רשמי, npm, PATH)
    appdata = Path(os.environ.get("APPDATA", Path.home()))
    for c in (Path.home() / ".local" / "bin" / "claude.exe", shutil.which("claude.exe"), shutil.which("claude"),
              appdata / "npm" / "claude.cmd"):
        if c and Path(c).exists():
            return Path(c)
    return None


def install_claude():
    print("מתקין את Claude Code...", flush=True)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                    "irm https://claude.ai/install.ps1 | iex"])
    claude = find_claude()
    if not claude:
        sys.exit("התקנת Claude Code נכשלה. בדוק את החיבור לאינטרנט והפעל שוב את 'הכנה ראשונית'.")
    return claude


def claude_logged_in(claude):
    r = subprocess.run([str(claude), "auth", "status"], capture_output=True, encoding="utf-8")
    return r.returncode == 0


def ensure_login():
    claude = find_claude() or install_claude()
    if claude_logged_in(claude):
        return claude
    print("\nClaude לא מחובר. נפתח דפדפן להתחברות - התחבר לחשבון שלך ואז חזור לחלון הזה.\n", flush=True)
    subprocess.run([str(claude), "auth", "login"])
    if not claude_logged_in(claude):
        sys.exit("ההתחברות ל-Claude לא הושלמה. נסה שוב.")
    print("Claude מחובר.\n", flush=True)
    return claude


def desktop_dir():
    # הנתיב האמיתי של שולחן העבודה (גם כש-OneDrive מעביר אותו למקום אחר)
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf)  # CSIDL_DESKTOPDIRECTORY
    return Path(buf.value)


def free_path(path):
    # אם קובץ באותו שם כבר קיים (למשל פתוח ב-Word) - מוסיפים מספר
    n = 2
    candidate = path
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        n += 1
    return candidate


def has_nvidia():
    return shutil.which("nvidia-smi") is not None


def install_cuda():
    # מורידים את חבילות ה-CUDA (קבצי wheel = zip) מ-PyPI ומחלצים רק את קובצי ה-DLL
    for name, prefix in CUDA_PACKAGES:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json") as r:
            releases = json.load(r)["releases"]
        versions = sorted((v for v in releases if v.startswith(prefix) and v.replace(".", "").isdigit()),
                          key=lambda v: [int(x) for x in v.split(".")], reverse=True)
        url = next((f["url"] for v in versions for f in releases[v] if f["filename"].endswith("win_amd64.whl")), None)
        if not url:
            raise RuntimeError(f"לא נמצאה חבילת {name} ל-Windows")
        whl = CUDA_DIR / "download.whl"
        CUDA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"מוריד {name}...", flush=True)
        with urllib.request.urlopen(url) as r, open(whl, "wb") as f:
            total, done = int(r.headers.get("Content-Length", 0)), 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r{100 * done / total:5.1f}%", end="", flush=True)
        print(flush=True)
        with zipfile.ZipFile(whl) as z:
            for member in z.namelist():
                if member.lower().endswith(".dll"):
                    (CUDA_DIR / Path(member).name).write_bytes(z.read(member))
        whl.unlink()


def setup():
    print(f"=== {APP_NAME} - גרסה {VERSION} - הכנה ראשונית ===", flush=True)
    print("כל רכיב שלא נמצא במחשב (בכל מיקום) מותקן מחדש.", flush=True)
    print("\n1/4 Claude Code", flush=True)
    if find_claude():
        print(f"Claude Code נמצא: {find_claude()}", flush=True)
    ensure_login()

    print("\n2/4 האצת GPU", flush=True)
    if not has_nvidia():
        print("לא נמצא כרטיס NVIDIA - התמלול ירוץ על המעבד (איטי יותר)", flush=True)
    elif any(CUDA_DIR.glob("cudnn*.dll")):
        print("האצת GPU כבר מותקנת", flush=True)
    else:
        print("נמצא כרטיס מסך NVIDIA - מתקין האצת GPU (כ-1GB, פעם אחת)", flush=True)
        try:
            install_cuda()
            transcribe.USE_GPU = True
        except Exception as e:
            print(f"התקנת האצת GPU נכשלה ({e}) - התמלול ירוץ על המעבד", flush=True)

    print("\n3/4 מודל התמלול לעברית", flush=True)
    transcribe.add_cuda_dlls()
    _, device = transcribe.load_model()
    print(f"המודל מוכן, ירוץ על {device}", flush=True)

    print("\n4/4 התראות לאייפון (ntfy)", flush=True)
    if NTFY_TOPIC.exists():
        print(f"ערוץ ההתראות: {NTFY_TOPIC.read_text(encoding='utf-8').strip()}", flush=True)
    else:
        topic = input("הקלד את שם ערוץ ה-ntfy (מהקובץ ntfy_topic.txt), או Enter לדילוג: ").strip()
        if topic:
            NTFY_TOPIC.write_text(topic, encoding="utf-8")
            print("נשמר. באייפון: אפליקציית ntfy > + > שם הערוץ.", flush=True)
        else:
            print("ללא התראות לאייפון (אפשר להוסיף בהפעלה חוזרת של 'הכנה ראשונית').", flush=True)
    print("\nההכנה הסתיימה. אפשר לגרור קבצי שמע לאייקון 'סיכום ישיבה' שעל שולחן העבודה.", flush=True)


def selftest():
    # בדיקה שכל הרכיבים נארזו נכון: Word, PDF, פענוח שמע, VAD ותמלול עם מודל קטן
    import math
    import struct
    import wave

    import pypdf  # noqa: F401
    from faster_whisper import WhisperModel

    md = WORK / "selftest.md"
    md.write_text("# בדיקה\n## סעיף\n- תבליט\n1. מספור\n☐ משימה\n| שאלה | הקשר | אחראי |\n|---|---|---|\n| א | ב | ג |\n**מודגש**\n",
                  encoding="utf-8")
    make_docx.main(md, WORK / "selftest.docx")

    wav = WORK / "selftest.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / 16000)))
                               for i in range(32000)))
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(wav), vad_filter=True)
    list(segments)
    print(f"selftest OK: duration={info.duration:.1f}s, prompt={len(PROMPT.read_text(encoding='utf-8'))} chars", flush=True)


def read_background(path):
    ext = path.suffix.lower()
    if ext == ".pdf":
        import pypdf
        return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
    if ext == ".docx":
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    return path.read_text(encoding="utf-8", errors="ignore")


def notify_phone(doc_name):
    # התראה לאייפון דרך ntfy, עם שם קובץ הסיכום (בלי תוכן הסיכום)
    if not NTFY_TOPIC.exists():
        return
    body = json.dumps({
        "topic": NTFY_TOPIC.read_text(encoding="utf-8").strip(),
        "title": "מסכם הישיבות",
        "message": f"סיכום ישיבה חדש מוכן ב-OneDrive:\n{doc_name}",
    }).encode("utf-8")
    try:
        req = urllib.request.Request("https://ntfy.sh/", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).close()
        print("נשלחה התראה לאייפון", flush=True)
    except Exception as e:
        print(f"שליחת ההתראה לאייפון נכשלה: {e}", flush=True)


def recording_date(audio):
    # הוותיק מבין תאריך היצירה והשינוי (בהעתקה, תאריך היצירה הוא מועד ההעתקה)
    st = audio.stat()
    return datetime.datetime.fromtimestamp(min(st.st_ctime, st.st_mtime)).strftime("%d.%m.%Y")


def split_filename(summary, audio):
    """מפריד את שורת שם-הקובץ מהסיכום. מחזיר (שם קובץ נקי, סיכום)."""
    lines = summary.splitlines()
    for i, line in enumerate(lines[:3]):
        clean = line.strip().strip("*").strip()
        if clean.startswith(FILENAME_PREFIX):
            break
    else:
        return f"{audio.stem} - {recording_date(audio)}", summary
    rest = "\n".join(lines[:i] + lines[i + 1:])
    name = clean[len(FILENAME_PREFIX):]
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .-")[:120].strip(" .-")
    return (name or f"{audio.stem} - {recording_date(audio)}"), rest.lstrip("\n")


def summarize(claude, audio, transcript, background):
    """מחזיר (טקסט הסיכום, מילון שימוש בטוקנים)."""
    rules = PROMPT.read_text(encoding="utf-8")
    prompt = (f"{rules}\n{FORMAT_RULES}\nשם קובץ ההקלטה: {audio.name}\n"
              f"תאריך יצירת קובץ ההקלטה: {recording_date(audio)}\n")
    for name, text in background:
        prompt += f"\n<רקע קובץ='{name}'>\n{text}\n</רקע>\n"
    prompt += f"\n<תמלול>\n{transcript.read_text(encoding='utf-8')}\n</תמלול>\n"

    res = subprocess.run(
        [str(claude), "-p", "--output-format", "json"],
        input=prompt, capture_output=True, encoding="utf-8", cwd=DATA,
    )
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Claude נכשל: {res.stderr or res.stdout}")
    if data.get("is_error") or not data.get("result", "").strip():
        raise RuntimeError(f"Claude נכשל: {data.get('result')}")

    u = data.get("usage", {})
    usage = {
        "input": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0),
        "output": u.get("output_tokens", 0),
        "cost_usd": data.get("total_cost_usd", 0),
    }
    usage["total"] = usage["input"] + usage["output"]
    return data["result"].strip(), usage


def log_tokens(name, usage):
    new = not TOKEN_LOG.exists()
    with open(TOKEN_LOG, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["תאריך", "קובץ", "טוקני קלט", "טוקני פלט", "סה\"כ טוקנים", "עלות משוערת ($)"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), name,
                    usage["input"], usage["output"], usage["total"], f"{usage['cost_usd']:.4f}"])


def finish(claude, audio, transcript, background):
    # סיכום ב-Claude ושמירה. רץ ברקע, כך שהתמלול של הקובץ הבא מתחיל בינתיים
    start = time.time()
    summary, usage = summarize(claude, audio, transcript, background)
    usage["claude_sec"] = time.time() - start
    doc_name, summary = split_filename(summary, audio)
    md = WORK / (audio.stem + ".summary.md")
    md.write_text(summary, encoding="utf-8")
    out = free_path(desktop_dir() / (doc_name + ".docx"))
    make_docx.main(md, out)
    log_tokens(audio.name, usage)
    print(f"\n[{audio.name}] הסיכום נשמר בשולחן העבודה: {out.name}", flush=True)
    try:
        ONEDRIVE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out, free_path(ONEDRIVE_DIR / out.name))
        print(f"עותק נשמר ב-OneDrive: {ONEDRIVE_DIR}", flush=True)
        notify_phone(out.name)
    except Exception as e:
        print(f"שמירת העותק ב-OneDrive נכשלה: {e}", flush=True)
    os.startfile(out)
    return usage


def pick_files():
    # הפעלה בלחיצה כפולה (בלי קבצים) - חלון בחירה
    from tkinter import Tk, filedialog
    root = Tk()
    root.withdraw()
    audio_types = " ".join("*" + e for e in sorted(AUDIO_EXT))
    files = filedialog.askopenfilenames(
        title="בחר קובץ שמע (ואופציונלית מסמכי רקע: txt / docx / pdf)",
        filetypes=[("שמע ומסמכי רקע", audio_types + " *.txt *.docx *.pdf"), ("כל הקבצים", "*.*")])
    root.destroy()
    return [Path(f) for f in files]


def run(files):
    audios = [f for f in files if f.suffix.lower() in AUDIO_EXT]
    background = [(f.name, read_background(f)) for f in files if f not in audios]
    if not audios:
        sys.exit("לא נמצא קובץ שמע. גרור קובץ שמע (m4a, mp3, wav...) אל האייקון.")

    claude = ensure_login()
    jobs = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        for audio in audios:
            print(f"\n=== {audio.name} ===", flush=True)
            try:
                start = time.time()
                transcript = transcribe.transcribe(audio, WORK)
                job = pool.submit(finish, claude, audio, transcript, background)
                jobs.append((audio.name, time.time() - start, job))
                print("Claude כותב את הסיכום ברקע...", flush=True)
            except Exception as e:
                print(f"\nשגיאה בתמלול {audio.name}: {e}", flush=True)
                jobs.append((audio.name, 0, None))
    results = []
    for name, transcribe_sec, job in jobs:
        try:
            usage = job.result() if job else None
            if usage:
                usage["transcribe_sec"] = transcribe_sec
            results.append((name, usage))
        except Exception as e:
            print(f"\nשגיאה בעיבוד {name}: {e}", flush=True)
            results.append((name, None))

    print("\n================ סיכום הרצה ================", flush=True)
    for name, usage in results:
        if usage:
            print(f"{name}: {usage['total']:,} טוקנים (קלט {usage['input']:,}, פלט {usage['output']:,})"
                  f", עלות משוערת ${usage['cost_usd']:.4f}", flush=True)
            print(f"   זמן: תמלול {transcribe.fmt(usage['transcribe_sec'])}, Claude {transcribe.fmt(usage['claude_sec'])}",
                  flush=True)
        else:
            print(f"{name}: נכשל", flush=True)
    print(f"היסטוריית טוקנים: {TOKEN_LOG}", flush=True)


def main():
    init()
    args = sys.argv[1:]
    if args == ["--selftest"]:
        return selftest()
    if args == ["--version"]:
        return print(VERSION)
    try:
        if args == ["--setup"]:
            setup()
        else:
            files = [Path(f) for f in args] or pick_files()
            if files:
                run(files)
    except SystemExit as e:
        if e.code not in (None, 0):
            print(f"\n{e.code}", flush=True)
    except Exception as e:
        print(f"\nשגיאה: {e}", flush=True)
    if FROZEN:
        input("\nלחץ Enter לסגירת החלון...")


if __name__ == "__main__":
    main()
