"""cloudshift validate <plan_id> -- validate applied transformations."""

from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer
from rich.console import Console

from cloudshift.application.dtos.validation import ValidationRequest
from cloudshift.application.use_cases import ValidateTransformationUseCase
from cloudshift.infrastructure.config.dependency_injection import Container
from cloudshift.presentation.cli.formatters import (
    error_panel,
    validation_summary,
    validation_table,
)

app = typer.Typer(name="validate", help="Validate applied transformations.")
console = Console()


@app.callback(invoke_without_command=True)
def validate(
    plan_id: Annotated[str, typer.Argument(help="ID of the executed plan to validate.")],
    skip_ast: Annotated[bool, typer.Option("--skip-ast", help="Skip AST equivalence checks.")] = False,
    skip_refs: Annotated[bool, typer.Option("--skip-refs", help="Skip residual reference checks.")] = False,
    skip_sdk: Annotated[bool, typer.Option("--skip-sdk", help="Skip SDK surface coverage checks.")] = False,
    run_tests: Annotated[bool, typer.Option("--run-tests", help="Run the project test suite.")] = False,
    test_command: Annotated[Optional[str], typer.Option("--test-cmd", help="Custom test command.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Validate that transformations are correct and complete."""
    container = Container()
    use_case: ValidateTransformationUseCase = container.resolve(ValidateTransformationUseCase)

    request = ValidationRequest(
        plan_id=plan_id,
        check_ast_equivalence=not skip_ast,
        check_residual_refs=not skip_refs,
        check_sdk_surface=not skip_sdk,
        run_tests=run_tests,
        test_command=test_command,
    )

    with console.status("[bold green]Validating transformations..."):
        result = asyncio.run(use_case.execute(request))

    if result.error:
        console.print(error_panel("Validation Error", result.error))
        raise typer.Exit(code=2)

    if json_output:
        console.print_json(result.model_dump_json())
    else:
        if result.issues:
            console.print(validation_table(result))
        console.print(validation_summary(result))

    raise typer.Exit(code=0 if result.passed else 1)
