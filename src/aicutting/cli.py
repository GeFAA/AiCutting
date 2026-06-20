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

    typer.echo(f"Input: {inputs.input_dir}")
    typer.echo(f"Music: {inputs.music_path if inputs.music_path else 'none'}")
    typer.echo(f"Output: {inputs.output_dir}")
    typer.echo(f"Dry run: {dry_run}")
