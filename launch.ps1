# Refresh PATH after winget installations, then launch the windowed entry point.
# This file intentionally uses ASCII text for Windows PowerShell 5.1 compatibility.

param([switch] $SelfTest)

$ErrorActionPreference = "Stop"

if ($SelfTest) {
    Write-Output "PDF_TO_EPUB_LAUNCH_SCRIPT_OK"
    exit 0
}

$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

$installRoot = if ($env:PDF_TO_EPUB_INSTALL_ROOT) {
    [IO.Path]::GetFullPath($env:PDF_TO_EPUB_INSTALL_ROOT)
} else {
    Join-Path $env:LocalAppData "PDF-to-EPUB-OCR"
}
$launcher = Join-Path $installRoot "venv\Scripts\pdf-to-epub-gui.exe"
if (-not (Test-Path $launcher)) {
    throw "The application was not found. Run Setup again."
}
Start-Process -FilePath $launcher -WorkingDirectory $PSScriptRoot
