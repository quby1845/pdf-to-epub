@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo   PDF to EPUB OCR
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv was not found. Run setup.ps1 first.
    pause
    exit /b 1
)

if not exist "input" mkdir input
dir /b "input\*.pdf" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No PDF files were found in input\.
    echo Place a PDF in that folder and run this file again.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" convert.py
set "result=%errorlevel%"
echo.
if not "%result%"=="0" echo Conversion ended with an error.
pause
exit /b %result%
