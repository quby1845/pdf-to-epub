# Refresh PATH after winget installations, then launch the windowed entry point.
$ErrorActionPreference = "Stop"
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

$launcher = Join-Path $PSScriptRoot ".venv\Scripts\pdf-to-epub-gui.exe"
if (-not (Test-Path $launcher)) {
    throw "Uygulama bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
}
Start-Process -FilePath $launcher -WorkingDirectory $PSScriptRoot
