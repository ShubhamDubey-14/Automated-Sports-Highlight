@echo off
echo Sports Highlights Generator
echo ============================
echo.
echo Starting the server...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Install requirements if needed
echo Checking dependencies...
pip install -r requirements.txt

REM Start the server
echo Starting server...
python app.py

pause
