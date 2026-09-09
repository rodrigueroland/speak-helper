# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.0.x   | Yes       |

## Reporting a vulnerability

If you discover a security issue (e.g. API key handling, path traversal in cache, unsafe OCR payload):

1. **Do not** open a public GitHub issue with exploit details.
2. Email the maintainer or open a **private** security advisory on GitHub if the repo is published there.
3. Include steps to reproduce and impact assessment.

## API keys and data

- Speak Helper sends text to **your configured TTS/OCR endpoints** only. Edge-TTS
  uses Microsoft's online speech service.
- Store API keys in the OS keyring when possible; avoid committing `config.json` with secrets.
- Clear local cache from Settings if you shared audio derived from sensitive text.
- Structured logs record event names and text lengths, not complete clipboard/OCR
  text, API keys, or authorization headers.
