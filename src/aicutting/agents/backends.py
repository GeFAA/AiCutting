import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentBackend:
    name: str
    executable: str | None
    available: bool


def detect_agent_backends() -> list[AgentBackend]:
    backends: list[AgentBackend] = []
    for name in ("codex", "claude"):
        executable = shutil.which(name)
        backends.append(
            AgentBackend(name=name, executable=executable, available=executable is not None)
        )
    return backends
