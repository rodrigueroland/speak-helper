# Release checklist

Do not declare version 1 ready until every required item is checked with the exact
release commit and packaged artifact.

## Automated quality

- [x] `uv sync --extra dev`
- [x] Ruff formatting check
- [x] Ruff lint
- [x] mypy
- [x] pytest (43 tests on Windows/Python 3.12)
- [x] Windows native selection probe, 10/10 consecutive captures
- [x] GitHub Actions green on Linux and Windows, Python 3.11 and 3.13

## Application behavior

- [x] Development application launches and shuts down cleanly
- [x] English UI native render inspected
- [x] French UI native render inspected
- [x] Runtime language switch persists
- [x] Live Edge-TTS English synthesis
- [x] Live Edge-TTS French synthesis
- [x] Real Qt MP3 playback starts and finishes
- [x] Windows releases the completed media file
- [x] Empty local API key omits Authorization
- [ ] Live local OpenAI-compatible server test
- [ ] Live Qwen3-TTS-compatible server test
- [ ] OCR mocked response/error tests

## Critical Windows acceptance

- [ ] PyCharm/Codex selection works at least ten consecutive times
- [ ] Stop interrupts PyCharm/Codex speech immediately
- [ ] A new selection replaces obsolete speech immediately
- [ ] Chrome and Edge selections
- [ ] Notepad selections
- [ ] Word or equivalent delayed clipboard selection
- [ ] PDF viewer multiline selection
- [ ] Terminal selection where Copy is supported
- [ ] Long text, Markdown, code blocks, French accents, and repeated text
- [ ] Default or documented alternative hotkey has no conflict on release test host

## Packaging

- [x] PyInstaller Windows folder build completes
- [x] ZIP artifact produced
- [x] Packaged executable `--smoke-test` exits with code 0
- [x] Packaged config and structured log created in isolated user directory
- [ ] Packaged selected-text hotkey test
- [ ] Packaged Edge-TTS synthesis and playback test
- [ ] Fresh Windows user-profile test
- [ ] Antivirus/signing review

## Documentation and repository

- [x] English README reflects implemented behavior
- [x] French user documentation exists
- [x] Upstream attribution and MIT license retained
- [x] Architecture, configuration, troubleshooting, and build instructions updated
- [x] Mission tracker and Windows matrix updated
- [ ] Final changelog and version number
- [ ] No secrets or generated user content in Git diff
- [ ] Release tag and published artifact
