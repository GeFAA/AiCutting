import contextlib
import sys
from pathlib import Path
from typing import Annotated

import typer

from aicutting import __version__
from aicutting.core.errors import AiCuttingError
from aicutting.core.paths import resolve_cut_inputs

app = typer.Typer(help="AiCutting: local cinematic drone video cutting.")


def _ensure_utf8_streams() -> None:
    # The live view and progress messages use ✓/·/spinner glyphs; a legacy Windows code page
    # (cp1252) cannot encode them and rich would crash mid-run. Force UTF-8 where supported.
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError, OSError):
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


@app.callback()
def main() -> None:
    """AiCutting command line interface."""
    _ensure_utf8_streams()


@app.command()
def version() -> None:
    """Print the installed AiCutting version."""
    typer.echo(f"AiCutting {__version__}")


@app.command()
def gui() -> None:
    """Launch AiCutting Studio."""
    try:
        from aicutting.gui.app import main as run_gui

        exit_code = run_gui()
    except RuntimeError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
    raise typer.Exit(code=exit_code)


@app.command()
def cut(
    input_dir: Annotated[Path, typer.Argument(help="Folder containing drone videos.")],
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output folder for render and artifacts."),
    ],
    music: Annotated[
        Path | None,
        typer.Option("--music", "-m", help="Optional music file or folder."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Create artifacts without rendering video."),
    ] = False,
) -> None:
    """Run the automatic cinematic cut pipeline."""
    try:
        inputs = resolve_cut_inputs(input_dir=input_dir, music_path=music, output_dir=out)
    except AiCuttingError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc

    from aicutting.pipeline import CutPipeline
    from aicutting.tui import RunReporter

    try:
        with RunReporter() as reporter:
            result = CutPipeline().cut(
                input_dir=inputs.input_dir,
                music_path=inputs.music_path,
                output_dir=inputs.output_dir,
                dry_run=dry_run,
                progress=reporter,
            )
    except AiCuttingError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
    _print_summary(result.output_dir, result.final_video, dry_run=dry_run)


def _print_summary(output_dir: Path, final_video: Path, dry_run: bool) -> None:
    from rich.console import Console
    from rich.panel import Panel

    report = output_dir / "report.html"
    lines = [f"[bold]Output[/]   {output_dir}"]
    if report.exists():
        lines.append(f"[bold]Report[/]   {report}")
        lines.append("[dim]         open report.html to see every shot the AI kept and why[/]")
    if dry_run:
        lines.append("[dim]Artifacts only (dry run). Run without --dry-run to render the video.[/]")
    else:
        lines.append(f"[bold]Video[/]    {final_video}")
    Console().print(Panel("\n".join(lines), title="Done", border_style="green", expand=False))


if __name__ == "__main__":
    app()
