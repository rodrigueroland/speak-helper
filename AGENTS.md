# Speak Helper fork engineering instructions

- Use Python 3.12 in the repository-local `.venv`; never install packages globally.
- Preserve upstream Git history and MIT attribution. Keep `upstream` pointed at
  `https://github.com/archoor/speak-helper`.
- English is mandatory for source identifiers, comments, logs, tests, commit
  messages, and internal technical documentation.
- User-facing text must use the centralized localization layer and must be
  complete in English and French.
- Keep core policy independent of PySide6. Windows APIs, Qt widgets, clipboard
  access, audio playback, and HTTP clients belong behind focused adapters.
- Never access Qt widgets from worker threads. Communicate across threads using
  Qt signals and give every worker an explicit cancellation and cleanup path.
- Prefer deterministic event-driven clipboard capture over fixed sleeps.
- Never log clipboard contents, API keys, authorization headers, or secrets.
- Before UI changes, read the relevant skills under `.agents/skills/ui/`, in
  particular `pyqt`, `pyqt-widgets`, `pyqt-styling`, `pyqt-threading`,
  `pyqt-testing`, `qt-ui-design`, `design-system-practice`, and
  `ux-heuristics`.
- Before delivery, run formatting, Ruff, type checking, pytest, the Windows
  build, and application smoke tests. Record truthful results and blockers in
  `docs/missions/STATUS.md`.
