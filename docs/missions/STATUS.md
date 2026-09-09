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

## Mission 1 — Clean development baseline — DONE

- Objective: provide deterministic format, lint, type-check, test, run, and
  Windows build commands without unnecessary dependency churn.
- Decisions: retain uv and PyInstaller; add focused tooling only where it creates
  an enforceable quality gate.
- Files modified: `.gitignore`, `pyproject.toml`, `uv.lock`, `scripts/check.ps1`.
- Tests added: none; this mission makes the existing and subsequent tests enforceable.
- Validation: Ruff formatting and lint pass; mypy passes; pytest passes on Python 3.12.
- Remaining issues: CI and the packaged Windows build are tracked by Missions 19 and 21.

## Mission 2 — Internationalization — DONE

- Objective: provide complete runtime-switchable English and French UI catalogs.
- Decisions: use one observable translation service and centralized catalogs;
  retain English technical logs.
- Files modified: `speak_helper/i18n.py` and all modules under `speak_helper/ui/`.
- Tests added: catalog parity, fallback, persistence, Settings runtime switch, and
  safe localized service-error classification.
- Validation: native Windows renders inspected in English and French; production
  UI string scan completed, including runtime-localized voice display names.
- Remaining issues: none for the current visible UI.

## Mission 3 — Configuration migration — DONE

- Objective: version configuration and preserve existing installations.
- Decisions: schema version 2; deep merge old files; detect French only on first
  launch; validate bounded and enumerated values.
- Files modified: `speak_helper/config.py`.
- Tests added: old-file migration, locale defaults, invalid values, persistence.
- Validation: migration tests pass; an existing local configuration loaded and saved.
- Remaining issues: none for schema version 2.

## Mission 4 — Windows global hotkeys — IN PROGRESS

- Objective: make all four global actions reliable and diagnosable on Windows.
- Decisions: native `RegisterHotKey` plus `MOD_NOREPEAT` on Windows; `pynput`
  fallback elsewhere; Qt queued dispatch and explicit cleanup.
- Files modified: `speak_helper/hotkey_service.py`, `speak_helper/main.py`.
- Tests added: parsing, duplicates, conflict results, dispatch, cleanup.
- Validation: native probe chord registered/unregistered; default chord conflict
  correctly returned Windows error 1409.
- Remaining issues: repeat manual validation with the user's final chosen chord.

## Mission 5 — Selected-text capture — IN PROGRESS

- Objective: transact Copy/capture/restore reliably without fixed clipboard sleeps.
- Decisions: use the Windows clipboard sequence number, preserve all Qt MIME
  formats, use a polling deadline, and suppress self-generated watcher events.
- Files modified: `speak_helper/selection_capture.py`, `clipboard_watcher.py`, `main.py`.
- Tests added: same-text capture, timeout, copy failure, restoration.
- Validation: Windows probe passed 10/10 consecutive Unicode selection cycles.
- Remaining issues: run the PyCharm/browser/Word/PDF packaged-app matrix.

## Mission 6 — TTS text normalization — DONE

- Objective: make technical prose pleasant without changing meaning.
- Decisions: conservative Markdown cleanup, configurable URL handling, preserve
  fenced code by default.
- Files modified: `speak_helper/text_normalizer.py`, `speak_helper/main.py`.
- Tests added: French accents, Unicode, Markdown, URLs, multiline code.
- Validation: all normalization tests pass.
- Remaining issues: expose advanced preprocessing options in Settings if demanded.

## Mission 7 — Diagnostics — DONE

- Objective: explain hotkey, clipboard, backend, audio, cache, and log state.
- Decisions: safe snapshots plus JSON-lines rotating logs; never include credentials
  or full clipboard/OCR text.
- Files modified: `diagnostics.py`, `logging_config.py`, Settings and composition.
- Tests added: safe snapshot/privacy coverage and a one-shot hotkey diagnostic test.
- Validation: structured events captured native conflict and clean shutdown; the
  hotkey test consumes one press without starting a selection capture.
- Remaining issues: none for the current diagnostic scope.

## Mission 8 — Edge-TTS — DONE

- Objective: retain a zero-key baseline supporting good English and French voices.
- Decisions: curated voice selector and live Test TTS action.
- Files modified: `speech_service.py`, `ui/settings_dialog.py`.
- Tests added: backend worker/cache/error tests.
- Validation: live English and French synthesis passed; real Qt playback completed.
- Remaining issues: optional dynamic voice discovery is deferred.

## Mission 9 — OpenAI-compatible TTS — DONE

- Objective: support local and remote compatible `/audio/speech` endpoints.
- Decisions: API key is optional; endpoint participates in cache identity; validate
  content type and empty responses.
- Files modified: `speech_service.py`, Settings and configuration.
- Tests added: no-key request, timeout, cache, malformed content type.
- Validation: mocked error suite and real loopback HTTP server synthesis contract pass.
- Remaining issues: none for the generic transport.

## Mission 10 — Qwen3-TTS — DONE

- Objective: connect to Qwen through an editable OpenAI-compatible local preset.
- Decisions: no PyTorch/CUDA desktop dependency; preset reuses the generic client.
- Files modified: `config.py`, `ui/settings_dialog.py`.
- Tests added: generic local no-key transport coverage.
- Validation: preset renders with a published Qwen model and voice; the real-socket
  compatible contract passes with French language metadata.
- Remaining issues: actual GPU-backed Qwen synthesis remains a release-environment gate.

## Mission 11 — Audio player UX — DONE

- Objective: implement immediate replacement, pause, resume, stop, and replay.
- Decisions: new reads discard obsolete audio; state follows Qt multimedia signals;
  clear media sources so Windows releases file handles.
- Files modified: `audio_player.py`, `main.py`, tray and dock UI.
- Tests added: pause/resume/stop state and queue replacement.
- Validation: unit tests and real Edge MP3 playback pass.
- Remaining issues: packaged-device validation remains in Mission 18.

## Mission 12 — Clipboard modes — DONE

- Objective: provide manual, ask, and automatic behavior without duplicate speech.
- Decisions: manual is the default; monitoring is disabled in manual mode; selection
  transactions suppress watcher events.
- Files modified: configuration, watcher, tray, Settings, composition.
- Tests added: selection/watcher boundaries covered by capture tests.
- Validation: mode controls render in both locales.
- Remaining issues: packaged manual UX validation.

## Mission 13 — OCR isolation — DONE

- Objective: retain OCR without burdening the primary selection workflow.
- Decisions: disabled by default, optional local-key transport, isolated worker,
  length-only logs, and shutdown cleanup.
- Files modified: `ocr_service.py`, configuration and Settings.
- Tests added: image encoding, optional authentication, valid/malformed/no-text
  responses, and cancellation coverage.
- Validation: OCR suite passes with the feature disabled by default at startup.
- Remaining issues: none for the isolated optional scope.

## Mission 14 — Settings UI — IN PROGRESS

- Objective: responsive, accessible, localized sections with separated service logic.
- Decisions: navigation plus stacked scrollable pages, semantic theme tokens, no
  fixed content positioning, keyboard focus borders, and application-wide
  light/dark/system theme resolution.
- Files modified: `ui/settings_dialog.py`, `ui/theme.py`, application composition.
- Tests added: runtime language switch and deterministic theme stylesheet tests.
- Validation: English and French native Windows renders inspected at 860 x 700.
- Remaining issues: inspect every page and dark mode at minimum size and high DPI.

## Mission 15 — System tray — DONE

- Objective: expose primary controls and visible clipboard mode in the tray.
- Decisions: localized command menu with Read, Pause/Resume, Stop, Replay, modes,
  Settings, About, and Quit.
- Files modified: `ui/tray_icon.py`.
- Tests added: exercised through application and Settings smoke runs.
- Validation: tray application smoke exits cleanly.
- Remaining issues: packaged notification behavior remains to validate.

## Mission 16 — Startup and single instance — IN PROGRESS

- Objective: ensure one instance and deterministic cleanup.
- Decisions: retain Windows mutex and explicitly stop capture, hotkeys, OCR, speech,
  and media during idempotent shutdown.
- Files modified: `main.py` and service lifecycle methods.
- Tests added: hotkey cleanup and application smoke coverage.
- Validation: development and packaged applications launched and exited cleanly;
  the Windows mutex handle is explicitly released during shutdown.
- Remaining issues: optional launch-at-login behavior.

## Mission 17 — Automated testing — IN PROGRESS

- Objective: cover critical pure logic and service boundaries without live dependencies.
- Decisions: use pytest-qt and injected registrars/clipboard adapters; reserve live
  providers for explicit probes.
- Files modified: `tests/`.
- Tests added: 62 total tests across configuration, localization, hotkeys, clipboard,
  TTS, audio, preprocessing, Settings, and legacy filtering.
- Validation: full suite passes.
- Remaining issues: more UI resize/DPI and packaged integration coverage.

## Mission 18 — Windows manual validation — IN PROGRESS

- Objective: repeatedly validate real application workflows on Windows 11.
- Decisions: maintain a factual matrix and a reusable native selection probe.
- Files modified: `docs/development/windows_test_matrix.md`,
  `scripts/windows_selection_probe.py`.
- Tests added: 10-cycle native hotkey/clipboard integration probe.
- Validation: 10/10 synthetic editor captures; Edge synthesis/playback live checks.
- Remaining issues: PyCharm/Codex and other named applications were not available
  through the UI automation surface; packaged matrix remains NOT RUN.

## Mission 19 — Packaging — DONE

- Objective: produce a reproducible standalone Windows application.
- Decisions: retain PyInstaller folder mode, bundle Qt multimedia/SVG, Edge-TTS,
  HTTP, keyring, Pillow, and pynput fallbacks; validate cleanup targets before removal.
- Files modified: `speak_helper.spec`, `scripts/build_win.ps1`, `scripts/build_mac.sh`.
- Tests added: packaged `--smoke-test` mode with isolated configuration directory.
- Validation: Windows build and ZIP succeeded; packaged executable exited 0 and
  produced config plus structured logs without a development Python runtime.
- Remaining issues: signing/antivirus and packaged workflow testing remain release tasks.

## Mission 20 — Documentation — DONE

- Objective: provide accurate primary English and French user/developer docs.
- Decisions: replace the obsolete Chinese mirror with `docs/fr/README.md`; keep
  implementation status explicit and preserve upstream attribution.
- Files modified: `README.md`, `docs/`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CHANGELOG.md`, `NOTICE.md`, `config.example.json`.
- Tests added: none.
- Validation: links and claims reviewed against the implemented paths and test matrix.
- Remaining issues: refresh screenshots and release notes for the final version tag.

## Mission 21 — GitHub CI — DONE

- Objective: keep lint, typing, tests, and Windows packaging repeatable in GitHub.
- Decisions: small Python 3.11/3.13 Linux/Windows matrix plus one Python 3.12
  packaged build/smoke job; pin uv action input.
- Files modified: `.github/workflows/ci.yml`.
- Tests added: packaged bounded launch in the Windows job.
- Validation: hosted run 34396262540 passed all four Linux/Windows quality jobs
  and the Windows packaged executable smoke job.
- Remaining issues: none for the current workflow scope.

## Mission 22 — Release readiness — IN PROGRESS

- Objective: close all quality, application, documentation, and packaged acceptance gates.
- Decisions: use a checkbox document that cannot conflate unit, development, and
  packaged validation.
- Files modified: `docs/development/release_checklist.md`.
- Tests added: none beyond prior missions.
- Validation: quality gates, live Edge synthesis/playback, build, and packaged
  smoke pass on Windows 11.
- Remaining issues: PyCharm/application matrix, live local/Qwen server, hosted CI,
  signing review, final version/changelog/tag, and published artifact.

## Repository ownership

- Local branch: `main`, preserving upstream history.
- `upstream`: `https://github.com/archoor/speak-helper`.
- `origin`: `https://github.com/rodrigueroland/speak-helper` (GitHub fork).
- License: upstream MIT license retained; derived-project attribution must remain
  in user and developer documentation.
