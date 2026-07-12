# ============================================================
# PDF-to-EPUB Yerel Kurulum Scripti (Windows)
# RTX 4060 Ti + Python 3.12 + CUDA 13.2
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PDF-to-EPUB Yerel Kurulum Basliyor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------
# 1. Sanal ortam (virtual environment) olustur
# -----------------------------------------------------------
$venvPath = "$PSScriptRoot\venv"

if (Test-Path $venvPath) {
    Write-Host "[!] Sanal ortam zaten mevcut: $venvPath" -ForegroundColor Yellow
} else {
    Write-Host "[1/5] Sanal ortam olusturuluyor..." -ForegroundColor Green
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "HATA: Sanal ortam olusturulamadi!" -ForegroundColor Red
        exit 1
    }
    Write-Host "  -> Sanal ortam olusturuldu." -ForegroundColor Green
}

# Sanal ortami aktif et
$activateScript = "$venvPath\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Host "  -> Sanal ortam aktif edildi." -ForegroundColor Green
} else {
    Write-Host "HATA: Activate.ps1 bulunamadi!" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------
# 2. PyTorch + CUDA kurulumu
# -----------------------------------------------------------
Write-Host ""
Write-Host "[2/5] PyTorch + CUDA kurulumu yapiliyor..." -ForegroundColor Green
Write-Host "  (Bu islem birkaç dakika surebilir)" -ForegroundColor DarkGray

# CUDA 12.6 stabil sürüm (en güvenilir Windows desteği)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "UYARI: cu126 kurulumu basarisiz. cu132 deneniyor..." -ForegroundColor Yellow
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu132
}

# CUDA dogrulama
Write-Host ""
Write-Host "  CUDA dogrulamasi yapiliyor..." -ForegroundColor DarkGray
python -c "import torch; cuda_ok = torch.cuda.is_available(); print(f'  CUDA kullanilabilir: {cuda_ok}'); print(f'  GPU: {torch.cuda.get_device_name(0)}' if cuda_ok else '  UYARI: CUDA bulunamadi!')"

# -----------------------------------------------------------
# 3. pdf-craft kurulumu
# -----------------------------------------------------------
Write-Host ""
Write-Host "[3/5] pdf-craft kurulumu yapiliyor..." -ForegroundColor Green
pip install pdf-craft

if ($LASTEXITCODE -ne 0) {
    Write-Host "HATA: pdf-craft kurulamadi!" -ForegroundColor Red
    exit 1
}
Write-Host "  -> pdf-craft kuruldu." -ForegroundColor Green

# -----------------------------------------------------------
# 4. Pandoc kurulumu (winget ile)
# -----------------------------------------------------------
Write-Host ""
Write-Host "[4/5] Pandoc kontrol ediliyor..." -ForegroundColor Green

$pandocCheck = Get-Command pandoc -ErrorAction SilentlyContinue
if ($pandocCheck) {
    Write-Host "  -> Pandoc zaten kurulu: $(pandoc --version | Select-Object -First 1)" -ForegroundColor Green
} else {
    Write-Host "  Pandoc kuruluyor (winget ile)..." -ForegroundColor DarkGray
    winget install --exact --id JohnMacFarlane.Pandoc --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "HATA: Pandoc kurulamadi! Manuel olarak indirin:" -ForegroundColor Red
        Write-Host "  https://pandoc.org/installing.html" -ForegroundColor Yellow
    } else {
        Write-Host "  -> Pandoc kuruldu. Terminal'i yeniden baslatin PATH'in guncellenmesi icin." -ForegroundColor Green
    }
}

# -----------------------------------------------------------
# 5. Poppler kurulumu (winget ile)
# -----------------------------------------------------------
Write-Host ""
Write-Host "[5/5] Poppler kontrol ediliyor..." -ForegroundColor Green

$popplerCheck = Get-Command pdftoppm -ErrorAction SilentlyContinue
if ($popplerCheck) {
    Write-Host "  -> Poppler zaten kurulu." -ForegroundColor Green
} else {
    Write-Host "  Poppler kuruluyor (winget ile)..." -ForegroundColor DarkGray
    winget install --exact --id oschwartz10612.Poppler --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "HATA: Poppler kurulamadi! Manuel olarak indirin:" -ForegroundColor Red
        Write-Host "  https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Yellow
        Write-Host "  Indirdikten sonra bin/ klasorunu PATH'e ekleyin." -ForegroundColor Yellow
    } else {
        Write-Host "  -> Poppler kuruldu. Terminal'i yeniden baslatin PATH'in guncellenmesi icin." -ForegroundColor Green
    }
}

# -----------------------------------------------------------
# Klasorleri olustur
# -----------------------------------------------------------
$dirs = @("input", "output", "models", "temp")
foreach ($dir in $dirs) {
    $fullPath = "$PSScriptRoot\$dir"
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath | Out-Null
    }
}

# -----------------------------------------------------------
# Ozet
# -----------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Kurulum Tamamlandi!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Sonraki adimlar:" -ForegroundColor White
Write-Host "  1. Bu terminali KAPATIN ve YENI bir terminal acin (PATH guncellenmesi icin)" -ForegroundColor Yellow
Write-Host "  2. PDF dosyanizi 'input' klasorune koyun" -ForegroundColor White
Write-Host "  3. Donusumu baslatmak icin:" -ForegroundColor White
Write-Host "     cd $PSScriptRoot" -ForegroundColor DarkGray
Write-Host "     .\venv\Scripts\Activate.ps1" -ForegroundColor DarkGray
Write-Host "     python convert.py" -ForegroundColor DarkGray
Write-Host ""
