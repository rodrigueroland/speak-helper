"""Compatibility launcher tests."""

from pathlib import Path


def test_root_launcher_delegates_to_package_entrypoint() -> None:
    launcher = Path(__file__).parents[1] / "main.py"
    source = launcher.read_text(encoding="utf-8")

    assert "from speak_helper.main import main" in source
    assert 'if __name__ == "__main__":' in source
