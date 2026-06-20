from typer.testing import CliRunner

from aicutting.cli import app


def test_version_command_prints_package_name() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AiCutting" in result.stdout


def test_cut_command_rejects_missing_input(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["cut", str(tmp_path / "missing"), "--out", str(tmp_path / "out")])
    assert result.exit_code != 0
    assert "Input folder does not exist" in result.stdout
