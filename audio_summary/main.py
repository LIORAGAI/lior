#!/usr/bin/env python3
"""CLI להפקת סיכום שיחה מקובץ שמע.

שימוש:
    python main.py --audio path/to/file.mp3 [--background "טקסט רקע" | --background-file notes.txt] [--out summary.docx]

דורש משתנה סביבה OPENAI_API_KEY.
"""
import argparse
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transcribe import transcribe_audio
from summarize import summarize_transcript
from docx_builder import build_docx


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="הפקת סיכום שיחה מקובץ שמע")
    parser.add_argument("--audio", required=True, help="נתיב לקובץ השמע")
    parser.add_argument("--background", default="", help="טקסט רקע חופשי")
    parser.add_argument("--background-file", default="", help="נתיב לקובץ טקסט עם רקע נוסף")
    parser.add_argument("--out", default="", help="נתיב לקובץ הפלט (docx)")
    parser.add_argument("--model", default="gpt-4o", help="מודל GPT לסיכום")
    parser.add_argument("--language", default="he", help="קוד שפת השמע לתמלול")
    parser.add_argument("--keep-transcript", action="store_true", help="שמור גם את התמלול הגולמי לקובץ txt")
    args = parser.parse_args()

    if not os.path.isfile(args.audio):
        print(f"שגיאה: הקובץ {args.audio} לא נמצא", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("שגיאה: יש להגדיר משתנה סביבה OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    background = args.background
    if args.background_file:
        if not os.path.isfile(args.background_file):
            print(f"שגיאה: קובץ הרקע {args.background_file} לא נמצא", file=sys.stderr)
            sys.exit(1)
        with open(args.background_file, "r", encoding="utf-8") as f:
            background = (background + "\n" + f.read()).strip()

    print("מתמלל את קובץ השמע...")
    transcript = transcribe_audio(client, args.audio, language=args.language)

    base_name = os.path.splitext(os.path.basename(args.audio))[0]
    out_path = args.out or f"{base_name}_summary.docx"

    if args.keep_transcript:
        transcript_path = f"{base_name}_transcript.txt"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"התמלול הגולמי נשמר ב: {transcript_path}")

    print("מפיק סיכום...")
    summary_md = summarize_transcript(client, transcript, background=background, model=args.model)

    print("בונה מסמך Word...")
    build_docx(summary_md, out_path)

    print(f"הסיכום נשמר ב: {out_path}")


if __name__ == "__main__":
    main()
