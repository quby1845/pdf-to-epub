# Windows setup used by KURULUM.bat.
# This file intentionally uses ASCII text for Windows PowerShell 5.1 compatibility.

param([switch] $SelfTest)

$ErrorActionPreference = "Stop"

if ($SelfTest) {
    Write-Output "PDF_TO_EPUB_SETUP_OK"
    exit 0
}

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
        throw "$DisplayName kurulamadi (winget cikis kodu: $LASTEXITCODE)."
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PDF to EPUB OCR - Kolay Kurulum" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$python = Find-SupportedPython
if (-not $python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "Python 3.11-3.13 bulunamadi ve winget kullanilamiyor." -ForegroundColor Red
        Write-Host "Once https://www.python.org/downloads/ adresinden Python 3.12 kurun." -ForegroundColor Yellow
        exit 1
    }
    Install-WingetPackage -Id "Python.Python.3.12" -DisplayName "Python 3.12"
    $python = Find-SupportedPython
}

if (-not $python) {
    Write-Host "Python kuruldu ancak bu oturumda bulunamadi." -ForegroundColor Yellow
    Write-Host "Bilgisayari yeniden baslatip KURULUM.bat dosyasini tekrar acin." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/6] Python ortami hazirlaniyor..." -ForegroundColor Green
if (-not (Test-Path $venvPython)) {
    Invoke-SelectedPython -Selection $python -PythonArguments @("-m", "venv", $venvPath)
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        throw "Python ortami olusturulamadi."
    }
} else {
    Write-Host "Mevcut .venv kullanilacak." -ForegroundColor Yellow
}

Write-Host "[2/6] Kurulum araclari guncelleniyor..." -ForegroundColor Green
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip guncellenemedi." }

Write-Host "[3/6] NVIDIA CUDA destekli PyTorch kuruluyor..." -ForegroundColor Green
& $venvPython -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
if ($LASTEXITCODE -ne 0) {
    Write-Host "CUDA 12.6 paketi kurulamadi; CUDA 13.0 deneniyor..." -ForegroundColor Yellow
    & $venvPython -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
}
if ($LASTEXITCODE -ne 0) {
    throw "PyTorch kurulamadi. https://pytorch.org/get-started/locally/ adresindeki seciciyi kullanin."
}

Write-Host "[4/6] PDF to EPUB OCR ve bagimliliklar kuruluyor..." -ForegroundColor Green
& $venvPython -m pip install --editable $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw "Proje bagimliliklari kurulamadi." }

Write-Host "[5/6] Pandoc ve Poppler kontrol ediliyor..." -ForegroundColor Green
if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Install-WingetPackage -Id "JohnMacFarlane.Pandoc" -DisplayName "Pandoc"
    } else {
        throw "Pandoc bulunamadi. https://pandoc.org/installing.html adresinden kurun."
    }
}
if (-not (Get-Command pdftoppm -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Install-WingetPackage -Id "oschwartz10612.Poppler" -DisplayName "Poppler"
    } else {
        throw "Poppler bulunamadi. Poppler'i kurup bin klasorunu PATH'e ekleyin."
    }
}

Write-Host "[6/6] Masaustu kisayolu hazirlaniyor..." -ForegroundColor Green
try {
    $shell = New-Object -ComObject WScript.Shell
    $powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $launchScript = Join-Path $PSScriptRoot "launch.ps1"
    $guiLauncher = Join-Path $PSScriptRoot ".venv\Scripts\pdf-to-epub-gui.exe"
    $desktop = [Environment]::GetFolderPath("Desktop")
    $programs = [Environment]::GetFolderPath("Programs")

    foreach ($shortcutFolder in @($desktop, $programs)) {
        $shortcut = $shell.CreateShortcut((Join-Path $shortcutFolder "PDF to EPUB OCR.lnk"))
        $shortcut.TargetPath = $powerShellPath
        $shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launchScript`""
        $shortcut.WorkingDirectory = $PSScriptRoot
        $shortcut.IconLocation = "$guiLauncher,0"
        $shortcut.Description = "Taranmis PDF dosyalarini EPUB'a donustur"
        $shortcut.Save()
    }
} catch {
    Write-Host "Uygulama kisayollari olusturulamadi; PDF-TO-EPUB.bat yine kullanilabilir." -ForegroundColor Yellow
}

& $venvPython -c "import torch; print(f'PyTorch {torch.__version__}; CUDA kullanilabilir: {torch.cuda.is_available()}')"

Write-Host ""
Write-Host "Kurulum tamamlandi." -ForegroundColor Green
Write-Host "Bundan sonra masaustundeki 'PDF to EPUB OCR' kisayolunu acmaniz yeterli." -ForegroundColor Green
