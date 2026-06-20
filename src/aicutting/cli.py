import typer

from aicutting import __version__

app = typer.Typer(help="AiCutting: local cinematic drone video cutting.")


@app.callback()
def main() -> None:
    """AiCutting command line interface."""


@app.command()
def version() -> None:
    """Print the installed AiCutting version."""
    typer.echo(f"AiCutting {__version__}")
