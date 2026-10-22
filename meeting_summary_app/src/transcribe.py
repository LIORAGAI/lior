"""תמלול קובץ שמע בעברית עם מודל ivrit-ai (חינמי, מקומי).

שימוש:  python transcribe.py <קובץ שמע> [תיקיית פלט]
פלט:    <שם הקובץ>.txt עם חותמות זמן
"""
import os
import sys
import time
import site
from pathlib import Path

MODEL = "ivrit-ai/whisper-large-v3-turbo-ct2"
CUDA_DIRS = []  # תיקיות נוספות עם DLL של CUDA (נקבע ע"י app.py)
USE_GPU = True  # app.py מכבה כשספריות CUDA לא הותקנו, כדי לא לקרוס באמצע תמלול


def add_cuda_dlls(extra_dirs=CUDA_DIRS):
    # ספריות CUDA (nvidia-cublas / nvidia-cudnn) צריכות להיות ב-PATH ב-Windows.
    # מחפשים ב-site-packages (הרצה מקוד מקור) ובתיקיות נוספות (תוכנה מותקנת).
    roots = [Path(sp) / "nvidia" for sp in site.getsitepackages() + [site.getusersitepackages()]]
    roots += [Path(d) for d in extra_dirs]
    for nv in roots:
        if nv.is_dir():
            for bin_dir in [nv, *nv.glob("*/bin")]:
                if any(bin_dir.glob("*.dll")):
                    os.add_dll_directory(str(bin_dir))
                    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]


def load_model():
    from faster_whisper import WhisperModel
    if not USE_GPU:
        return WhisperModel(MODEL, device="cpu", compute_type="int8"), "CPU"
    try:
        return WhisperModel(MODEL, device="cuda", compute_type="float16"), "GPU"
    except Exception as e:
        print(f"GPU לא זמין ({e}), עובר ל-CPU (איטי יותר)", flush=True)
        return WhisperModel(MODEL, device="cpu", compute_type="int8"), "CPU"


def fmt(t):
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def transcribe(audio, out_dir):
    audio, out_dir = Path(audio), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (audio.stem + ".txt")

    add_cuda_dlls()
    model, device = load_model()
    start = time.time()
    segments, info = model.transcribe(
        str(audio), language="he", vad_filter=True, beam_size=5
    )
    print(f"מתמלל על {device}, אורך הקלטה {fmt(info.duration)}", flush=True)

    with open(out, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"[{fmt(seg.start)}] {seg.text.strip()}\n")
            f.flush()
            pct = 100 * seg.end / info.duration if info.duration else 0
            print(f"\r{pct:5.1f}%", end="", flush=True)

    print(f"\nהסתיים תוך {fmt(time.time() - start)} -> {out}", flush=True)
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "transcripts"
    transcribe(sys.argv[1], out_dir)


if __name__ == "__main__":
    main()
