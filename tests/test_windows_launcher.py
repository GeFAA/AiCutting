from pathlib import Path


def test_windows_launcher_is_double_click_friendly() -> None:
    launcher = Path("Start AiCutting.cmd")

    assert launcher.exists()
    text = launcher.read_text(encoding="utf-8")

    assert "@echo off" in text
    assert "PYTHONPATH=%CD%\\src" in text
    assert "import aicutting" in text
    assert "py -3 -m aicutting.cli gui" in text
    assert "py -3 -m venv .venv" in text
    assert 'pip install -e ".[gui]"' in text
    assert "-m aicutting.cli gui" in text
    assert "pause" in text.lower()
