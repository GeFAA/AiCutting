from pathlib import Path


def test_public_docs_cover_first_time_user_paths() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Quick Start" in readme
    assert "Start AiCutting.cmd" in readme
    assert "aicutting cut" in readme
    assert "FFmpeg" in readme
    assert "Codex" in readme
    assert "Claude" in readme
    assert "CONTRIBUTING.md" in readme
    assert "MIT" in readme
    assert Path("docs/quickstart.md").exists()
    assert Path("CONTRIBUTING.md").exists()
