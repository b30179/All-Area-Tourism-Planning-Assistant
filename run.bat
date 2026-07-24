@echo off
cd /d "%~dp0"

echo ============================================================
echo   QuanYu Tourism Planner - Starting...
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt -q
    echo.
)

if not exist .env (
    echo [INFO] .env not found, copied from .env.example
    copy .env.example .env >nul
    echo [INFO] Please edit .env with your API Key, then re-run
    start notepad .env
    pause
    exit /b 1
)

echo [START] Launching Streamlit...
echo [URL]   http://localhost:8501
echo.
python -m streamlit run app.py
pause
