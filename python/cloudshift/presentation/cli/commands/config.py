"""cloudshift config show|set -- manage configuration."""

from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cloudshift.infrastructure.config.dependency_injection import Container

app = typer.Typer(name="config", help="View and modify CloudShift configuration.")
console = Console()


def _container() -> Container:
    return Container()


@app.command()
def show(
    key: Annotated[Optional[str], typer.Argument(help="Specific config key to display.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Show current configuration (or a single key)."""
    container = _container()
    config = container.config()

    if key:
        value = config.get(key)
        if value is None:
            console.print(f"[dim]Key '{key}' not found.[/dim]")
            raise typer.Exit(code=2)
        if json_output:
            import json as _json

            console.print_json(_json.dumps({key: value}))
        else:
            console.print(f"[bold]{key}[/bold] = {value}")
    else:
        all_config = config.as_dict()
        if json_output:
            import json as _json

            console.print_json(_json.dumps(all_config))
        else:
            table = Table(title="Configuration", show_lines=True)
            table.add_column("Key", style="cyan", no_wrap=True)
            table.add_column("Value", style="green")

            for k, v in sorted(all_config.items()):
                table.add_row(k, str(v))

            console.print(table)

    raise typer.Exit(code=0)


@app.command("set")
def set_(
    key: Annotated[str, typer.Argument(help="Config key to set.")],
    value: Annotated[str, typer.Argument(help="New value.")],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Set a configuration value."""
    container = _container()
    config = container.config()

    config.set(key, value)

    if json_output:
        import json as _json

        console.print_json(_json.dumps({"key": key, "value": value, "status": "ok"}))
    else:
        console.print(f"[bold green]Set[/bold green] {key} = {value}")

    raise typer.Exit(code=0)
