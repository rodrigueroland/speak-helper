"""Compatibility launcher tests."""

from pathlib import Path
from xml.etree import ElementTree


def test_root_launcher_delegates_to_package_entrypoint() -> None:
    launcher = Path(__file__).parents[1] / "main.py"
    source = launcher.read_text(encoding="utf-8")

    assert "from speak_helper.main import main" in source
    assert 'if __name__ == "__main__":' in source


def test_pycharm_run_configuration_uses_the_compatibility_script() -> None:
    project = Path(__file__).parents[1]
    configuration = ElementTree.parse(project / ".run" / "Speak Helper.run.xml").getroot()
    options = {
        option.attrib["name"]: option.attrib.get("value", "")
        for option in configuration.iter("option")
    }

    assert options["SCRIPT_NAME"] == "$PROJECT_DIR$/main.py"
    assert options["WORKING_DIRECTORY"] == "$PROJECT_DIR$"
    assert "MODULE_NAME" not in options
