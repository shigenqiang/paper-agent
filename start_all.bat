@echo off
chcp 65001 > nul
echo =====================================
echo     论文Agent 完整启动
echo =====================================
echo.
echo 此脚本将同时启动：
echo   1. API服务 (端口8000)
echo   2. Web界面 (端口8501)
echo.
echo 启动后请访问: http://localhost:8501
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 安装依赖
echo 正在检查依赖...
pip install -q -r requirements.txt

echo.
echo =====================================
echo 正在启动服务...
echo =====================================
echo.

REM 使用start命令在新窗口中启动API服务
echo [1/2] 启动API服务...
start "论文Agent API" cmd /k "python api.py"

REM 等待API服务启动
timeout /t 3 /nobreak >nul

REM 启动Web界面
echo [2/2] 启动Web界面...
streamlit run app.py

pause
