@echo off
echo ============================================
echo   AncientWorld GUI Dashboard
echo ============================================
echo.
echo Starting Streamlit dashboard...
echo Will open in browser at http://localhost:8501
echo.

cd /d "%~dp0"
"%~dp0\.venv\Scripts\python.exe" -m streamlit run src\ui\web\dashboard.py

pause
