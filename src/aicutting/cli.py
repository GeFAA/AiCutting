from pathlib import Path
from typing import Annotated

import typer

from aicutting import __version__
from aicutting.core.errors import AiCuttingError
from aicutting.core.paths import resolve_cut_inputs

app = typer.Typer(help="AiCutting: local cinematic drone video cutting.")


@app.callback()
def main() -> None:
    """AiCutting command line interface."""


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

    try:
        from aicutting.pipeline import CutPipeline

        result = CutPipeline().cut(
            input_dir=inputs.input_dir,
            music_path=inputs.music_path,
            output_dir=inputs.output_dir,
            dry_run=dry_run,
        )
    except AiCuttingError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
    typer.echo(f"Analysis: {result.analysis}")
    typer.echo(f"Cut plan: {result.cut_plan}")
    typer.echo(f"Timeline: {result.timeline}")
    typer.echo(f"Final video: {result.final_video}")
