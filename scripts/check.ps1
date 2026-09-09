# Run all local quality gates from the repository root.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

uv sync --extra dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run mypy speak_helper
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$pytestBase = Join-Path $env:LOCALAPPDATA (
    "Temp\speak-helper-pytest-" + [guid]::NewGuid().ToString("N")
)
uv run pytest --basetemp $pytestBase
exit $LASTEXITCODE
