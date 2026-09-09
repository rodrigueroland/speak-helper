"""Store a TTS API key through Speak Helper's configuration abstraction."""

from __future__ import annotations

import sys

from speak_helper.config import Config


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("Usage: python write_api_key.py <API-key>")
        return 1
    config = Config()
    config.api_key = sys.argv[1]
    config.save()
    print(f"API key stored for Speak Helper in {config.config_dir}")
    print("Restart Speak Helper to apply the change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
