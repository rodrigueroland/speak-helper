# Mission status

Last updated: 2026-09-09

This file is the persistent engineering handoff for the Speak Helper fork.
Statuses are factual: `TODO`, `IN PROGRESS`, `BLOCKED`, or `DONE`.

## Mission 0 — Baseline audit — DONE

- Objective: understand upstream before changing behavior.
- Decisions: preserve upstream history; use `upstream` for
  `archoor/speak-helper`; treat the Qt timer created from a Python thread as the
  primary Windows hotkey failure cause.
- Files modified: `docs/development/upstream_audit.md`, `AGENTS.md`, `.agents/`.
- Tests added: none.
- Validation: dependency sync passed; upstream tests passed 10/10 using a local
  pytest base temp; application completed a three-second offscreen smoke launch.
- Remaining issues: no baseline packaged build or interactive hotkey/audio test.

## Mission 1 — Clean development baseline — IN PROGRESS

- Objective: provide deterministic format, lint, type-check, test, run, and
  Windows build commands without unnecessary dependency churn.
- Decisions: retain uv and PyInstaller; add focused tooling only where it creates
  an enforceable quality gate.
- Files modified: `.gitignore`.
- Tests added: none yet.
- Validation: pending.
- Remaining issues: Ruff/type-check configuration and developer commands.

## Mission 2 — Internationalization — TODO
## Mission 3 — Configuration migration — TODO
## Mission 4 — Windows global hotkeys — TODO
## Mission 5 — Selected-text capture — TODO
## Mission 6 — TTS text normalization — TODO
## Mission 7 — Diagnostics — TODO
## Mission 8 — Edge-TTS — TODO
## Mission 9 — OpenAI-compatible TTS — TODO
## Mission 10 — Qwen3-TTS — TODO
## Mission 11 — Audio player UX — TODO
## Mission 12 — Clipboard modes — TODO
## Mission 13 — OCR isolation — TODO
## Mission 14 — Settings UI — TODO
## Mission 15 — System tray — TODO
## Mission 16 — Startup and single instance — TODO
## Mission 17 — Automated testing — TODO
## Mission 18 — Windows manual validation — TODO
## Mission 19 — Packaging — TODO
## Mission 20 — Documentation — TODO
## Mission 21 — GitHub CI — TODO
## Mission 22 — Release readiness — TODO

## Repository ownership

- Local branch: `main`, preserving upstream history.
- `upstream`: `https://github.com/archoor/speak-helper`.
- `origin`: intentionally not created because the user has not supplied the new
  repository name. Engineering work is not blocked; adding/renaming `origin`
  remains a single Git operation.
- License: upstream MIT license retained; derived-project attribution must remain
  in user and developer documentation.
