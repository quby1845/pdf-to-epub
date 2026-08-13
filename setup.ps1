# Windows setup used by KURULUM.bat.
# It prefers Python 3.12 and installs missing system tools with winget.

$ErrorActionPreference = "Stop"
$venvPath = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

function Find-SupportedPython {
    $candidates = @(
        [pscustomobject]@{ Command = "py"; Arguments = @("-3.12") },
        [pscustomobject]@{ Command = "py"; Arguments = @("-3.11") },
        [pscustomobject]@{ Command = "py"; Arguments = @("-3.13") },
        [pscustomobject]@{ Command = "python"; Arguments = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) {
            continue
        }
        $version = & $candidate.Command @($candidate.Arguments) -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $version -in @("3.11", "3.12", "3.13")) {
            return $candidate
        }
    }

    $knownPaths = @(
        (Join-Path $env:LocalAppData "Programs\Python\Python312\python.exe"),
        (Join-Path $env:ProgramFiles "Python312\python.exe")
    )
    foreach ($knownPath in $knownPaths) {
        if (Test-Path $knownPath) {
            return [pscustomobject]@{ Command = $knownPath; Arguments = @() }
        }
    }
    return $null
}

function Invoke-SelectedPython {
    param(
        [Parameter(Mandatory = $true)] $Selection,
        [Parameter(ValueFromRemainingArguments = $true)] [string[]] $PythonArguments
    )
    & $Selection.Command @($Selection.Arguments) @PythonArguments
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory = $true)] [string] $Id,
        [Parameter(Mandatory = $true)] [string] $DisplayName
    )
    Write-Host "$DisplayName kuruluyor..." -ForegroundColor Green
    winget install --exact --id $Id --accept-source-agreements --accept-package-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        throw "$DisplayName kurulamadı (winget çıkış kodu: $LASTEXITCODE)."
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PDF to EPUB OCR - Kolay Kurulum" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$python = Find-SupportedPython
if (-not $python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "Python 3.11-3.13 bulunamadı ve winget kullanılamıyor." -ForegroundColor Red
        Write-Host "Önce https://www.python.org/downloads/ adresinden Python 3.12 kurun." -ForegroundColor Yellow
        exit 1
    }
    Install-WingetPackage -Id "Python.Python.3.12" -DisplayName "Python 3.12"
    $python = Find-SupportedPython
}

if (-not $python) {
    Write-Host "Python kuruldu ancak bu oturumda bulunamadı." -ForegroundColor Yellow
    Write-Host "Bilgisayarı yeniden başlatıp KURULUM.bat dosyasını tekrar açın." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/6] Python ortamı hazırlanıyor..." -ForegroundColor Green
if (-not (Test-Path $venvPython)) {
    Invoke-SelectedPython -Selection $python -PythonArguments @("-m", "venv", $venvPath)
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        throw "Python ortamı oluşturulamadı."
    }
} else {
    Write-Host "Mevcut .venv kullanılacak." -ForegroundColor Yellow
}

Write-Host "[2/6] Kurulum araçları güncelleniyor..." -ForegroundColor Green
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip güncellenemedi." }

Write-Host "[3/6] NVIDIA CUDA destekli PyTorch kuruluyor..." -ForegroundColor Green
& $venvPython -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
if ($LASTEXITCODE -ne 0) {
    Write-Host "CUDA 12.6 paketi kurulamadı; CUDA 13.0 deneniyor..." -ForegroundColor Yellow
    & $venvPython -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
}
if ($LASTEXITCODE -ne 0) {
    throw "PyTorch kurulamadı. https://pytorch.org/get-started/locally/ adresindeki seçiciyi kullanın."
}

Write-Host "[4/6] PDF to EPUB OCR ve bağımlılıklar kuruluyor..." -ForegroundColor Green
& $venvPython -m pip install --editable $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw "Proje bağımlılıkları kurulamadı." }

Write-Host "[5/6] Pandoc ve Poppler kontrol ediliyor..." -ForegroundColor Green
if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Install-WingetPackage -Id "JohnMacFarlane.Pandoc" -DisplayName "Pandoc"
    } else {
        throw "Pandoc bulunamadı. https://pandoc.org/installing.html adresinden kurun."
    }
}
if (-not (Get-Command pdftoppm -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Install-WingetPackage -Id "oschwartz10612.Poppler" -DisplayName "Poppler"
    } else {
        throw "Poppler bulunamadı. Poppler'ı kurup bin klasörünü PATH'e ekleyin."
    }
}

Write-Host "[6/6] Masaüstü kısayolu hazırlanıyor..." -ForegroundColor Green
try {
    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcut = $shell.CreateShortcut((Join-Path $desktop "PDF to EPUB OCR.lnk"))
    $shortcut.TargetPath = Join-Path $PSScriptRoot "PDF-TO-EPUB.bat"
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = "Taranmış PDF dosyalarını EPUB'a dönüştür"
    $shortcut.Save()
} catch {
    Write-Host "Masaüstü kısayolu oluşturulamadı; PDF-TO-EPUB.bat yine kullanılabilir." -ForegroundColor Yellow
}

& $venvPython -c "import torch; print(f'PyTorch {torch.__version__}; CUDA kullanılabilir: {torch.cuda.is_available()}')"

Write-Host ""
Write-Host "Kurulum tamamlandı." -ForegroundColor Green
Write-Host "Bundan sonra masaüstündeki 'PDF to EPUB OCR' kısayolunu açmanız yeterli." -ForegroundColor Green
