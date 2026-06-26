import os
import subprocess
import sys
from pathlib import Path


def test_cli_module_can_be_run_with_python_m() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")

    completed = subprocess.run(
        [sys.executable, "-m", "aicutting.cli", "version"],
        capture_output=True,
        check=False,
        env=env,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0
    assert "AiCutting" in completed.stdout
