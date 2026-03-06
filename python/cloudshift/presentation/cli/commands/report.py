"""cloudshift report <project_id> -- generate a migration audit report."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console

from cloudshift.application.use_cases import GenerateReportUseCase
from cloudshift.infrastructure.config.dependency_injection import Container
from cloudshift.presentation.cli.formatters import (
    error_panel,
    report_files_table,
    report_panel,
)

app = typer.Typer(name="report", help="Generate migration audit reports.")
console = Console()


@app.callback(invoke_without_command=True)
def report(
    project_id: Annotated[str, typer.Argument(help="Project ID to generate a report for.")],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Generate a full migration audit report."""
    container = Container()
    use_case: GenerateReportUseCase = container.resolve(GenerateReportUseCase)

    with console.status("[bold green]Generating report..."):
        result = asyncio.run(use_case.execute(project_id))

    if json_output:
        console.print_json(result.model_dump_json())
    else:
        console.print(report_panel(result))
        if result.file_summaries:
            console.print(report_files_table(result))

    raise typer.Exit(code=0)
