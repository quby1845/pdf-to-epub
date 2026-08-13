@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

title PDF to EPUB OCR - Kurulum
echo.
echo ========================================
echo   PDF to EPUB OCR - Kolay Kurulum
echo ========================================
echo.
echo Bu işlem gerekli programları ve OCR bileşenlerini kurar.
echo İlk kurulum internet hızına göre 10-30 dakika sürebilir.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
    echo.
    echo [HATA] Kurulum tamamlanamadı. Yukarıdaki mesajı ekran görüntüsüyle paylaşabilirsiniz.
    pause
    exit /b 1
)

echo.
echo Kurulum tamamlandı. Uygulama şimdi açılıyor...
timeout /t 2 /nobreak >nul
call "%~dp0PDF-TO-EPUB.bat"
exit /b %errorlevel%
