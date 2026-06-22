@echo off
echo ====================================================
echo Building yt-dlp Flow Executable for Windows
echo ====================================================

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: Create Virtual Environment
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate and install requirements
echo Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt
pip install pyinstaller

:: Compile executable
echo Compiling standalone Windows executable...
pyinstaller --clean gui-yt-dlp.spec

echo ====================================================
echo Build Complete!
echo Standalone executable is in: dist\gui-yt-dlp.exe
echo ====================================================
pause
