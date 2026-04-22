@echo off
chcp 65001 > nul
echo =====================================
echo     论文Agent Web界面启动中...
echo =====================================

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

REM 启动Streamlit应用
echo 启动Web界面...
streamlit run app.py

pause
