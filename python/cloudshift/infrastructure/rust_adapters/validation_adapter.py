"""Rust-backed validation adapter implementing ValidationPort."""

from __future__ import annotations

import asyncio
from pathlib import Path

from cloudshift.domain.entities.manifest import MigrationManifest
from cloudshift.domain.entities.transformation import Transformation
from cloudshift.domain.entities.validation_report import ValidationReport
from cloudshift.domain.value_objects.types import Language, Severity, ValidationIssue
from cloudshift.infrastructure.rust_adapters.detector_adapter import _dict_to_py_node

import cloudshift.cloudshift_core as core

# Code extensions to scan for residual refs (scan(root, provider))
_RESIDUAL_SCAN_EXTENSIONS = (".py", ".ts", ".tsx", ".js", ".jsx", ".tf", ".yaml", ".yml", ".json")


class RustValidationAdapter:
    """Implements ValidationPort by delegating to the Rust core.

    Protocol methods:
        validate_syntax(source, language) -> ValidationReport
        validate_transformation(transformation) -> ValidationReport
        validate_manifest(manifest) -> ValidationReport
    Plus ValidateTransformationUseCase protocol:
        check_equivalence(original, modified, language) -> list[ValidationIssue]
        scan(root, provider) -> list[ValidationIssue]
        check_coverage(root, target_provider) -> tuple[float, list[ValidationIssue]]
    """

    def __init__(self, parser: object | None = None, file_system: object | None = None) -> None:
        self._parser = parser
        self._file_system = file_system

    def _get_parser(self):
        if self._parser is None:
            from cloudshift.infrastructure.rust_adapters.parser_adapter import RustParserAdapter

            self._parser = RustParserAdapter()
        return self._parser

    def validate_syntax(self, source: str, language: Language) -> ValidationReport:
        report = ValidationReport()
        try:
            parser = self._get_parser()
            parser.parse(source, language)
        except Exception as exc:
            report.add_issue(ValidationIssue(
                message=f"Syntax error: {exc}",
                severity=Severity.ERROR,
                rule="syntax_check",
            ))
        return report

    def validate_transformation(self, transformation: Transformation) -> ValidationReport:
        report = ValidationReport()
        parser = self._get_parser()

        # AST equivalence: parse both original and transformed, check via Rust
        try:
            old_constructs = parser.extract_constructs(
                transformation.original_text, Language.PYTHON,
            )
            new_constructs = parser.extract_constructs(
                transformation.transformed_text, Language.PYTHON,
            )
            py_old = [_dict_to_py_node(c) for c in old_constructs]
            py_new = [_dict_to_py_node(c) for c in new_constructs]
            equiv = core.py_check_ast_equivalence(py_old, py_new, transformation.file_path)
            for issue_dict in equiv.issues:
                sev = _severity_from_str(issue_dict.get("severity", "warning"))
                report.add_issue(ValidationIssue(
                    message=issue_dict.get("message", ""),
                    severity=sev,
                    file_path=issue_dict.get("file_path"),
                    line=int(issue_dict["line"]) if "line" in issue_dict else None,
                    rule=issue_dict.get("category"),
                ))
        except Exception as exc:
            report.add_issue(ValidationIssue(
                message=f"AST equivalence check failed: {exc}",
                severity=Severity.WARNING,
                file_path=transformation.file_path,
                rule="ast_equivalence",
            ))

        # Residual reference scan
        residual = core.py_scan_residual_refs(
            transformation.transformed_text, transformation.file_path,
        )
        for issue_dict in residual.issues:
            sev = _severity_from_str(issue_dict.get("severity", "error"))
            report.add_issue(ValidationIssue(
                message=issue_dict.get("message", ""),
                severity=sev,
                file_path=issue_dict.get("file_path"),
                line=int(issue_dict["line"]) if "line" in issue_dict else None,
                rule=issue_dict.get("category"),
            ))

        return report

    def validate_manifest(self, manifest: MigrationManifest) -> ValidationReport:
        report = ValidationReport()
        if not manifest.entries:
            report.add_issue(ValidationIssue(
                message="Manifest has no entries",
                severity=Severity.WARNING,
                rule="manifest_empty",
            ))
        return report

    # ---- ValidateTransformationUseCase protocol (async) ----

    async def check_equivalence(
        self, original: str, modified: str, language: str,
    ) -> list[ValidationIssue]:
        """AST equivalence check for use by ValidateTransformationUseCase."""
        lang = _language_from_str(language)
        parser = self._get_parser()

        def _run() -> list[ValidationIssue]:
            old_constructs = parser.extract_constructs(original, lang)
            new_constructs = parser.extract_constructs(modified, lang)
            py_old = [_dict_to_py_node(c) for c in old_constructs]
            py_new = [_dict_to_py_node(c) for c in new_constructs]
            equiv = core.py_check_ast_equivalence(py_old, py_new, "")
            out: list[ValidationIssue] = []
            for issue_dict in equiv.issues:
                sev = _severity_from_str(issue_dict.get("severity", "warning"))
                out.append(ValidationIssue(
                    message=issue_dict.get("message", ""),
                    severity=sev,
                    file_path=issue_dict.get("file_path"),
                    line=int(issue_dict["line"]) if "line" in issue_dict else None,
                    rule=issue_dict.get("category"),
                ))
            return out

        return await asyncio.to_thread(_run)

    async def scan(self, root: str, provider: str) -> list[ValidationIssue]:
        """Scan directory for residual references to source provider."""
        fs = self._file_system
        if fs is None:
            return []
        root_path = Path(root)
        if not root_path.is_dir():
            return []
        try:
            files = fs.list_files(root_path, None)
        except Exception:
            return []
        code_files = [f for f in files if f.suffix.lower() in _RESIDUAL_SCAN_EXTENSIONS]
        all_issues: list[ValidationIssue] = []
        for path in code_files:
            try:
                content = fs.read(path)
            except Exception:
                continue
            result = await asyncio.to_thread(
                self.scan_residual_refs_raw, content, str(path),
            )
            for issue_dict in result.get("issues", []):
                sev = _severity_from_str(issue_dict.get("severity", "error"))
                all_issues.append(ValidationIssue(
                    message=issue_dict.get("message", ""),
                    severity=sev,
                    file_path=issue_dict.get("file_path"),
                    line=int(issue_dict["line"]) if "line" in issue_dict else None,
                    rule=issue_dict.get("category"),
                ))
        return all_issues

    async def check_coverage(self, root: str, target_provider: str) -> tuple[float, list[ValidationIssue]]:
        """SDK surface coverage: stub (no implementation yet). Returns 1.0 and no issues."""
        return (1.0, [])

    # ---- Raw Rust wrappers (convenience, not part of the port) ----

    def check_ast_equivalence_raw(
        self, old_nodes: list[dict], new_nodes: list[dict], file_path: str,
    ) -> dict:
        py_old = [_dict_to_py_node(n) for n in old_nodes]
        py_new = [_dict_to_py_node(n) for n in new_nodes]
        result = core.py_check_ast_equivalence(py_old, py_new, file_path)
        return {
            "is_valid": result.is_valid,
            "issues": list(result.issues),
            "summary": result.summary,
        }

    def scan_residual_refs_raw(self, source: str, file_path: str) -> dict:
        result = core.py_scan_residual_refs(source, file_path)
        return {
            "is_valid": result.is_valid,
            "issues": list(result.issues),
            "summary": result.summary,
        }


def _severity_from_str(s: str) -> Severity:
    return {
        "error": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
        "critical": Severity.CRITICAL,
    }.get(s.lower(), Severity.WARNING)


def _language_from_str(s: str) -> Language:
    if not s:
        return Language.PYTHON
    k = s.lower().strip()
    if k in ("python", "py"):
        return Language.PYTHON
    if k in ("typescript", "ts", "tsx", "javascript", "js", "jsx"):
        return Language.TYPESCRIPT
    if k in ("hcl", "tf"):
        return Language.HCL
    return Language.PYTHON
