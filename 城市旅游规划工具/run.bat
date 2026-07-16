@echo off
chcp 65001 >nul
echo ============================================
echo  全域旅游规划助手 - 启动脚本
echo ============================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查 .env 文件
if not exist ".env" (
    echo [提示] 未找到 .env 文件，将使用 .env.example 模板
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [提示] 已复制 .env.example 为 .env，请编辑后填入真实 API Key
    )
)

REM 安装依赖（首次运行）
echo [步骤 1/2] 检查依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络或 pip 配置
    pause
    exit /b 1
)

REM 启动 Streamlit
echo [步骤 2/2] 启动 Streamlit...
echo [提示] 浏览器将自动打开 http://localhost:8501
echo [提示] 按 Ctrl+C 可停止服务
echo.
streamlit run app.py

pause