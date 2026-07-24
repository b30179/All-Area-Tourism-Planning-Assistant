@echo off
REM ============================================================
REM 全域旅游规划助手 - 一键启动脚本
REM 启动后浏览器自动打开 http://localhost:8501
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   全域旅游规划助手 启动中...
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python ^>= 3.10
    pause
    exit /b 1
)

REM 检查依赖
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 正在安装依赖...
    pip install -r requirements.txt -q
    echo.
)

REM 检查 .env
if not exist ".env" (
    echo [提示] 未找到 .env，从 .env.example 复制...
    copy .env.example .env
    echo [提示] 请编辑 .env 填入你的 API Key 后重新运行
    start notepad .env
    pause
    exit /b 1
)

echo [启动] Streamlit 应用...
echo [地址] http://localhost:8501
echo [提示] 按 Ctrl+C 停止服务
echo.

streamlit run app.py --server.headless true
pause
