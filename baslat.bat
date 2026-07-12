@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   PDF-to-EPUB Hizli Baslat
echo ========================================
echo.

:: Proje klasorune git
cd /d "%~dp0"

:: Sanal ortami aktif et
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Sanal ortam aktif edildi.
) else (
    echo [HATA] Sanal ortam bulunamadi! Once setup.ps1 calistirin.
    pause
    exit /b 1
)

:: Kontroller
echo.
echo Kontroller yapiliyor...
python -c "import torch; print(f'  CUDA: {torch.cuda.is_available()} - {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"YOK\"}')" 2>nul
if errorlevel 1 (
    echo [HATA] PyTorch kurulu degil!
    pause
    exit /b 1
)

pandoc --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Pandoc kurulu degil!
    pause
    exit /b 1
)

echo.
echo ----------------------------------------
echo PDF dosyanizi "input" klasorune koyun
echo ve Enter'a basin.
echo ----------------------------------------
echo.

if not exist "input" mkdir input

:: PDF dosyalarini listele
echo Mevcut PDF dosyalari:
dir /b input\*.pdf 2>nul
if errorlevel 1 (
    echo   [!] Hic PDF bulunamadi. Lutfen input/ klasorune PDF koyun.
    explorer "%~dp0input"
    pause
    exit /b 1
)

echo.

:: Donusumu baslat
python convert.py

echo.
pause
