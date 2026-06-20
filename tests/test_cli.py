from typer.testing import CliRunner

from aicutting.cli import app


def test_version_command_prints_package_name() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AiCutting" in result.stdout
