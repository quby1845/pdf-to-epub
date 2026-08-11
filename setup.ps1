# PDF to EPUB OCR setup for Windows.
# Requires Python 3.11-3.13, winget, and an NVIDIA GPU for supported conversions.

$ErrorActionPreference = "Stop"
$venvPath = Join-Path $PSScriptRoot ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PDF to EPUB OCR - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $pythonVersion -notin @("3.11", "3.12", "3.13")) {
    Write-Host "Python 3.11, 3.12, or 3.13 is required (found: $pythonVersion)." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $venvPath)) {
    Write-Host "[1/5] Creating .venv..." -ForegroundColor Green
    python -m venv $venvPath
} else {
    Write-Host "[1/5] Reusing .venv." -ForegroundColor Yellow
}

Write-Host "[2/5] Updating packaging tools..." -ForegroundColor Green
& $pythonPath -m pip install --upgrade pip

Write-Host "[3/5] Installing CUDA-enabled PyTorch..." -ForegroundColor Green
& $pythonPath -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
if ($LASTEXITCODE -ne 0) {
    Write-Host "CUDA 12.6 wheels failed; trying CUDA 13.0 wheels..." -ForegroundColor Yellow
    & $pythonPath -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyTorch installation failed. Use the selector at https://pytorch.org/get-started/locally/." -ForegroundColor Red
    exit 1
}

Write-Host "[4/5] Installing PDF to EPUB OCR and Python dependencies..." -ForegroundColor Green
& $pythonPath -m pip install --editable $PSScriptRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host "Project installation failed." -ForegroundColor Red
    exit 1
}

Write-Host "[5/5] Checking system tools..." -ForegroundColor Green
if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    winget install --exact --id JohnMacFarlane.Pandoc --accept-source-agreements --accept-package-agreements
}
if (-not (Get-Command pdftoppm -ErrorAction SilentlyContinue)) {
    winget install --exact --id oschwartz10612.Poppler --accept-source-agreements --accept-package-agreements
}

foreach ($directory in @("input", "output")) {
    $path = Join-Path $PSScriptRoot $directory
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

& $pythonPath -c "import torch; print(f'PyTorch {torch.__version__}; CUDA available: {torch.cuda.is_available()}')"

Write-Host ""
Write-Host "Setup complete. Open a new terminal, place a PDF in input/, then run start.bat." -ForegroundColor Green
