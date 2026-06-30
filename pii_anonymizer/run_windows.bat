@echo off
cd /d "%~dp0"
echo מתקין דרישות (פעם ראשונה זה ייקח כמה דקות, בפעמים הבאות יהיה מהיר)...
python -m pip install -r ../requirements.txt
echo מפעיל את התוכנה...
python -m streamlit run streamlit_app.py
pause
