"""cloudshift apply <plan_id> -- apply transformations from a plan."""

from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer
from rich.console import Console

from cloudshift.application.dtos.transform import TransformRequest
from cloudshift.application.use_cases import ApplyTransformationUseCase
from cloudshift.infrastructure.config.dependency_injection import Container
from cloudshift.presentation.api.plan_store import get_plan
from cloudshift.presentation.cli.formatters import diff_panel, error_panel

app = typer.Typer(name="apply", help="Apply migration transformations.")
console = Console()


@app.callback(invoke_without_command=True)
def apply(
    plan_id: Annotated[str, typer.Argument(help="ID of the migration plan to execute.")],
    step_ids: Annotated[Optional[list[str]], typer.Option("--step", "-s", help="Specific step IDs to apply.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview diffs without writing files.")] = False,
    no_backup: Annotated[bool, typer.Option("--no-backup", help="Skip creating backup files.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Apply migration transformations to source files."""
    container = Container()
    use_case: ApplyTransformationUseCase = container.resolve(ApplyTransformationUseCase)

    request = TransformRequest(
        plan_id=plan_id,
        step_ids=step_ids or [],
        dry_run=dry_run,
        backup=not no_backup,
    )

    label = "Previewing changes..." if dry_run else "Applying transformations..."
    with console.status(f"[bold green]{label}"):
        result = asyncio.run(use_case.execute(request))

    if result.success and getattr(result, "modified_file_details", None):
        plan = asyncio.run(get_plan(plan_id))
        if plan and getattr(plan, "project_id", None):
            manifest = asyncio.run(container.project_repository.get_manifest(plan.project_id))
            if manifest:
                container.project_repository.save_transform_metadata(
                    plan_id,
                    getattr(manifest, "root_path", ""),
                    getattr(manifest, "source_provider", "aws"),
                    getattr(manifest, "target_provider", "gcp"),
                    [f.model_dump() for f in result.modified_file_details],
                )
    if not result.success:
        console.print(error_panel("Apply Failed", "\n".join(result.errors)))
        raise typer.Exit(code=2)

    if json_output:
        console.print_json(result.model_dump_json())
    else:
        if dry_run:
            console.print("[bold yellow]DRY RUN[/bold yellow] -- no files were modified.\n")

        for panel in diff_panel(result):
            console.print(panel)

        console.print(
            f"\n[bold]{result.files_modified}[/bold] files modified, "
            f"[bold]{len(result.applied_steps)}[/bold] steps applied."
        )

        if result.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for err in result.errors:
                console.print(f"  - {err}")

    raise typer.Exit(code=0)
