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


def test_cut_command_dry_run_reports_artifacts(monkeypatch, tmp_path) -> None:
    from aicutting.pipeline import PipelineResult

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "clip.mp4").write_text("", encoding="utf-8")

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, dry_run, progress, kwargs
            output_dir.mkdir(parents=True, exist_ok=True)
            return PipelineResult(
                analysis=output_dir / "analysis.json",
                cut_plan=output_dir / "cut-plan.json",
                timeline=output_dir / "timeline.json",
                final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    monkeypatch.setattr("aicutting.pipeline.CutPipeline", FakePipeline)

    result = CliRunner().invoke(app, ["cut", str(input_dir), "--out", str(output_dir), "--dry-run"])

    assert result.exit_code == 0
    assert "Artifacts only" in result.stdout


def test_cut_command_forwards_vertical_aspect(monkeypatch, tmp_path) -> None:
    from aicutting.pipeline import PipelineResult

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "clip.mp4").write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, dry_run, progress
            captured.update(kwargs)
            output_dir.mkdir(parents=True, exist_ok=True)
            return PipelineResult(
                analysis=output_dir / "analysis.json",
                cut_plan=output_dir / "cut-plan.json",
                timeline=output_dir / "timeline.json",
                final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    monkeypatch.setattr("aicutting.pipeline.CutPipeline", FakePipeline)

    result = CliRunner().invoke(
        app,
        ["cut", str(input_dir), "--out", str(output_dir), "--aspect", "9:16", "--dry-run"],
    )

    assert result.exit_code == 0
    assert captured.get("aspect") == "9:16"


def test_cut_command_forwards_style_and_variants(monkeypatch, tmp_path) -> None:
    from aicutting.pipeline import PipelineResult

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "clip.mp4").write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, dry_run, progress
            captured.update(kwargs)
            output_dir.mkdir(parents=True, exist_ok=True)
            return PipelineResult(
                analysis=output_dir / "analysis.json",
                cut_plan=output_dir / "cut-plan.json",
                timeline=output_dir / "timeline.json",
                final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    monkeypatch.setattr("aicutting.pipeline.CutPipeline", FakePipeline)

    args = ["cut", str(input_dir), "--out", str(output_dir)]
    args += ["--style", "vlog", "--variants", "--dry-run"]
    result = CliRunner().invoke(app, args)

    assert result.exit_code == 0
    assert captured["style"].name == "vlog"  # type: ignore[union-attr]
    assert captured["variants"] is True


def test_cut_command_reports_pipeline_errors(monkeypatch, tmp_path) -> None:
    from aicutting.core.errors import ExternalToolError

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()

    class FailingPipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, output_dir, dry_run, progress, kwargs
            raise ExternalToolError("FFmpeg is not available on PATH.")

    monkeypatch.setattr("aicutting.pipeline.CutPipeline", FailingPipeline)

    result = CliRunner().invoke(app, ["cut", str(input_dir), "--out", str(output_dir), "--dry-run"])

    assert result.exit_code == 2
    assert "FFmpeg is not available" in result.stdout


def test_gui_command_delegates_to_gui_app(monkeypatch) -> None:
    called = False

    def fake_main() -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr("aicutting.gui.app.main", fake_main)

    result = CliRunner().invoke(app, ["gui"])

    assert result.exit_code == 0
    assert called is True


def test_gui_command_reports_friendly_gui_errors(monkeypatch) -> None:
    def fake_main() -> int:
        raise RuntimeError("Install the GUI extra")

    monkeypatch.setattr("aicutting.gui.app.main", fake_main)

    result = CliRunner().invoke(app, ["gui"])

    assert result.exit_code == 2
    assert "Install the GUI extra" in result.stdout
