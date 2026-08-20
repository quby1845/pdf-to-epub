@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if /I "%~1"=="--self-test" goto self_test

if not exist "%LocalAppData%\PDF-to-EPUB-OCR\venv\Scripts\pdf-to-epub-gui.exe" goto not_installed

set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL%" goto powershell_missing

"%POWERSHELL%" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
if errorlevel 1 goto launch_failed
exit /b 0

:not_installed
echo.
echo [BILGI] Program henuz kurulmamis. Kolay kurulum baslatiliyor...
call "%~dp0KURULUM.bat"
exit /b %errorlevel%

:powershell_missing
echo [HATA] Windows PowerShell bulunamadi.
pause
exit /b 1

:launch_failed
echo [HATA] Uygulama acilamadi. KURULUM.bat dosyasini yeniden calistirin.
pause
exit /b 1

:self_test
echo PDF_TO_EPUB_LAUNCHER_OK
exit /b 0
