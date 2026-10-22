# PyInstaller: אריזת סיכום ישיבה לתיקיית תוכנה עצמאית (לא נדרש Python במחשב היעד)
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files

SRC = os.path.join(SPECPATH, "..", "src")

datas = [(os.path.join(SRC, "summary_prompt.txt"), ".")] + collect_data_files("docx")
binaries, hiddenimports = [], []
for pkg in ("faster_whisper", "ctranslate2", "onnxruntime", "tokenizers"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(SRC, "app.py")],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["torch", "matplotlib", "IPython"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MeetingSummary", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="MeetingSummary")
