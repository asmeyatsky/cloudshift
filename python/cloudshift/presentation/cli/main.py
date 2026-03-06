"""CloudShift CLI -- main Typer application with all command groups."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

import cloudshift
from cloudshift.presentation.cli.commands import apply, config, patterns, plan, report, scan, validate

console = Console()

app = typer.Typer(
    name="cloudshift",
    help="CloudShift -- cloud migration toolkit powered by pattern matching and LLMs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)

# ---------------------------------------------------------------------------
# Register command groups
# ---------------------------------------------------------------------------

app.add_typer(scan.app, name="scan", help="Scan a project for cloud service usage.")
app.add_typer(plan.app, name="plan", help="Generate a migration plan.")
app.add_typer(apply.app, name="apply", help="Apply migration transformations.")
app.add_typer(validate.app, name="validate", help="Validate applied transformations.")
app.add_typer(patterns.app, name="patterns", help="Manage migration patterns.")
app.add_typer(report.app, name="report", help="Generate migration audit reports.")
app.add_typer(config.app, name="config", help="View and modify configuration.")


# ---------------------------------------------------------------------------
# Global options via callback
# ---------------------------------------------------------------------------

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"cloudshift {cloudshift.__version__}")
        raise typer.Exit(code=0)


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Enable JSON output mode globally.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output.")] = False,
) -> None:
    """CloudShift -- cloud migration toolkit."""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def cli() -> None:
    """Entry point for ``cloudshift`` console script."""
    app()


if __name__ == "__main__":
    cli()
