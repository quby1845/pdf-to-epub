# ============================================================
# PDF-to-EPUB Setup Script (Windows)
# Requires: NVIDIA GPU (8GB+ VRAM), Python 3.10+, winget
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PDF-to-EPUB Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------
# 1. Create virtual environment
# -----------------------------------------------------------
$venvPath = "$PSScriptRoot\venv"

if (Test-Path $venvPath) {
    Write-Host "[!] Virtual environment already exists: $venvPath" -ForegroundColor Yellow
} else {
    Write-Host "[1/5] Creating virtual environment..." -ForegroundColor Green
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
    Write-Host "  -> Virtual environment created." -ForegroundColor Green
}

# Activate virtual environment
$activateScript = "$venvPath\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Host "  -> Virtual environment activated." -ForegroundColor Green
} else {
    Write-Host "ERROR: Activate.ps1 not found!" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------
# 2. Install PyTorch + CUDA
# -----------------------------------------------------------
Write-Host ""
Write-Host "[2/5] Installing PyTorch + CUDA..." -ForegroundColor Green
Write-Host "  (This may take a few minutes - ~2.5 GB download)" -ForegroundColor DarkGray

# CUDA 12.6 stable build (most reliable Windows support)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "WARNING: cu126 install failed. Trying cu132..." -ForegroundColor Yellow
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu132
}

# Verify CUDA
Write-Host ""
Write-Host "  Verifying CUDA..." -ForegroundColor DarkGray
python -c "import torch; cuda_ok = torch.cuda.is_available(); print(f'  CUDA available: {cuda_ok}'); print(f'  GPU: {torch.cuda.get_device_name(0)}' if cuda_ok else '  WARNING: CUDA not found!')"

# -----------------------------------------------------------
# 3. Install pdf-craft
# -----------------------------------------------------------
Write-Host ""
Write-Host "[3/5] Installing pdf-craft..." -ForegroundColor Green
pip install pdf-craft

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install pdf-craft!" -ForegroundColor Red
    exit 1
}
Write-Host "  -> pdf-craft installed." -ForegroundColor Green

# -----------------------------------------------------------
# 4. Install Pandoc (via winget)
# -----------------------------------------------------------
Write-Host ""
Write-Host "[4/5] Checking Pandoc..." -ForegroundColor Green

$pandocCheck = Get-Command pandoc -ErrorAction SilentlyContinue
if ($pandocCheck) {
    Write-Host "  -> Pandoc already installed: $(pandoc --version | Select-Object -First 1)" -ForegroundColor Green
} else {
    Write-Host "  Installing Pandoc via winget..." -ForegroundColor DarkGray
    winget install --exact --id JohnMacFarlane.Pandoc --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Pandoc installation failed! Install manually:" -ForegroundColor Red
        Write-Host "  https://pandoc.org/installing.html" -ForegroundColor Yellow
    } else {
        Write-Host "  -> Pandoc installed. Restart your terminal to update PATH." -ForegroundColor Green
    }
}

# -----------------------------------------------------------
# 5. Install Poppler (via winget)
# -----------------------------------------------------------
Write-Host ""
Write-Host "[5/5] Checking Poppler..." -ForegroundColor Green

$popplerCheck = Get-Command pdftoppm -ErrorAction SilentlyContinue
if ($popplerCheck) {
    Write-Host "  -> Poppler already installed." -ForegroundColor Green
} else {
    Write-Host "  Installing Poppler via winget..." -ForegroundColor DarkGray
    winget install --exact --id oschwartz10612.Poppler --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Poppler installation failed! Install manually:" -ForegroundColor Red
        Write-Host "  https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Yellow
        Write-Host "  After extracting, add the bin/ folder to your system PATH." -ForegroundColor Yellow
    } else {
        Write-Host "  -> Poppler installed. Restart your terminal to update PATH." -ForegroundColor Green
    }
}

# -----------------------------------------------------------
# Create project directories
# -----------------------------------------------------------
$dirs = @("input", "output", "models", "temp")
foreach ($dir in $dirs) {
    $fullPath = "$PSScriptRoot\$dir"
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath | Out-Null
    }
}

# -----------------------------------------------------------
# Summary
# -----------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. CLOSE this terminal and open a NEW one (to update PATH)" -ForegroundColor Yellow
Write-Host "  2. Place your PDF file in the 'input' folder" -ForegroundColor White
Write-Host "  3. Run the converter:" -ForegroundColor White
Write-Host "     cd $PSScriptRoot" -ForegroundColor DarkGray
Write-Host "     .\venv\Scripts\Activate.ps1" -ForegroundColor DarkGray
Write-Host "     python convert.py" -ForegroundColor DarkGray
Write-Host ""
