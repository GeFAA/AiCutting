import shutil

import pytest

from aicutting.agents.backends import AgentBackend, detect_agent_backends


def test_detect_agent_backends_finds_codex_and_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        return {"codex": "C:/bin/codex.exe", "claude": "C:/bin/claude.exe"}.get(name)

    monkeypatch.setattr(shutil, "which", fake_which)

    assert detect_agent_backends() == [
        AgentBackend(name="codex", executable="C:/bin/codex.exe", available=True),
        AgentBackend(name="claude", executable="C:/bin/claude.exe", available=True),
    ]


def test_detect_agent_backends_reports_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)

    backends = detect_agent_backends()

    assert [backend.available for backend in backends] == [False, False]
