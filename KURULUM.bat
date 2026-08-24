@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if /I "%~1"=="--self-test" goto self_test

set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL%" goto powershell_missing
set "INSTALL_LOG_DIR=%LocalAppData%\PDF-to-EPUB-OCR\logs"
set "INSTALL_ERROR_LOG=%INSTALL_LOG_DIR%\install-error.log"
if not exist "%INSTALL_LOG_DIR%" mkdir "%INSTALL_LOG_DIR%" >nul 2>&1
if exist "%INSTALL_ERROR_LOG%" del /q "%INSTALL_ERROR_LOG%" >nul 2>&1
if /I "%~1"=="--failure-self-test" (
    set "PDF_TO_EPUB_INSTALLER_TEST=1"
    echo simulated installer failure>"%INSTALL_ERROR_LOG%"
    set "SETUP_RESULT=1"
    goto setup_failed
)

title PDF to EPUB OCR - Setup
echo.
echo ========================================
echo   PDF to EPUB OCR - Legacy Setup
echo ========================================
echo.
echo Required applications and OCR components will be installed.
echo The first setup can take 10-30 minutes depending on your connection.
echo.

"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" 2>"%INSTALL_ERROR_LOG%"
set "SETUP_RESULT=%errorlevel%"
if not "%SETUP_RESULT%"=="0" goto setup_failed
if not exist "%LocalAppData%\PDF-to-EPUB-OCR\venv\Scripts\pdf-to-epub-gui.exe" goto launcher_missing

echo.
echo Setup completed. Opening the application...
timeout /t 2 /nobreak >nul
call "%~dp0PDF-TO-EPUB.bat"
exit /b %errorlevel%

:powershell_missing
echo.
echo [ERROR] Windows PowerShell was not found.
pause
exit /b 1

:setup_failed
echo.
echo [ERROR] Setup could not be completed.
if exist "%INSTALL_ERROR_LOG%" (
    echo.
    type "%INSTALL_ERROR_LOG%"
    echo.
    echo Detailed error log: %INSTALL_ERROR_LOG%
    if not defined PDF_TO_EPUB_INSTALLER_TEST start "PDF to EPUB OCR - Setup Error" notepad.exe "%INSTALL_ERROR_LOG%"
)
if defined PDF_TO_EPUB_INSTALLER_TEST (
    echo PDF_TO_EPUB_INSTALLER_FAILURE_OK
    exit /b %SETUP_RESULT%
)
echo.
echo This window will remain open.
choice /c C /n /m "Press C to close this window: "
exit /b %SETUP_RESULT%

:launcher_missing
echo.
echo [ERROR] Setup finished but the application launcher is missing.
echo Run KURULUM.bat again.
pause
exit /b 1

:self_test
echo PDF_TO_EPUB_INSTALLER_OK
exit /b 0

