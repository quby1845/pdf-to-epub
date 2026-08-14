# Windows setup used by KURULUM.bat.
# This file intentionally uses ASCII text for Windows PowerShell 5.1 compatibility.

param(
    [switch] $SelfTest,
    [switch] $PythonProbeSelfTest,
    [switch] $InstallerLogicSelfTest
)

$ErrorActionPreference = "Stop"

if ($SelfTest) {
    Write-Output "PDF_TO_EPUB_SETUP_OK"
    exit 0
}

function Get-ManagedInstallRoot {
    if ($env:PDF_TO_EPUB_INSTALL_ROOT) {
        return [IO.Path]::GetFullPath($env:PDF_TO_EPUB_INSTALL_ROOT)
    }
    return Join-Path $env:LocalAppData "PDF-to-EPUB-OCR"
}

function Get-PythonCandidateVersion {
    param([Parameter(Mandatory = $true)] $Candidate)

    # Windows may expose a Microsoft Store/App Execution Alias named python.exe.
    # Probe every candidate without allowing native stderr to abort the installer.
    $previousErrorActionPreference = $ErrorActionPreference
    $output = $null
    $exitCode = 1
    try {
        $ErrorActionPreference = "Continue"
        $output = & $Candidate.Command @($Candidate.Arguments) -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $exitCode = $LASTEXITCODE
    } catch {
        return $null
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0) {
        return $null
    }

    $version = [string]($output | Select-Object -Last 1)
    if ($version -in @("3.11", "3.12", "3.13")) {
        return $version
    }
    return $null
}

function Find-SupportedPython {
    param([object[]] $Candidates)

    if (-not $PSBoundParameters.ContainsKey("Candidates")) {
        $Candidates = @(
            [pscustomobject]@{ Command = "py"; Arguments = @("-3.12") },
            [pscustomobject]@{ Command = "py"; Arguments = @("-3.11") },
            [pscustomobject]@{ Command = "py"; Arguments = @("-3.13") },
            [pscustomobject]@{ Command = "python"; Arguments = @() }
        )
    }

    foreach ($candidate in $Candidates) {
        if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) {
            continue
        }
        if (Get-PythonCandidateVersion -Candidate $candidate) {
            return $candidate
        }
    }

    $knownPaths = @(
        (Join-Path $env:LocalAppData "Programs\Python\Python313\python.exe"),
        (Join-Path $env:LocalAppData "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LocalAppData "Programs\Python\Python311\python.exe"),
        (Join-Path $env:ProgramFiles "Python313\python.exe"),
        (Join-Path $env:ProgramFiles "Python312\python.exe"),
        (Join-Path $env:ProgramFiles "Python311\python.exe")
    )
    foreach ($knownPath in $knownPaths) {
        if (Test-Path $knownPath) {
            $candidate = [pscustomobject]@{ Command = $knownPath; Arguments = @() }
            if (Get-PythonCandidateVersion -Candidate $candidate) {
                return $candidate
            }
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

function Test-PythonCommand {
    param(
        [Parameter(Mandatory = $true)] [string] $Command,
        [Parameter(Mandatory = $true)] [string] $Code
    )
    if (-not (Test-Path -LiteralPath $Command)) {
        return $false
    }
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Command -c $Code *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Reset-ManagedVenv {
    param(
        [Parameter(Mandatory = $true)] [string] $InstallRoot,
        [Parameter(Mandatory = $true)] [string] $VenvPath
    )
    $resolvedRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
    $resolvedVenv = [IO.Path]::GetFullPath($VenvPath).TrimEnd('\')
    if ([IO.Path]::GetDirectoryName($resolvedVenv) -ne $resolvedRoot -or
        [IO.Path]::GetFileName($resolvedVenv) -ne "venv") {
        throw "Guvenlik denetimi: yonetilen Python ortami disindaki bir klasor silinemez."
    }
    if (Test-Path -LiteralPath $resolvedVenv) {
        Remove-Item -LiteralPath $resolvedVenv -Recurse -Force
    }
}

function Find-NvidiaSmi {
    $command = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $knownPaths = @(
        (Join-Path $env:SystemRoot "System32\nvidia-smi.exe"),
        (Join-Path $env:ProgramFiles "NVIDIA Corporation\NVSMI\nvidia-smi.exe")
    )
    foreach ($knownPath in $knownPaths) {
        if (Test-Path -LiteralPath $knownPath) {
            return $knownPath
        }
    }
    return $null
}

function Get-NvidiaGpuProfile {
    param([string] $NvidiaSmi)
    if (-not $NvidiaSmi) {
        return [pscustomobject]@{ Name = "Unknown"; ComputeCapability = 0.0; IsBlackwell = $false }
    }

    $line = & $NvidiaSmi --query-gpu=name,compute_cap --format=csv,noheader,nounits 2>$null |
        Select-Object -First 1
    if ($LASTEXITCODE -ne 0 -or -not $line) {
        $line = & $NvidiaSmi --query-gpu=name --format=csv,noheader,nounits 2>$null |
            Select-Object -First 1
    }

    $parts = ([string]$line).Split(",")
    $name = $parts[0].Trim()
    $capability = 0.0
    if ($parts.Count -gt 1) {
        [double]::TryParse(
            $parts[1].Trim(),
            [Globalization.NumberStyles]::Float,
            [Globalization.CultureInfo]::InvariantCulture,
            [ref]$capability
        ) | Out-Null
    }
    $blackwell = $capability -ge 12.0 -or $name -match "RTX\s*50"
    return [pscustomobject]@{
        Name = $name
        ComputeCapability = $capability
        IsBlackwell = $blackwell
    }
}

function Get-TorchChannel {
    param([Parameter(Mandatory = $true)] $GpuProfile)
    if ($GpuProfile.IsBlackwell) {
        return "cu130"
    }
    return "cu126"
}

function Get-TorchProbeCode {
    return @'
import sys
try:
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    capability = tuple(torch.cuda.get_device_capability(0))
    architectures = set(torch.cuda.get_arch_list())
    if capability >= (12, 0) and "sm_120" not in architectures:
        raise RuntimeError("PyTorch does not contain sm_120 kernels")
    value = torch.ones(1, device="cuda")
    value.add_(1)
    torch.cuda.synchronize()
    print(f"PyTorch {torch.__version__}; CUDA {torch.version.cuda}; GPU capability {capability[0]}.{capability[1]}")
except Exception as error:
    print(f"PyTorch/CUDA validation failed: {error}", file=sys.stderr)
    raise
'@
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

if ($PythonProbeSelfTest) {
    $probeRoot = Join-Path ([IO.Path]::GetTempPath()) ("pdf-to-epub-python-probe-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $probeRoot | Out-Null
    try {
        $brokenPython = Join-Path $probeRoot "python.cmd"
        $workingPython = Join-Path $probeRoot "python312.cmd"
        Set-Content -LiteralPath $brokenPython -Encoding Ascii -Value @(
            "@echo off", "echo Python bulunamadi 1>&2", "exit /b 9009"
        )
        Set-Content -LiteralPath $workingPython -Encoding Ascii -Value @(
            "@echo off", "echo 3.12", "exit /b 0"
        )
        $selection = Find-SupportedPython -Candidates @(
            [pscustomobject]@{ Command = $brokenPython; Arguments = @() },
            [pscustomobject]@{ Command = $workingPython; Arguments = @() }
        )
        if (-not $selection -or $selection.Command -ne $workingPython) {
            throw "Broken Python alias was not skipped."
        }
        Write-Output "PDF_TO_EPUB_PYTHON_ALIAS_OK"
    } finally {
        Remove-Item -LiteralPath $probeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit 0
}

if ($InstallerLogicSelfTest) {
    $originalRoot = $env:PDF_TO_EPUB_INSTALL_ROOT
    $testRoot = Join-Path ([IO.Path]::GetTempPath()) ("p2e-installer-test-" + [guid]::NewGuid())
    try {
        $env:PDF_TO_EPUB_INSTALL_ROOT = Join-Path ([IO.Path]::GetTempPath()) "p2e-short"
        $managedRoot = Get-ManagedInstallRoot
        $managedVenv = Join-Path $managedRoot "venv"
        if ($managedVenv.StartsWith($PSScriptRoot, [StringComparison]::OrdinalIgnoreCase) -or
            $managedVenv.Length -gt 120) {
            throw "Managed venv did not use an independent short path."
        }
        $blackwell = [pscustomobject]@{ IsBlackwell = $true }
        $ampere = [pscustomobject]@{ IsBlackwell = $false }
        if ((Get-TorchChannel $blackwell) -ne "cu130" -or
            (Get-TorchChannel $ampere) -ne "cu126") {
            throw "GPU channel selection failed."
        }

        $testVenv = Join-Path $testRoot "venv"
        New-Item -ItemType Directory -Path $testVenv -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $testVenv "partial-install.txt") -Encoding Ascii -Value "broken"
        Reset-ManagedVenv -InstallRoot $testRoot -VenvPath $testVenv
        if (Test-Path -LiteralPath $testVenv) {
            throw "Partial managed venv was not removed."
        }
        Write-Output "PDF_TO_EPUB_INSTALLER_LOGIC_OK"
    } finally {
        $env:PDF_TO_EPUB_INSTALL_ROOT = $originalRoot
        Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit 0
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

$installRoot = Get-ManagedInstallRoot
$venvPath = Join-Path $installRoot "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$torchProbe = Get-TorchProbeCode
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null

Write-Host "[1/7] Kisa yoldaki Python ortami kontrol ediliyor..." -ForegroundColor Green
$venvValid = Test-PythonCommand -Command $venvPython -Code "import sys; assert sys.prefix != sys.base_prefix"
if ($venvValid -and -not (Test-PythonCommand -Command $venvPython -Code "import torch")) {
    Write-Host "Yarim veya bozuk PyTorch kurulumu bulundu; Python ortami onariliyor." -ForegroundColor Yellow
    Reset-ManagedVenv -InstallRoot $installRoot -VenvPath $venvPath
    $venvValid = $false
} elseif (-not $venvValid -and (Test-Path -LiteralPath $venvPath)) {
    Write-Host "Yarim veya bozuk Python ortami bulundu; yeniden olusturuluyor." -ForegroundColor Yellow
    Reset-ManagedVenv -InstallRoot $installRoot -VenvPath $venvPath
}

if (-not $venvValid) {
    Invoke-SelectedPython -Selection $python -PythonArguments @("-m", "venv", $venvPath)
    if ($LASTEXITCODE -ne 0 -or
        -not (Test-PythonCommand -Command $venvPython -Code "import sys; assert sys.prefix != sys.base_prefix")) {
        throw "Python ortami olusturulamadi."
    }
} else {
    Write-Host "Mevcut kisa-yol Python ortami kullanilacak." -ForegroundColor Yellow
}

Write-Host "[2/7] Kurulum araclari guncelleniyor..." -ForegroundColor Green
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip guncellenemedi." }

Write-Host "[3/7] NVIDIA ekran karti ve PyTorch uyumu kontrol ediliyor..." -ForegroundColor Green
$nvidiaSmi = Find-NvidiaSmi
if (-not $nvidiaSmi) {
    throw "NVIDIA ekran karti surucusu bulunamadi. Bu surum yalnizca NVIDIA CUDA ile calisir."
}
$gpuProfile = Get-NvidiaGpuProfile -NvidiaSmi $nvidiaSmi
$torchChannel = Get-TorchChannel -GpuProfile $gpuProfile
Write-Host "Ekran karti: $($gpuProfile.Name); PyTorch kanali: $torchChannel" -ForegroundColor Cyan

if (-not (Test-PythonCommand -Command $venvPython -Code $torchProbe)) {
    Write-Host "Uyumlu NVIDIA CUDA destekli PyTorch kuruluyor..." -ForegroundColor Green
    & $venvPython -m pip install --upgrade --force-reinstall torch torchvision --index-url "https://download.pytorch.org/whl/$torchChannel"
    if ($LASTEXITCODE -ne 0 -and -not $gpuProfile.IsBlackwell) {
        Write-Host "CUDA 12.6 paketi kurulamadi; CUDA 13.0 deneniyor..." -ForegroundColor Yellow
        $torchChannel = "cu130"
        & $venvPython -m pip install --upgrade --force-reinstall torch torchvision --index-url "https://download.pytorch.org/whl/$torchChannel"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "PyTorch kurulamadi. Ag baglantisini ve bos disk alanini kontrol edin."
    }
}

Write-Host "[4/7] PyTorch gercek CUDA islemiyle dogrulaniyor..." -ForegroundColor Green
& $venvPython -c $torchProbe
if ($LASTEXITCODE -ne 0) {
    throw "PyTorch kurulmus gorunuyor ancak ekran kartinda calismiyor. Kurulum onarilamadi."
}

Write-Host "[5/7] PDF to EPUB OCR ve bagimliliklar kuruluyor..." -ForegroundColor Green
& $venvPython -m pip install --upgrade $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw "Proje bagimliliklari kurulamadi." }

# Dependencies can change PyTorch constraints. Verify import and a real kernel again.
& $venvPython -c $torchProbe
if ($LASTEXITCODE -ne 0) {
    throw "Bagimlilik kurulumundan sonra PyTorch/CUDA dogrulamasi basarisiz oldu."
}

Write-Host "[6/7] Pandoc ve Poppler kontrol ediliyor..." -ForegroundColor Green
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

Write-Host "[7/7] Masaustu kisayolu hazirlaniyor..." -ForegroundColor Green
try {
    $shell = New-Object -ComObject WScript.Shell
    $powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $launchScript = Join-Path $PSScriptRoot "launch.ps1"
    $guiLauncher = Join-Path $venvPath "Scripts\pdf-to-epub-gui.exe"
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

Write-Host ""
Write-Host "Kurulum tamamlandi." -ForegroundColor Green
Write-Host "Python ortami: $venvPath" -ForegroundColor Green
Write-Host "Bundan sonra masaustundeki 'PDF to EPUB OCR' kisayolunu acmaniz yeterli." -ForegroundColor Green
