@echo off
title Volcano AI Image Generator
cls
echo ================================
echo   Volcano AI Image Generator
echo ================================
echo.

echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Error: Python not found!
    echo Please install Python 3.6 or higher and add it to PATH.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo Python environment OK

echo Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Error: pip not found!
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
echo pip OK

echo Installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Warning: Failed to install dependencies, trying individual packages...
    
    python -m pip install requests
    python -m pip install Pillow
    
    if %errorlevel% neq 0 (
        echo.
        echo Error: Failed to install packages!
        echo Please run manually: pip install -r requirements.txt
        echo.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
)

echo Dependencies installed!

echo.
echo ================================
echo Starting Volcano AI Image Generator...
echo ================================
echo.

python main.py

echo.
echo ================================
echo Program exited
echo ================================
echo.
echo Press any key to close this window...
pause >nul