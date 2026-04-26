@echo off
REM Deploy Script for Windows
REM Usage: deploy.bat

echo ========================================
echo Paper Agent System Deployment
echo ========================================

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Install dependencies
echo [2/5] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    exit /b 1
)

REM Check API key
echo [3/5] Checking environment variables...
if "%OPENAI_API_KEY%"=="" (
    echo Warning: OPENAI_API_KEY is not set
    echo Please set it in .env file or environment
)

REM Build Docker image
echo [4/5] Building Docker image...
docker build -t paper-agent .
if errorlevel 1 (
    echo Warning: Docker build failed (Docker may not be installed)
)

REM Start services
echo [5/5] Starting services...
docker-compose up -d

echo ========================================
echo Deployment complete!
echo ========================================
echo.
echo View logs with: docker-compose logs -f
echo Stop with: docker-compose down
