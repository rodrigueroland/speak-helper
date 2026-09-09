# scripts/build_win.ps1 - Windows build script
# Usage: run from speak_helper root
#   .\scripts\build_win.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Root = [System.IO.Path]::GetFullPath($Root)
Set-Location $Root

function Remove-VerifiedBuildPath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    $target = [System.IO.Path]::GetFullPath((Join-Path $Root $RelativePath))
    $workspacePrefix = $Root.TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
        [System.IO.Path]::DirectorySeparatorChar
    if (-not $target.StartsWith($workspacePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the repository: $target"
    }
    if (Test-Path -LiteralPath $target) {
        Write-Host "Cleaning $target ..."
        for ($attempt = 1; $attempt -le 10; $attempt++) {
            try {
                Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
                break
            }
            catch {
                if ($attempt -eq 10) { throw }
                Start-Sleep -Milliseconds 300
            }
        }
    }
}

Write-Host "=== SpeakHelper Windows build ===" -ForegroundColor Cyan
Write-Host "Working dir: $Root"

Write-Host "Syncing dependencies (including edge-tts) ..."
uv sync --all-extras
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependency sync failed." -ForegroundColor Red
    exit 1
}

Write-Host "Generating icon.ico ..."
uv run python scripts/make_icon.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Icon generation failed." -ForegroundColor Red
    exit 1
}

Remove-VerifiedBuildPath "dist\SpeakHelper"
Remove-VerifiedBuildPath "build\speak_helper"

$pi = uv run pyinstaller --version 2>&1
Write-Host "PyInstaller version: $pi"

Write-Host "`nBuilding..." -ForegroundColor Yellow
uv run pyinstaller speak_helper.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

$outDir = "$Root\dist\SpeakHelper"
Write-Host "`nBuild complete." -ForegroundColor Green
Write-Host "Output dir: $outDir"
Write-Host "Executable: $outDir\SpeakHelper.exe"

$zipName = "SpeakHelper-win64.zip"
if (Test-Path "dist\$zipName") { Remove-Item -LiteralPath "dist\$zipName" }
Compress-Archive -Path $outDir -DestinationPath "dist\$zipName"
Write-Host "Zip archive: dist\$zipName" -ForegroundColor Cyan
