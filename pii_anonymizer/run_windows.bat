@echo off
cd /d "%~dp0"
echo מתקין דרישות (פעם ראשונה זה ייקח כמה דקות)...
pip install -r ../requirements.txt
echo מפעיל את התוכנה...
streamlit run streamlit_app.py
pause
