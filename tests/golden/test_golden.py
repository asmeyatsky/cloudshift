"""Golden tests: parse -> detect -> match -> transform for each fixture."""
import pytest
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
EXPECTED_DIR = Path(__file__).parent / "expected"

# Collect all input files that have a corresponding expected file
GOLDEN_CASES = sorted(
    p.stem
    for p in INPUT_DIR.iterdir()
    if p.is_file() and (EXPECTED_DIR / p.name).exists()
)


def _detect_language(filename: str) -> str:
    if filename.endswith(".py"):
        return "python"
    if filename.endswith(".ts"):
        return "typescript"
    if filename.endswith(".tf"):
        return "hcl"
    if filename.endswith(".json"):
        return "cloudformation"
    return "unknown"


def _detect_provider_from_name(name: str) -> str:
    if name.startswith("aws_") or name.startswith("aws-"):
        return "aws"
    if name.startswith("azure_") or name.startswith("azure-"):
        return "azure"
    return "unknown"


@pytest.fixture(scope="module")
def patterns_loaded():
    from cloudshift.cloudshift_core import py_load_patterns
    count = py_load_patterns("patterns")
    assert count >= 50, f"Expected >=50 patterns, got {count}"
    return count


class TestGoldenParsing:
    """Verify that all golden input files parse without errors."""

    @pytest.mark.parametrize("case", GOLDEN_CASES)
    def test_parse_input(self, case):
        from cloudshift.cloudshift_core import py_parse_source

        input_file = INPUT_DIR / f"{case}.py"
        if not input_file.exists():
            input_file = INPUT_DIR / f"{case}.ts"
        if not input_file.exists():
            input_file = INPUT_DIR / f"{case}.tf"
        if not input_file.exists():
            input_file = INPUT_DIR / f"{case}.json"

        source = input_file.read_text()
        lang = _detect_language(input_file.name)
        ast = py_parse_source(source, lang, input_file.name)
        assert ast.language == lang
        assert len(ast.nodes) > 0, f"No AST nodes parsed from {input_file.name}"


class TestGoldenDetection:
    """Verify that service detection finds the expected cloud provider."""

    @pytest.mark.parametrize("case", GOLDEN_CASES)
    def test_detect_provider(self, case):
        from cloudshift.cloudshift_core import py_parse_source, py_detect_services

        input_file = next(INPUT_DIR.glob(f"{case}.*"))
        source = input_file.read_text()
        lang = _detect_language(input_file.name)
        ast = py_parse_source(source, lang, input_file.name)
        detections = py_detect_services(ast.nodes)

        expected_provider = _detect_provider_from_name(case)
        if expected_provider != "unknown":
            providers = {d.provider for d in detections}
            assert expected_provider in providers, (
                f"Expected provider '{expected_provider}' not found in detections. "
                f"Got: {providers}"
            )


def _find_node_text(ast_nodes, detection):
    """Find the original AST node text that corresponds to a detection."""
    for node in ast_nodes:
        if node.start_line == detection.start_line:
            return node.text
    # Fallback: use node_name
    return detection.node_name


class TestGoldenTransform:
    """Verify that at least one construct per golden case gets a pattern match."""

    @pytest.mark.parametrize("case", GOLDEN_CASES)
    def test_has_matching_pattern(self, case, patterns_loaded):
        from cloudshift.cloudshift_core import (
            py_parse_source,
            py_detect_services,
            py_match_and_transform,
        )

        input_file = next(INPUT_DIR.glob(f"{case}.*"))
        source = input_file.read_text()
        lang = _detect_language(input_file.name)
        ast = py_parse_source(source, lang, input_file.name)
        detections = py_detect_services(ast.nodes)

        transforms = []
        for detection in detections:
            node_text = _find_node_text(ast.nodes, detection)
            result = py_match_and_transform(
                node_type=detection.construct_type,
                node_name=detection.node_name,
                node_text=node_text,
                provider=detection.provider,
                service=detection.service,
                language=lang,
                metadata=detection.metadata,
            )
            if result is not None:
                transforms.append(result)

        assert len(transforms) > 0, (
            f"No pattern matched any construct in {case}. "
            f"Detections: {[(d.provider, d.service, d.construct_type) for d in detections]}"
        )

    @pytest.mark.parametrize("case", GOLDEN_CASES)
    def test_transform_confidence(self, case, patterns_loaded):
        from cloudshift.cloudshift_core import (
            py_parse_source,
            py_detect_services,
            py_match_and_transform,
        )

        input_file = next(INPUT_DIR.glob(f"{case}.*"))
        source = input_file.read_text()
        lang = _detect_language(input_file.name)
        ast = py_parse_source(source, lang, input_file.name)
        detections = py_detect_services(ast.nodes)

        for detection in detections:
            node_text = _find_node_text(ast.nodes, detection)
            result = py_match_and_transform(
                node_type=detection.construct_type,
                node_name=detection.node_name,
                node_text=node_text,
                provider=detection.provider,
                service=detection.service,
                language=lang,
                metadata=detection.metadata,
            )
            if result is not None:
                assert result.confidence >= 0.5, (
                    f"Low confidence {result.confidence} for {case} "
                    f"construct {detection.construct_type}"
                )


class TestGoldenDiff:
    """Verify unified diff generation between input and expected."""

    @pytest.mark.parametrize("case", GOLDEN_CASES)
    def test_diff_generated(self, case):
        from cloudshift.cloudshift_core import py_unified_diff

        input_file = next(INPUT_DIR.glob(f"{case}.*"))
        expected_file = EXPECTED_DIR / input_file.name
        if not expected_file.exists():
            pytest.skip(f"No expected file for {case}")

        old = input_file.read_text()
        new = expected_file.read_text()
        diff = py_unified_diff(old, new, input_file.name)
        # The diff should show changes (input != expected)
        assert "---" in diff or old == new, f"No diff header for {case}"


class TestGoldenValidation:
    """Verify that expected outputs pass residual reference scanning."""

    @pytest.mark.parametrize("case", GOLDEN_CASES)
    def test_expected_has_no_residual_refs(self, case):
        from cloudshift.cloudshift_core import py_scan_residual_refs

        expected_file = next(EXPECTED_DIR.glob(f"{case}.*"), None)
        if expected_file is None:
            pytest.skip(f"No expected file for {case}")

        source = expected_file.read_text()
        result = py_scan_residual_refs(source, expected_file.name)
        # Expected outputs should be clean of AWS/Azure references
        assert result.is_valid, (
            f"Expected output {case} has residual references: "
            f"{[i.message for i in result.issues]}"
        )
