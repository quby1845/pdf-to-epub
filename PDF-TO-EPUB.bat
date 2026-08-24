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
echo [INFO] The application is not installed yet. Starting legacy setup...
call "%~dp0KURULUM.bat"
exit /b %errorlevel%

:powershell_missing
echo [ERROR] Windows PowerShell was not found.
pause
exit /b 1

:launch_failed
echo [ERROR] The application could not start. Run Setup or KURULUM.bat again.
pause
exit /b 1

:self_test
echo PDF_TO_EPUB_LAUNCHER_OK
exit /b 0
