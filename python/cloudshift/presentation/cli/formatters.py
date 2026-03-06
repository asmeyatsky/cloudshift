"""Rich formatters for CLI output: tables, panels, and syntax-highlighted diffs."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from cloudshift.application.dtos.pattern import PatternDTO
from cloudshift.application.dtos.report import ReportDTO
from cloudshift.application.dtos.scan import ScanResult
from cloudshift.application.dtos.transform import TransformResult
from cloudshift.application.dtos.validation import ValidationResult
from cloudshift.domain.value_objects.types import Severity

console = Console()

_SEVERITY_COLORS: dict[Severity, str] = {
    Severity.INFO: "blue",
    Severity.WARNING: "yellow",
    Severity.ERROR: "red",
    Severity.CRITICAL: "bold red",
}


# ---------------------------------------------------------------------------
# ManifestTable
# ---------------------------------------------------------------------------

def manifest_table(result: ScanResult) -> Table:
    """Rich table showing file, service, confidence, status."""
    table = Table(
        title=f"Scan Results  [{result.total_files_scanned} files scanned]",
        show_lines=True,
    )
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Language", style="magenta")
    table.add_column("Services", style="green")
    table.add_column("Confidence", justify="right")
    table.add_column("Lines", justify="right", style="dim")

    for entry in result.files:
        conf = entry.confidence
        conf_style = "green" if conf >= 0.8 else "yellow" if conf >= 0.5 else "red"
        table.add_row(
            entry.path,
            entry.language.name if entry.language else "-",
            ", ".join(entry.services_detected) or "-",
            Text(f"{conf:.0%}", style=conf_style),
            str(entry.line_count),
        )

    return table


# ---------------------------------------------------------------------------
# DiffPanel
# ---------------------------------------------------------------------------

def diff_panel(result: TransformResult) -> list[Panel]:
    """Rich panels with syntax-highlighted diffs for each modified file."""
    panels: list[Panel] = []
    for diff in result.diffs:
        lines: list[str] = []
        for hunk in diff.hunks:
            lines.append(f"@@ -{hunk.start_line} +{hunk.end_line} @@")
            for line in hunk.original_text.splitlines():
                lines.append(f"- {line}")
            for line in hunk.modified_text.splitlines():
                lines.append(f"+ {line}")
            lines.append("")

        syntax = Syntax(
            "\n".join(lines),
            "diff",
            theme="monokai",
            line_numbers=True,
        )
        title = f"[bold]{diff.file_path}[/bold]  {diff.original_hash[:8]} -> {diff.modified_hash[:8]}"
        panels.append(Panel(syntax, title=title, border_style="blue"))

    return panels


# ---------------------------------------------------------------------------
# ValidationTable
# ---------------------------------------------------------------------------

def validation_table(result: ValidationResult) -> Table:
    """Rich table showing issues with severity colors."""
    table = Table(title="Validation Results", show_lines=True)
    table.add_column("Severity", width=10)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Line", justify="right", width=6)
    table.add_column("Rule", style="dim")
    table.add_column("Message")

    for issue in result.issues:
        color = _SEVERITY_COLORS.get(issue.severity, "white")
        table.add_row(
            Text(issue.severity.name, style=color),
            issue.file_path or "-",
            str(issue.line) if issue.line is not None else "-",
            issue.rule or "-",
            issue.message,
        )

    return table


def validation_summary(result: ValidationResult) -> Panel:
    """Panel summarising validation outcome."""
    status = "[bold green]PASSED[/bold green]" if result.passed else "[bold red]FAILED[/bold red]"
    lines = [
        f"Status: {status}",
        f"Issues: {len(result.issues)}",
        f"Residual refs: {result.residual_refs_found}",
        f"SDK coverage: {result.sdk_coverage:.0%}",
    ]
    if result.ast_equivalent is not None:
        lines.append(f"AST equivalent: {'yes' if result.ast_equivalent else 'no'}")
    if result.tests_passed is not None:
        lines.append(f"Tests passed: {'yes' if result.tests_passed else 'no'}")

    return Panel("\n".join(lines), title="Validation Summary", border_style="green" if result.passed else "red")


# ---------------------------------------------------------------------------
# PatternTable
# ---------------------------------------------------------------------------

def pattern_table(patterns: list[PatternDTO]) -> Table:
    """Rich table showing patterns with ID, name, services, confidence."""
    table = Table(title=f"Patterns ({len(patterns)})", show_lines=True)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Source", style="yellow")
    table.add_column("Target", style="green")
    table.add_column("Language", style="magenta")
    table.add_column("Confidence", justify="right")
    table.add_column("Tags", style="dim")

    for p in patterns:
        conf_style = "green" if p.confidence >= 0.8 else "yellow" if p.confidence >= 0.5 else "red"
        table.add_row(
            p.pattern_id,
            p.name,
            p.source_provider.name,
            p.target_provider.name,
            p.language.name,
            Text(f"{p.confidence:.0%}", style=conf_style),
            ", ".join(p.tags) or "-",
        )

    return table


# ---------------------------------------------------------------------------
# ReportPanel
# ---------------------------------------------------------------------------

def report_panel(report: ReportDTO) -> Panel:
    """Rich panel with summary statistics for the migration report."""
    status_style = "green" if report.validation_passed else "red"
    conf_style = "green" if report.overall_confidence >= 0.8 else "yellow" if report.overall_confidence >= 0.5 else "red"

    lines = [
        f"[bold]Project:[/bold]       {report.project_id}",
        f"[bold]Migration:[/bold]     {report.source_provider.name} -> {report.target_provider.name}",
        f"[bold]Generated:[/bold]     {report.generated_at:%Y-%m-%d %H:%M:%S}",
        "",
        f"[bold]Total files:[/bold]   {report.total_files}",
        f"[bold]Files changed:[/bold] {report.files_changed}",
        f"[bold]Patterns:[/bold]      {report.patterns_applied}",
        f"[bold]Validation:[/bold]    [{status_style}]{'PASSED' if report.validation_passed else 'FAILED'}[/{status_style}]",
        f"[bold]Confidence:[/bold]    [{conf_style}]{report.overall_confidence:.0%}[/{conf_style}]",
    ]

    if report.warnings:
        lines.append("")
        lines.append("[bold yellow]Warnings:[/bold yellow]")
        for w in report.warnings:
            lines.append(f"  - {w}")

    if report.notes:
        lines.append("")
        lines.append(f"[bold]Notes:[/bold] {report.notes}")

    return Panel("\n".join(lines), title="Migration Report", border_style="blue")


def report_files_table(report: ReportDTO) -> Table:
    """Per-file breakdown table for the report."""
    table = Table(title="File Summary", show_lines=True)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Services Migrated", style="green")
    table.add_column("Issues", justify="right")
    table.add_column("Confidence", justify="right")

    for fs in report.file_summaries:
        conf_style = "green" if fs.confidence >= 0.8 else "yellow" if fs.confidence >= 0.5 else "red"
        issue_style = "green" if fs.issues == 0 else "red"
        table.add_row(
            fs.path,
            ", ".join(fs.services_migrated) or "-",
            Text(str(fs.issues), style=issue_style),
            Text(f"{fs.confidence:.0%}", style=conf_style),
        )

    return table


# ---------------------------------------------------------------------------
# Error panel
# ---------------------------------------------------------------------------

def error_panel(title: str, message: str) -> Panel:
    """Render a rich error panel."""
    return Panel(f"[bold red]{message}[/bold red]", title=title, border_style="red")
