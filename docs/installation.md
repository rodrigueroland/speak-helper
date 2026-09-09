# Installation and builds

## Development

Install Python 3.11–3.13 and `uv`, then run:

```powershell
uv sync --extra dev
uv run python -m speak_helper
```

Run format, lint, mypy, and tests with `scripts/check.ps1`.

## Standalone Windows application

```powershell
.\scripts\build_win.ps1
```

The reproducible PyInstaller build produces a self-contained folder and ZIP under
`dist`. Copy the whole `SpeakHelper` folder; the target PC needs neither Python nor
`uv`. The application keeps runtime configuration outside the installation folder.

For a bounded package launch check:

```powershell
$env:SPEAK_HELPER_CONFIG_DIR = "$env:TEMP\speak-helper-smoke"
.\dist\SpeakHelper\SpeakHelper.exe --smoke-test
```

## macOS and Linux

The `pynput` fallback and Qt application structure remain cross-platform. The macOS
build script uses PyInstaller, but neither macOS nor Linux packaging has been
validated for this fork yet. macOS may require Accessibility permission for global
keyboard input; Wayland may restrict global shortcuts.
