#!/usr/bin/env python3
"""CloudShift Demo Runner — exercises the full pipeline on seed projects.

Runs each demo project through all 5 pipeline stages:
  1. Parse   — Tree-sitter AST parsing
  2. Detect  — AWS/Azure service detection
  3. Match   — Pattern matching + transformation
  4. Diff    — Unified diff generation
  5. Validate — Residual reference scanning

Reports results per-project with service detection counts, pattern match
rates, confidence scores, and validation pass/fail.
"""

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cloudshift.cloudshift_core as core


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class FileResult:
    file_name: str
    language: str
    nodes_parsed: int
    detections: list[dict] = field(default_factory=list)
    transforms: list[dict] = field(default_factory=list)
    diff_lines: int = 0
    residual_clean: bool = True
    residual_issues: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ProjectResult:
    project_name: str
    files: list[FileResult] = field(default_factory=list)
    total_parse_time_ms: float = 0
    total_detect_time_ms: float = 0
    total_transform_time_ms: float = 0
    total_diff_time_ms: float = 0
    total_validate_time_ms: float = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LANG_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tf": "hcl",
    ".json": "cloudformation",
}


def detect_language(filename: str) -> str | None:
    for ext, lang in LANG_MAP.items():
        if filename.endswith(ext):
            return lang
    return None


def detect_provider(project_name: str) -> str:
    if "aws" in project_name.lower():
        return "aws"
    if "azure" in project_name.lower():
        return "azure"
    return "unknown"


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def run_parse(source: str, language: str, file_path: str) -> tuple[object, float]:
    t0 = time.perf_counter()
    ast = core.py_parse_source(source, language, file_path)
    elapsed = (time.perf_counter() - t0) * 1000
    return ast, elapsed


def run_detect(ast_nodes: list) -> tuple[list, float]:
    t0 = time.perf_counter()
    detections = core.py_detect_services(ast_nodes)
    elapsed = (time.perf_counter() - t0) * 1000
    return detections, elapsed


def run_transform(detections: list, ast_nodes: list, language: str) -> tuple[list, float]:
    t0 = time.perf_counter()
    transforms = []
    for det in detections:
        # Find the original AST node text
        node_text = det.node_name
        for node in ast_nodes:
            if node.start_line == det.start_line:
                node_text = node.text
                break

        result = core.py_match_and_transform(
            node_type=det.construct_type,
            node_name=det.node_name,
            node_text=node_text,
            provider=det.provider,
            service=det.service,
            language=language,
            metadata=det.metadata,
        )
        if result is not None:
            transforms.append({
                "pattern_id": result.pattern_id,
                "confidence": result.confidence,
                "original_len": len(result.original_text),
                "transformed_len": len(result.transformed_text),
                "import_additions": list(result.import_additions),
                "import_removals": list(result.import_removals),
            })
    elapsed = (time.perf_counter() - t0) * 1000
    return transforms, elapsed


def run_diff(input_source: str, expected_source: str, file_name: str) -> tuple[str, float]:
    t0 = time.perf_counter()
    diff = core.py_unified_diff(input_source, expected_source, file_name)
    elapsed = (time.perf_counter() - t0) * 1000
    return diff, elapsed


def run_validate(expected_source: str, file_name: str) -> tuple[object, float]:
    t0 = time.perf_counter()
    result = core.py_scan_residual_refs(expected_source, file_name)
    elapsed = (time.perf_counter() - t0) * 1000
    return result, elapsed


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_project(project_dir: Path) -> ProjectResult:
    project_name = project_dir.name
    input_dir = project_dir / "input"
    expected_dir = project_dir / "expected"

    result = ProjectResult(project_name=project_name)

    if not input_dir.exists():
        return result

    input_files = sorted(f for f in input_dir.iterdir() if f.is_file())

    for input_file in input_files:
        language = detect_language(input_file.name)
        if language is None:
            continue

        file_result = FileResult(file_name=input_file.name, language=language, nodes_parsed=0)

        try:
            source = input_file.read_text()

            # Stage 1: Parse
            ast, parse_ms = run_parse(source, language, input_file.name)
            file_result.nodes_parsed = len(ast.nodes)
            result.total_parse_time_ms += parse_ms

            # Stage 2: Detect
            detections, detect_ms = run_detect(ast.nodes)
            file_result.detections = [
                {
                    "provider": d.provider,
                    "service": d.service,
                    "construct_type": d.construct_type,
                    "confidence": d.confidence,
                    "line": d.start_line,
                }
                for d in detections
            ]
            result.total_detect_time_ms += detect_ms

            # Stage 3: Transform (match patterns)
            transforms, transform_ms = run_transform(detections, ast.nodes, language)
            file_result.transforms = transforms
            result.total_transform_time_ms += transform_ms

            # Stage 4: Diff (if expected file exists)
            expected_file = expected_dir / input_file.name
            if expected_file.exists():
                expected_source = expected_file.read_text()
                diff, diff_ms = run_diff(source, expected_source, input_file.name)
                file_result.diff_lines = len(diff.splitlines())
                result.total_diff_time_ms += diff_ms

                # Stage 5: Validate (residual reference scan on expected output)
                validation, validate_ms = run_validate(expected_source, input_file.name)
                file_result.residual_clean = validation.is_valid
                file_result.residual_issues = [i.message for i in validation.issues]
                result.total_validate_time_ms += validate_ms

        except Exception as exc:
            file_result.errors.append(str(exc))

        result.files.append(file_result)

    return result


def print_report(results: list[ProjectResult]) -> dict:
    """Print a human-readable report and return summary dict."""
    print("=" * 80)
    print("  CLOUDSHIFT DEMO PIPELINE REPORT")
    print("=" * 80)

    summary = {
        "total_projects": len(results),
        "total_files": 0,
        "total_detections": 0,
        "total_transforms": 0,
        "total_files_validated_clean": 0,
        "total_errors": 0,
        "projects": [],
    }

    for proj in results:
        total_detections = sum(len(f.detections) for f in proj.files)
        total_transforms = sum(len(f.transforms) for f in proj.files)
        total_nodes = sum(f.nodes_parsed for f in proj.files)
        clean_files = sum(1 for f in proj.files if f.residual_clean)
        error_files = sum(1 for f in proj.files if f.errors)

        avg_confidence = 0.0
        all_confidences = [t["confidence"] for f in proj.files for t in f.transforms]
        if all_confidences:
            avg_confidence = sum(all_confidences) / len(all_confidences)

        print(f"\n{'─' * 80}")
        print(f"  PROJECT: {proj.project_name}")
        print(f"{'─' * 80}")
        print(f"  Files:       {len(proj.files)}")
        print(f"  AST Nodes:   {total_nodes}")
        print(f"  Detections:  {total_detections}")
        print(f"  Transforms:  {total_transforms}")
        print(f"  Match Rate:  {total_transforms}/{total_detections} "
              f"({total_transforms / total_detections * 100:.0f}%)" if total_detections else "  Match Rate:  N/A")
        print(f"  Avg Conf:    {avg_confidence:.2f}")
        print(f"  Validated:   {clean_files}/{len(proj.files)} clean")
        print(f"  Errors:      {error_files}")
        print(f"  Timing:      parse={proj.total_parse_time_ms:.1f}ms "
              f"detect={proj.total_detect_time_ms:.1f}ms "
              f"transform={proj.total_transform_time_ms:.1f}ms "
              f"diff={proj.total_diff_time_ms:.1f}ms "
              f"validate={proj.total_validate_time_ms:.1f}ms")

        proj_summary = {
            "name": proj.project_name,
            "files": len(proj.files),
            "detections": total_detections,
            "transforms": total_transforms,
            "match_rate_pct": round(total_transforms / total_detections * 100, 1) if total_detections else 0,
            "avg_confidence": round(avg_confidence, 3),
            "validated_clean": clean_files,
            "errors": error_files,
        }

        # Per-file details
        for fr in proj.files:
            status = "✓" if not fr.errors else "✗"
            det_count = len(fr.detections)
            trans_count = len(fr.transforms)
            valid = "clean" if fr.residual_clean else f"DIRTY({len(fr.residual_issues)})"

            services = sorted(set(d["service"] for d in fr.detections))
            svc_str = ", ".join(services) if services else "none"

            print(f"    {status} {fr.file_name:<30} "
                  f"nodes={fr.nodes_parsed:>3}  "
                  f"detect={det_count:>2}  "
                  f"transform={trans_count:>2}  "
                  f"valid={valid:<10}  "
                  f"services=[{svc_str}]")

            if fr.errors:
                for err in fr.errors:
                    print(f"      ERROR: {err}")
            if fr.residual_issues:
                for issue in fr.residual_issues[:3]:
                    print(f"      RESIDUAL: {issue}")

        summary["total_files"] += len(proj.files)
        summary["total_detections"] += total_detections
        summary["total_transforms"] += total_transforms
        summary["total_files_validated_clean"] += clean_files
        summary["total_errors"] += error_files
        summary["projects"].append(proj_summary)

    # Grand summary
    print(f"\n{'=' * 80}")
    print(f"  GRAND SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Projects:         {summary['total_projects']}")
    print(f"  Total Files:      {summary['total_files']}")
    print(f"  Total Detections: {summary['total_detections']}")
    print(f"  Total Transforms: {summary['total_transforms']}")
    if summary['total_detections']:
        print(f"  Overall Match:    {summary['total_transforms']}/{summary['total_detections']} "
              f"({summary['total_transforms'] / summary['total_detections'] * 100:.0f}%)")
    print(f"  Validated Clean:  {summary['total_files_validated_clean']}/{summary['total_files']}")
    print(f"  Errors:           {summary['total_errors']}")
    print(f"{'=' * 80}")

    return summary


def main():
    demos_dir = Path(__file__).parent
    json_output = "--json" in sys.argv

    # Load pattern catalogue
    patterns_dir = str(demos_dir.parent / "patterns")
    pattern_count = core.py_load_patterns(patterns_dir)
    print(f"Loaded {pattern_count} patterns from {patterns_dir}\n")

    # Discover demo projects
    projects = sorted(
        d for d in demos_dir.iterdir()
        if d.is_dir() and (d / "input").exists()
    )

    if not projects:
        print("No demo projects found!")
        sys.exit(1)

    print(f"Found {len(projects)} demo projects: {[p.name for p in projects]}\n")

    # Run each project
    results = []
    for project_dir in projects:
        print(f"Running: {project_dir.name} ...", flush=True)
        result = run_project(project_dir)
        results.append(result)

    # Report
    summary = print_report(results)

    if json_output:
        print("\n--- JSON Summary ---")
        print(json.dumps(summary, indent=2))

    # Exit with error if any project had errors
    sys.exit(1 if summary["total_errors"] > 0 else 0)


if __name__ == "__main__":
    main()
