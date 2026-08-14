@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if /I "%~1"=="--self-test" goto self_test

set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL%" goto powershell_missing

title PDF to EPUB OCR - Setup
echo.
echo ========================================
echo   PDF to EPUB OCR - Kolay Kurulum
echo ========================================
echo.
echo Gerekli programlar ve OCR bilesenleri kurulacak.
echo Ilk kurulum internet hizina gore 10-30 dakika surebilir.
echo.

"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set "SETUP_RESULT=%errorlevel%"
if not "%SETUP_RESULT%"=="0" goto setup_failed
if not exist "%LocalAppData%\PDF-to-EPUB-OCR\venv\Scripts\pdf-to-epub-gui.exe" goto launcher_missing

echo.
echo Kurulum tamamlandi. Uygulama aciliyor...
timeout /t 2 /nobreak >nul
call "%~dp0PDF-TO-EPUB.bat"
exit /b %errorlevel%

:powershell_missing
echo.
echo [HATA] Windows PowerShell bulunamadi.
pause
exit /b 1

:setup_failed
echo.
echo [HATA] Kurulum tamamlanamadi. Yukaridaki son hata mesajinin ekran goruntusunu paylasin.
pause
exit /b %SETUP_RESULT%

:launcher_missing
echo.
echo [HATA] Kurulum tamamlandi ancak uygulama baslaticisi olusmadi.
echo KURULUM.bat dosyasini yeniden calistirin.
pause
exit /b 1

:self_test
echo PDF_TO_EPUB_INSTALLER_OK
exit /b 0
