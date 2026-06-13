# scripts/build_win.ps1 - Windows build script
# Usage: run from speak_helper root
#   .\scripts\build_win.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== SpeakHelper Windows build ===" -ForegroundColor Cyan
Write-Host "Working dir: $Root"

Write-Host "Generating icon.ico ..."
uv run python scripts/make_icon.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Icon generation failed." -ForegroundColor Red
    exit 1
}

if (Test-Path "dist\SpeakHelper") {
    Write-Host "Cleaning dist/SpeakHelper ..."
    Remove-Item -Recurse -Force "dist\SpeakHelper"
}
if (Test-Path "build\speak_helper") {
    Write-Host "Cleaning build/speak_helper ..."
    Remove-Item -Recurse -Force "build\speak_helper"
}

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
if (Test-Path "dist\$zipName") { Remove-Item "dist\$zipName" }
Compress-Archive -Path $outDir -DestinationPath "dist\$zipName"
Write-Host "Zip archive: dist\$zipName" -ForegroundColor Cyan
