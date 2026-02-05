@echo off
echo ============================================
echo   AncientWorld Discovery Spider
echo ============================================
echo.
echo Starting Wikimedia Commons discovery...
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0\ancientgeo"
"%~dp0\.venv\Scripts\python.exe" -m scrapy crawl commons_discover

echo.
echo Discovery completed!
echo Check status: streamlit run src\ui\web\dashboard.py
pause
