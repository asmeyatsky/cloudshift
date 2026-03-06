"""cloudshift plan <path> -- generate a migration plan."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from cloudshift.application.dtos.plan import PlanRequest
from cloudshift.application.use_cases import GeneratePlanUseCase
from cloudshift.infrastructure.config.dependency_injection import Container
from cloudshift.presentation.cli.formatters import error_panel

app = typer.Typer(name="plan", help="Generate a migration plan.")
console = Console()


@app.callback(invoke_without_command=True)
def plan(
    project_id: Annotated[str, typer.Argument(help="ID of the scanned project.")],
    manifest_id: Annotated[str, typer.Argument(help="ID of the scan manifest.")],
    strategy: Annotated[str, typer.Option("--strategy", help="Migration strategy: conservative | balanced | aggressive.")] = "conservative",
    max_parallel: Annotated[int, typer.Option("--max-parallel", help="Max parallel steps.")] = 4,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Generate a migration plan for a scanned project."""
    container = Container()
    use_case: GeneratePlanUseCase = container.resolve(GeneratePlanUseCase)

    request = PlanRequest(
        project_id=project_id,
        manifest_id=manifest_id,
        strategy=strategy,
        max_parallel=max_parallel,
    )

    with console.status("[bold green]Generating migration plan..."):
        result = asyncio.run(use_case.execute(request))

    if result.error:
        console.print(error_panel("Plan Failed", result.error))
        raise typer.Exit(code=2)

    if json_output:
        console.print_json(result.model_dump_json())
    else:
        table = Table(title=f"Migration Plan  [{result.plan_id}]", show_lines=True)
        table.add_column("Step", style="dim", no_wrap=True)
        table.add_column("File", style="cyan")
        table.add_column("Pattern", style="magenta")
        table.add_column("Description")
        table.add_column("Confidence", justify="right")
        table.add_column("Depends On", style="dim")

        for step in result.steps:
            conf_style = "green" if step.confidence >= 0.8 else "yellow" if step.confidence >= 0.5 else "red"
            table.add_row(
                step.step_id,
                step.file_path,
                step.pattern_id,
                step.description,
                Text(f"{step.confidence:.0%}", style=conf_style),
                ", ".join(step.depends_on) or "-",
            )

        console.print(table)
        console.print(
            f"\n[bold]{result.estimated_files_changed}[/bold] files to change, "
            f"estimated confidence [bold]{result.estimated_confidence:.0%}[/bold]."
        )

        if result.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for w in result.warnings:
                console.print(f"  - {w}")

    raise typer.Exit(code=0)
