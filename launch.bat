@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
echo Starting AI Sketch Booth...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Kill other Python instances running app.py from this project
echo Checking for other running instances...
set "PROJECT_DIR=%~dp0"
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2^>nul ^| findstr /I "PID:"') do (
    set "pid=%%a"
    REM Check if this PID is running app.py from this directory
    wmic process where "ProcessId=!pid!" get CommandLine 2>nul | findstr /I /C:"app.py" | findstr /I /C:"!PROJECT_DIR!" >nul 2>&1
    if not errorlevel 1 (
        echo Killing existing instance: PID !pid!
        taskkill /PID !pid! /F >nul 2>&1
    )
)

REM Also kill Python instances that might be holding COM ports (dexarm scripts)
echo Checking for Python instances using serial ports...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2^>nul ^| findstr /I "PID:"') do (
    set "pid=%%a"
    REM Check if this PID is running anything with dexarm or serial from this directory
    wmic process where "ProcessId=!pid!" get CommandLine 2>nul | findstr /I /C:"dexarm" | findstr /I /C:"!PROJECT_DIR!" >nul 2>&1
    if not errorlevel 1 (
        echo Killing DexArm-related instance: PID !pid!
        taskkill /PID !pid! /F >nul 2>&1
    )
)

echo Waiting for ports to be released...
timeout /t 2 /nobreak >nul

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask is not installed. Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error installing dependencies
        pause
        exit /b 1
    )
)

REM Start Flask server in background
echo Starting Flask server...
start /B python app.py

REM Wait for server to start
echo Waiting for server to start...
timeout /t 3 /nobreak >nul

REM Find Chrome installation
set CHROME_PATH=""
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if %CHROME_PATH%=="" (
    echo Chrome not found. Opening in default browser...
    start http://localhost:5000
) else (
    echo Opening Chrome...
    REM Launch Chrome with flags to allow camera access on localhost
    %CHROME_PATH% --new-window --app=http://localhost:5000 --use-fake-ui-for-media-stream --allow-file-access-from-files
)

echo.
echo AI Sketch Booth is running!
echo Press Ctrl+C to stop the server
echo.
pause
