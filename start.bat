@echo off
rem Backward-compatible English launcher. The main user-facing launcher is PDF-TO-EPUB.bat.
call "%~dp0PDF-TO-EPUB.bat"
exit /b %errorlevel%
