"""Main CLI application for drift."""

import typer

from drift.cli.commands import analyze

# Create the main Typer app
app = typer.Typer(
    name="drift",
    help=(
        "AI agent conversation drift analyzer - identifies gaps between "
        "what AI agents did and what users wanted"
    ),
    add_completion=False,
)

# Register commands
app.command(name="analyze")(analyze.analyze_command)


def version_callback(value: bool) -> None:
    """Handle --version flag."""
    if value:
        print("drift version 0.1.0")
        raise typer.Exit(0)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Drift - AI agent conversation drift analyzer."""
    pass


if __name__ == "__main__":
    app()
