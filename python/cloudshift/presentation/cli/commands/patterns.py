"""cloudshift patterns list|get|search -- manage migration patterns."""

from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from cloudshift.application.use_cases import ManagePatternsUseCase
from cloudshift.domain.value_objects.types import CloudProvider, Language
from cloudshift.infrastructure.config.dependency_injection import Container
from cloudshift.presentation.cli.formatters import error_panel, pattern_table

app = typer.Typer(name="patterns", help="Manage migration patterns.")
console = Console()


def _use_case() -> ManagePatternsUseCase:
    return Container().resolve(ManagePatternsUseCase)


@app.command()
def list_(
    source: Annotated[Optional[CloudProvider], typer.Option("--source", "-s", help="Filter by source provider.")] = None,
    target: Annotated[Optional[CloudProvider], typer.Option("--target", "-t", help="Filter by target provider.")] = None,
    language: Annotated[Optional[Language], typer.Option("--language", "-l", help="Filter by language.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """List available migration patterns."""
    use_case = _use_case()
    patterns = asyncio.run(use_case.list_patterns(source=source, target=target, language=language))

    if json_output:
        import json as _json

        console.print_json(_json.dumps([p.model_dump(mode="json") for p in patterns]))
    else:
        if not patterns:
            console.print("[dim]No patterns found.[/dim]")
            raise typer.Exit(code=0)
        console.print(pattern_table(patterns))

    raise typer.Exit(code=0)


@app.command()
def get(
    pattern_id: Annotated[str, typer.Argument(help="Pattern ID to retrieve.")],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Get details of a single pattern."""
    use_case = _use_case()
    pattern = asyncio.run(use_case.get_pattern(pattern_id))

    if pattern is None:
        console.print(error_panel("Not Found", f"Pattern '{pattern_id}' does not exist."))
        raise typer.Exit(code=2)

    if json_output:
        console.print_json(pattern.model_dump_json())
    else:
        console.print(f"[bold cyan]{pattern.name}[/bold cyan]  ({pattern.pattern_id})")
        console.print(f"  {pattern.description}\n")
        console.print(f"  {pattern.source_provider.name} -> {pattern.target_provider.name}  |  {pattern.language.name}  |  confidence {pattern.confidence:.0%}")
        console.print(f"  tags: {', '.join(pattern.tags) or '-'}  |  version {pattern.version}\n")

        if pattern.source_snippet:
            console.print(Panel(Syntax(pattern.source_snippet, "python", theme="monokai"), title="Source Snippet", border_style="yellow"))
        if pattern.target_snippet:
            console.print(Panel(Syntax(pattern.target_snippet, "python", theme="monokai"), title="Target Snippet", border_style="green"))

    raise typer.Exit(code=0)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query string.")],
    source: Annotated[Optional[CloudProvider], typer.Option("--source", "-s", help="Filter by source provider.")] = None,
    target: Annotated[Optional[CloudProvider], typer.Option("--target", "-t", help="Filter by target provider.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Search patterns by keyword."""
    use_case = _use_case()
    patterns = asyncio.run(use_case.search_patterns(query=query, source=source, target=target))

    if json_output:
        import json as _json

        console.print_json(_json.dumps([p.model_dump(mode="json") for p in patterns]))
    else:
        if not patterns:
            console.print(f"[dim]No patterns matching '{query}'.[/dim]")
            raise typer.Exit(code=0)
        console.print(pattern_table(patterns))

    raise typer.Exit(code=0)
