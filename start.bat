@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   PDF to EPUB Converter - Quick Start
echo ========================================
echo.

:: Go to project folder
cd /d "%~dp0"

:: Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated.
) else (
    echo [ERROR] Virtual environment not found! Run setup.ps1 first.
    pause
    exit /b 1
)

:: Check dependencies
echo.
echo Running checks...
python -c "import torch; print(f'  CUDA: {torch.cuda.is_available()} - {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"NOT FOUND\"}')" 2>nul
if errorlevel 1 (
    echo [ERROR] PyTorch is not installed!
    pause
    exit /b 1
)

pandoc --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Pandoc is not installed!
    pause
    exit /b 1
)

echo.
echo ----------------------------------------
echo Place your PDF file in the "input" folder
echo then press any key to continue.
echo ----------------------------------------
echo.

if not exist "input" mkdir input

:: List available PDF files
echo Available PDF files:
dir /b input\*.pdf 2>nul
if errorlevel 1 (
    echo   [!] No PDF files found. Please place a PDF in the input/ folder.
    explorer "%~dp0input"
    pause
    exit /b 1
)

echo.

:: Start conversion
python convert.py

echo.
pause
