# PyInstaller: אריזת סיכום ישיבה לתיקיית תוכנה עצמאית (לא נדרש Python במחשב היעד)
import os
import re

from PyInstaller.utils.hooks import collect_all, collect_data_files
from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                  VarFileInfo, VarStruct, VSVersionInfo)

SRC = os.path.join(SPECPATH, "..", "src")
VERSION = re.search(r'VERSION = "(.+?)"', open(os.path.join(SRC, "app.py"), encoding="utf-8").read()).group(1)
nums = (tuple(int(x) for x in VERSION.split(".")) + (0, 0, 0))[:4]

# פרטי גרסה ויצרן בקובץ ה-exe (מפחית זיהוי שגוי של אנטי-וירוס)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=nums, prodvers=nums),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "Lior Agay"),
            StringStruct("FileDescription", "Lior Agay Meeting Summarizer"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "MeetingSummary"),
            StringStruct("LegalCopyright", "Lior Agay"),
            StringStruct("OriginalFilename", "MeetingSummary.exe"),
            StringStruct("ProductName", "Meeting Summary"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

datas = [(os.path.join(SRC, "summary_prompt.txt"), ".")] + collect_data_files("docx")
binaries, hiddenimports = [], []
for pkg in ("faster_whisper", "ctranslate2", "onnxruntime", "tokenizers", "hf_xet"):
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
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MeetingSummary", console=True,
          upx=False, version=version_info)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="MeetingSummary")
