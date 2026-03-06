"""cloudshift scan <path> -- scan a project for cloud service usage."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from cloudshift.application.dtos.scan import ScanRequest
from cloudshift.application.use_cases import ScanProjectUseCase
from cloudshift.domain.value_objects.types import CloudProvider, Language
from cloudshift.infrastructure.config.dependency_injection import Container
from cloudshift.presentation.cli.formatters import error_panel, manifest_table

app = typer.Typer(name="scan", help="Scan a project directory for cloud service usage.")
console = Console()


@app.callback(invoke_without_command=True)
def scan(
    path: Annotated[Path, typer.Argument(help="Project root directory to scan.", exists=True, file_okay=False)],
    source: Annotated[CloudProvider, typer.Option("--source", "-s", help="Current cloud provider.")] = CloudProvider.AWS,
    target: Annotated[CloudProvider, typer.Option("--target", "-t", help="Target cloud provider.")] = CloudProvider.GCP,
    language: Annotated[Optional[list[Language]], typer.Option("--language", "-l", help="Languages to scan.")] = None,
    exclude: Annotated[Optional[list[str]], typer.Option("--exclude", "-e", help="Glob patterns to exclude.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Scan a project directory and detect cloud service usage."""
    container = Container()
    use_case: ScanProjectUseCase = container.resolve(ScanProjectUseCase)

    request = ScanRequest(
        root_path=str(path.resolve()),
        source_provider=source,
        target_provider=target,
        languages=language or [],
        exclude_patterns=exclude or [],
    )

    with console.status("[bold green]Scanning project...") as status:
        if verbose:
            status.update("[bold green]Scanning project (verbose)...")
        result = asyncio.run(use_case.execute(request))

    if result.error:
        console.print(error_panel("Scan Failed", result.error))
        raise typer.Exit(code=2)

    if json_output:
        console.print_json(result.model_dump_json())
    else:
        console.print(manifest_table(result))
        console.print(
            f"\n[bold]{result.total_files_scanned}[/bold] files scanned, "
            f"[bold]{len(result.files)}[/bold] with services, "
            f"[bold]{len(result.services_found)}[/bold] unique services detected."
        )

    raise typer.Exit(code=0)
