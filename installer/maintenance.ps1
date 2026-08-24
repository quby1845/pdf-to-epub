# English Windows maintenance center for PDF to EPUB OCR.

param([switch] $SelfTest)

$ErrorActionPreference = "Stop"
$repository = "quby1845/pdf-to-epub"
$appRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$setupScript = Join-Path $appRoot "setup.ps1"
$launchScript = Join-Path $appRoot "launch.ps1"
$versionFile = Join-Path $appRoot "version.txt"
$currentVersion = if (Test-Path -LiteralPath $versionFile) {
    (Get-Content -LiteralPath $versionFile -Raw).Trim()
} else {
    "0.0.0"
}

function Get-ReleaseAssetName {
    param([Parameter(Mandatory = $true)] [string] $Version)
    return "pdf-to-epub-ocr-v$Version-windows-setup.exe"
}

function Compare-AppVersion {
    param(
        [Parameter(Mandatory = $true)] [string] $Installed,
        [Parameter(Mandatory = $true)] [string] $Available
    )
    return ([version]$Available).CompareTo([version]$Installed)
}

if ($SelfTest) {
    if ((Get-ReleaseAssetName -Version "1.2.3") -ne
        "pdf-to-epub-ocr-v1.2.3-windows-setup.exe") {
        throw "Release asset naming failed."
    }
    if ((Compare-AppVersion -Installed "1.2.2" -Available "1.2.3") -le 0) {
        throw "Version comparison failed."
    }
    Write-Output "PDF_TO_EPUB_MAINTENANCE_OK"
    exit 0
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()

$colors = @{
    Background = [Drawing.Color]::FromArgb(15, 20, 32)
    Card = [Drawing.Color]::FromArgb(24, 31, 46)
    Text = [Drawing.Color]::FromArgb(243, 246, 252)
    Muted = [Drawing.Color]::FromArgb(168, 179, 197)
    Primary = [Drawing.Color]::FromArgb(124, 111, 247)
    Success = [Drawing.Color]::FromArgb(98, 219, 152)
    Danger = [Drawing.Color]::FromArgb(255, 129, 120)
}

$form = New-Object Windows.Forms.Form
$form.Text = "PDF to EPUB OCR - Maintenance"
$form.Size = New-Object Drawing.Size(720, 610)
$form.MinimumSize = New-Object Drawing.Size(660, 560)
$form.StartPosition = "CenterScreen"
$form.BackColor = $colors.Background
$form.ForeColor = $colors.Text
$form.Font = New-Object Drawing.Font("Segoe UI", 10)

$title = New-Object Windows.Forms.Label
$title.Text = "PDF to EPUB OCR"
$title.Font = New-Object Drawing.Font("Segoe UI", 20, [Drawing.FontStyle]::Bold)
$title.Location = New-Object Drawing.Point(28, 22)
$title.AutoSize = $true
$form.Controls.Add($title)

$subtitle = New-Object Windows.Forms.Label
$subtitle.Text = "Maintenance Center  -  installed version $currentVersion"
$subtitle.ForeColor = $colors.Muted
$subtitle.Location = New-Object Drawing.Point(31, 61)
$subtitle.AutoSize = $true
$form.Controls.Add($subtitle)

$intro = New-Object Windows.Forms.Label
$intro.Text = "Repair the local OCR runtime, install verified updates, or remove the application."
$intro.ForeColor = $colors.Muted
$intro.Location = New-Object Drawing.Point(31, 94)
$intro.Size = New-Object Drawing.Size(640, 42)
$form.Controls.Add($intro)

$status = New-Object Windows.Forms.Label
$status.Text = "Ready"
$status.Location = New-Object Drawing.Point(31, 150)
$status.Size = New-Object Drawing.Size(640, 28)
$status.ForeColor = $colors.Success
$form.Controls.Add($status)

$progress = New-Object Windows.Forms.ProgressBar
$progress.Location = New-Object Drawing.Point(34, 181)
$progress.Size = New-Object Drawing.Size(632, 9)
$progress.Style = "Marquee"
$progress.MarqueeAnimationSpeed = 0
$form.Controls.Add($progress)

$logBox = New-Object Windows.Forms.TextBox
$logBox.Location = New-Object Drawing.Point(34, 210)
$logBox.Size = New-Object Drawing.Size(632, 235)
$logBox.Multiline = $true
$logBox.ReadOnly = $true
$logBox.ScrollBars = "Vertical"
$logBox.BackColor = $colors.Card
$logBox.ForeColor = $colors.Text
$logBox.BorderStyle = "FixedSingle"
$logBox.Font = New-Object Drawing.Font("Consolas", 9)
$form.Controls.Add($logBox)

function Add-LogLine {
    param([Parameter(Mandatory = $true)] [string] $Message)
    $logBox.AppendText("$Message`r`n")
    $logBox.SelectionStart = $logBox.TextLength
    $logBox.ScrollToCaret()
    [Windows.Forms.Application]::DoEvents()
}

function Set-Busy {
    param(
        [Parameter(Mandatory = $true)] [bool] $Busy,
        [string] $Message = "Ready"
    )
    $status.Text = $Message
    $progress.MarqueeAnimationSpeed = if ($Busy) { 28 } else { 0 }
    foreach ($button in @($openButton, $repairButton, $updateButton, $uninstallButton)) {
        $button.Enabled = -not $Busy
    }
    [Windows.Forms.Application]::DoEvents()
}

function Invoke-HiddenPowerShell {
    param([Parameter(Mandatory = $true)] [string[]] $Arguments)
    $argumentLine = ($Arguments | ForEach-Object {
        if ($_ -match '[\s"]') { '"' + $_.Replace('"', '\"') + '"' } else { $_ }
    }) -join " "
    $runId = [guid]::NewGuid().ToString("N")
    $stdoutPath = Join-Path $env:TEMP "pdf-to-epub-$runId.out.log"
    $stderrPath = Join-Path $env:TEMP "pdf-to-epub-$runId.err.log"
    try {
        $process = Start-Process `
            -FilePath "powershell.exe" `
            -ArgumentList $argumentLine `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -PassThru
        while (-not $process.HasExited) {
            [Windows.Forms.Application]::DoEvents()
            Start-Sleep -Milliseconds 100
        }
        foreach ($path in @($stdoutPath, $stderrPath)) {
            if (Test-Path -LiteralPath $path) {
                Get-Content -LiteralPath $path | ForEach-Object { Add-LogLine -Message $_ }
            }
        }
        return $process.ExitCode
    } finally {
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function New-ActionButton {
    param(
        [Parameter(Mandatory = $true)] [string] $Text,
        [Parameter(Mandatory = $true)] [int] $X,
        [Parameter(Mandatory = $true)] [Drawing.Color] $Color
    )
    $button = New-Object Windows.Forms.Button
    $button.Text = $Text
    $button.Location = New-Object Drawing.Point($X, 472)
    $button.Size = New-Object Drawing.Size(148, 46)
    $button.FlatStyle = "Flat"
    $button.FlatAppearance.BorderSize = 0
    $button.BackColor = $Color
    $button.ForeColor = [Drawing.Color]::White
    $button.Cursor = "Hand"
    $form.Controls.Add($button)
    return $button
}

$openButton = New-ActionButton -Text "Open app" -X 34 -Color $colors.Primary
$repairButton = New-ActionButton -Text "Repair" -X 194 -Color $colors.Primary
$updateButton = New-ActionButton -Text "Check for updates" -X 354 -Color $colors.Primary
$uninstallButton = New-ActionButton -Text "Uninstall" -X 514 -Color $colors.Danger

$openButton.Add_Click({
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
        "-File", $launchScript
    )
})

$repairButton.Add_Click({
    try {
        Set-Busy -Busy $true -Message "Repairing the installation..."
        Add-LogLine -Message "Validating Python, GPU runtime, dependencies, and application files."
        $exitCode = Invoke-HiddenPowerShell -Arguments @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $setupScript,
            "-Operation", "Repair", "-SkipShortcuts"
        )
        if ($exitCode -ne 0) { throw "Repair failed with exit code $exitCode." }
        Add-LogLine -Message "Repair completed successfully."
        Set-Busy -Busy $false -Message "Installation repaired successfully"
    } catch {
        Add-LogLine -Message $_.Exception.Message
        Set-Busy -Busy $false -Message "Repair failed"
        [Windows.Forms.MessageBox]::Show($_.Exception.Message, "Repair failed", "OK", "Error")
    }
})

$updateButton.Add_Click({
    try {
        Set-Busy -Busy $true -Message "Checking GitHub for updates..."
        $headers = @{ "User-Agent" = "pdf-to-epub-ocr-maintenance" }
        $release = Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$repository/releases/latest" `
            -Headers $headers
        $availableVersion = ([string]$release.tag_name).TrimStart('v')
        Add-LogLine -Message "Installed: $currentVersion; latest: $availableVersion"
        if ((Compare-AppVersion -Installed $currentVersion -Available $availableVersion) -le 0) {
            Set-Busy -Busy $false -Message "You already have the latest version"
            [Windows.Forms.MessageBox]::Show(
                "PDF to EPUB OCR $currentVersion is up to date.",
                "No update available", "OK", "Information"
            )
            return
        }

        $assetName = Get-ReleaseAssetName -Version $availableVersion
        $installerAsset = $release.assets | Where-Object { $_.name -eq $assetName } |
            Select-Object -First 1
        $checksumAsset = $release.assets | Where-Object { $_.name -eq "$assetName.sha256" } |
            Select-Object -First 1
        if (-not $installerAsset -or -not $checksumAsset) {
            throw "The release does not contain a verified Windows installer."
        }

        $downloadRoot = Join-Path $env:TEMP "pdf-to-epub-ocr-update"
        New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
        $installerPath = Join-Path $downloadRoot $assetName
        $checksumPath = "$installerPath.sha256"
        Invoke-WebRequest -Uri $installerAsset.browser_download_url -OutFile $installerPath
        Invoke-WebRequest -Uri $checksumAsset.browser_download_url -OutFile $checksumPath
        $expectedHash = ((Get-Content -LiteralPath $checksumPath -Raw).Trim() -split '\s+')[0]
        $actualHash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash
        if ($expectedHash -ne $actualHash) {
            Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
            throw "Update verification failed. The downloaded installer was not started."
        }

        Add-LogLine -Message "SHA-256 verification passed. Starting Setup..."
        Start-Process -FilePath $installerPath -ArgumentList "/maintenance=1"
        $form.Close()
    } catch {
        Add-LogLine -Message $_.Exception.Message
        Set-Busy -Busy $false -Message "Update check failed"
        [Windows.Forms.MessageBox]::Show(
            $_.Exception.Message, "Update failed", "OK", "Error"
        )
    }
})

$uninstallButton.Add_Click({
    $answer = [Windows.Forms.MessageBox]::Show(
        "Remove PDF to EPUB OCR? Downloaded OCR models will be preserved for a future reinstall.",
        "Confirm uninstall", "YesNo", "Warning"
    )
    if ($answer -ne "Yes") { return }
    $uninstaller = Get-ChildItem -LiteralPath $appRoot -Filter "unins*.exe" |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $uninstaller) {
        [Windows.Forms.MessageBox]::Show(
            "The Windows uninstaller could not be found. Run Setup again to repair it.",
            "Uninstaller not found", "OK", "Error"
        )
        return
    }
    Start-Process -FilePath $uninstaller.FullName
    $form.Close()
})

[void]$form.ShowDialog()
