# Removes the managed Python environment while preserving downloaded OCR models.

param([switch] $PurgeUserData)

$ErrorActionPreference = "Stop"
$managedRoot = Join-Path $env:LocalAppData "PDF-to-EPUB-OCR"
$managedVenv = Join-Path $managedRoot "venv"

function Remove-ManagedDirectory {
    param(
        [Parameter(Mandatory = $true)] [string] $Root,
        [Parameter(Mandatory = $true)] [string] $Target
    )
    $resolvedRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $resolvedTarget = [IO.Path]::GetFullPath($Target).TrimEnd('\')
    if (-not $resolvedTarget.StartsWith($resolvedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a directory outside the managed application data folder."
    }
    if (Test-Path -LiteralPath $resolvedTarget) {
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
}

if ($PurgeUserData) {
    $expectedRoot = Join-Path $env:LocalAppData "PDF-to-EPUB-OCR"
    if ([IO.Path]::GetFullPath($managedRoot).TrimEnd('\') -ne
        [IO.Path]::GetFullPath($expectedRoot).TrimEnd('\')) {
        throw "Managed application data path validation failed."
    }
    if (Test-Path -LiteralPath $managedRoot) {
        Remove-Item -LiteralPath $managedRoot -Recurse -Force
    }
} else {
    Remove-ManagedDirectory -Root $managedRoot -Target $managedVenv
}

