@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pdf-to-epub-gui.exe" (
    echo.
    echo [BİLGİ] Program henüz kurulmamış. Kolay kurulum başlatılıyor...
    call "%~dp0KURULUM.bat"
    exit /b %errorlevel%
)

powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
if errorlevel 1 (
    echo [HATA] Uygulama açılamadı. KURULUM.bat dosyasını yeniden çalıştırın.
    pause
    exit /b 1
)
exit /b 0
