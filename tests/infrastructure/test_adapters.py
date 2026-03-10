"""Comprehensive unit tests for the CloudShift infrastructure layer.

Targets 100% code coverage on every infrastructure adapter.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch, call

import pytest
import yaml

# ---------------------------------------------------------------------------
# Domain types used across tests
# ---------------------------------------------------------------------------
from cloudshift.domain.value_objects.types import (
    CloudProvider,
    ConfidenceScore,
    DiffHunk,
    Language,
    ProjectStatus,
    Severity,
    ValidationIssue,
)
from cloudshift.domain.entities.pattern import Pattern
from cloudshift.domain.entities.transformation import Transformation
from cloudshift.domain.entities.manifest import MigrationManifest, ManifestEntry
from cloudshift.domain.entities.validation_report import ValidationReport
from cloudshift.domain.entities.project import Project
from cloudshift.domain.ports.test_runner_port import TestResult


# ===================================================================
# Helper factories
# ===================================================================

def _make_pattern(**overrides) -> Pattern:
    defaults = dict(
        id="p1",
        name="s3-to-gcs",
        description="Migrate S3 to GCS",
        source_provider=CloudProvider.AWS,
        source_service="s3",
        target_provider=CloudProvider.GCP,
        target_service="gcs",
        language=Language.PYTHON,
        match_pattern="boto3.client('s3')",
        transform_spec={},
        confidence=ConfidenceScore(0.9),
        tags=["storage"],
    )
    defaults.update(overrides)
    return Pattern(**defaults)


def _make_transformation(**overrides) -> Transformation:
    defaults = dict(
        file_path="app.py",
        original_text="import boto3",
        transformed_text="from google.cloud import storage",
        pattern_id="p1",
    )
    defaults.update(overrides)
    return Transformation(**defaults)


def _make_project(**overrides) -> Project:
    defaults = dict(
        name="test-project",
        root_path=Path("/tmp/project"),
        source_provider=CloudProvider.AWS,
        target_provider=CloudProvider.GCP,
        status=ProjectStatus.CREATED,
        file_patterns=["*.py"],
        exclude_paths=["venv"],
    )
    defaults.update(overrides)
    return Project(**defaults)


# ===================================================================
# 1. RustParserAdapter
# ===================================================================

class TestRustParserAdapter:
    """Tests for parser_adapter.py covering lines 22, 31, 56-58, 63-65, 69-70, 74-75."""

    @pytest.fixture(autouse=True)
    def _patch_core(self):
        """Patch cloudshift.cloudshift_core used inside parser_adapter."""
        import cloudshift.infrastructure.rust_adapters.parser_adapter as mod
        mock_core = MagicMock()
        with patch.object(mod, "core", mock_core):
            self.mod = mod
            self.core = mock_core
            yield

    def _stub_py_ast(self, nodes=None):
        ast = MagicMock()
        ast.file_path = "test.py"
        ast.language = "python"
        ast.nodes = nodes or []
        return ast

    def _stub_py_node(self, *, children=None):
        node = MagicMock()
        node.node_type = "function"
        node.name = "foo"
        node.text = "def foo(): pass"
        node.start_line = 1
        node.end_line = 1
        node.start_col = 0
        node.end_col = 15
        node.children = children or []
        node.metadata = {"key": "val"}
        return node

    # -- _py_node_to_dict (line 31 + recursive children) --
    def test_py_node_to_dict_basic(self):
        child = self._stub_py_node()
        node = self._stub_py_node(children=[child])
        result = self.mod._py_node_to_dict(node)
        assert result["node_type"] == "function"
        assert result["name"] == "foo"
        assert result["text"] == "def foo(): pass"
        assert result["start_line"] == 1
        assert result["end_line"] == 1
        assert result["start_col"] == 0
        assert result["end_col"] == 15
        assert result["metadata"] == {"key": "val"}
        assert len(result["children"]) == 1
        assert result["children"][0]["name"] == "foo"

    # -- _py_ast_to_dict (line 22) --
    def test_py_ast_to_dict(self):
        node = self._stub_py_node()
        ast = self._stub_py_ast(nodes=[node])
        result = self.mod._py_ast_to_dict(ast)
        assert result["file_path"] == "test.py"
        assert result["language"] == "python"
        assert len(result["nodes"]) == 1

    # -- parse() (lines 56-58) --
    def test_parse(self):
        node = self._stub_py_node()
        ast = self._stub_py_ast(nodes=[node])
        self.core.py_parse_source.return_value = ast

        adapter = self.mod.RustParserAdapter()
        result = adapter.parse("source", Language.PYTHON)
        self.core.py_parse_source.assert_called_once_with("source", "python", "<inline>")
        assert result["file_path"] == "test.py"

    def test_parse_with_unmapped_language(self):
        """Tests the fallback branch in _LANG_MAP.get()."""
        ast = self._stub_py_ast()
        self.core.py_parse_source.return_value = ast

        adapter = self.mod.RustParserAdapter()
        # Language.CLOUDFORMATION IS mapped, so use a mock to simulate unmapped
        with patch.object(self.mod, "_LANG_MAP", {}):
            adapter.parse("source", Language.PYTHON)
        self.core.py_parse_source.assert_called_with("source", "python", "<inline>")

    # -- extract_constructs() (lines 63-65) --
    def test_extract_constructs(self):
        node = self._stub_py_node()
        ast = self._stub_py_ast(nodes=[node])
        self.core.py_parse_source.return_value = ast

        adapter = self.mod.RustParserAdapter()
        result = adapter.extract_constructs("source", Language.TYPESCRIPT)
        self.core.py_parse_source.assert_called_once_with("source", "typescript", "<inline>")
        assert len(result) == 1
        assert result[0]["node_type"] == "function"

    # -- parse_file() (lines 69-70) --
    def test_parse_file(self):
        ast = self._stub_py_ast()
        self.core.py_parse_file.return_value = ast

        adapter = self.mod.RustParserAdapter()
        result = adapter.parse_file("/path/to/file.py")
        self.core.py_parse_file.assert_called_once_with("/path/to/file.py")
        assert result["file_path"] == "test.py"

    # -- parse_source() (lines 74-75) --
    def test_parse_source(self):
        ast = self._stub_py_ast()
        self.core.py_parse_source.return_value = ast

        adapter = self.mod.RustParserAdapter()
        result = adapter.parse_source("src", "hcl", "main.tf")
        self.core.py_parse_source.assert_called_once_with("src", "hcl", "main.tf")
        assert result["language"] == "python"


# ===================================================================
# 2. RustDetectorAdapter
# ===================================================================

class TestRustDetectorAdapter:
    """Tests for detector_adapter.py covering lines 19, 45-49, 54-58, 64-77, 83-85."""

    @pytest.fixture(autouse=True)
    def _patch_core(self):
        import cloudshift.infrastructure.rust_adapters.detector_adapter as mod
        mock_core = MagicMock()
        with patch.object(mod, "core", mock_core):
            self.mod = mod
            self.core = mock_core
            yield

    def _stub_detection(self, *, provider="aws", service="s3", start=1, end=5):
        d = MagicMock()
        d.provider = provider
        d.service = service
        d.construct_type = "client"
        d.confidence = 0.9
        d.node_name = "s3_client"
        d.start_line = start
        d.end_line = end
        d.metadata = {"k": "v"}
        return d

    # -- _dict_to_py_node (line 19) --
    def test_dict_to_py_node(self):
        node_dict = {
            "node_type": "import",
            "name": "boto3",
            "text": "import boto3",
            "start_line": 1,
            "end_line": 1,
            "start_col": 0,
            "end_col": 12,
            "children": [],
            "metadata": {"x": "y"},
        }
        self.core.PyAstNode.return_value = MagicMock()
        result = self.mod._dict_to_py_node(node_dict)
        self.core.PyAstNode.assert_called_once()

    def test_dict_to_py_node_defaults(self):
        """start_col/end_col default to 0 when missing."""
        node_dict = {
            "node_type": "import",
            "name": "boto3",
            "text": "import boto3",
            "start_line": 1,
            "end_line": 1,
        }
        self.core.PyAstNode.return_value = MagicMock()
        self.mod._dict_to_py_node(node_dict)
        kwargs = self.core.PyAstNode.call_args
        assert kwargs[1]["start_col"] == 0
        assert kwargs[1]["end_col"] == 0
        assert kwargs[1]["children"] == []
        assert kwargs[1]["metadata"] == {}

    def test_dict_to_py_node_with_children(self):
        child = {
            "node_type": "arg",
            "name": "x",
            "text": "x",
            "start_line": 1,
            "end_line": 1,
        }
        parent = {
            "node_type": "func",
            "name": "f",
            "text": "def f(x): pass",
            "start_line": 1,
            "end_line": 1,
            "children": [child],
        }
        self.core.PyAstNode.return_value = MagicMock()
        self.mod._dict_to_py_node(parent)
        assert self.core.PyAstNode.call_count == 2

    # -- __init__ and _get_parser (lines 45-49) --
    def test_get_parser_lazy_import(self):
        adapter = self.mod.RustDetectorAdapter(parser=None)
        mock_parser_cls = MagicMock()
        mock_parser_instance = MagicMock()
        mock_parser_cls.return_value = mock_parser_instance
        # The lazy import does `from ...parser_adapter import RustParserAdapter`
        # so we patch it at the source module level
        with patch.dict("sys.modules", {
            "cloudshift.infrastructure.rust_adapters.parser_adapter": MagicMock(
                RustParserAdapter=mock_parser_cls,
            ),
        }):
            result = adapter._get_parser()
        assert result is mock_parser_instance
        # After first call, should be cached
        assert adapter._parser is mock_parser_instance

    def test_get_parser_injected(self):
        mock_parser = MagicMock()
        adapter = self.mod.RustDetectorAdapter(parser=mock_parser)
        assert adapter._get_parser() is mock_parser

    # -- detect() (lines 54-58) --
    def test_detect(self):
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {
                "node_type": "call",
                "name": "s3_client",
                "text": "boto3.client('s3')",
                "start_line": 1,
                "end_line": 1,
                "start_col": 0,
                "end_col": 18,
                "children": [],
                "metadata": {},
            }
        ]
        detection = self._stub_detection()
        self.core.py_detect_services.return_value = [detection]
        self.core.PyAstNode.return_value = MagicMock()

        adapter = self.mod.RustDetectorAdapter(parser=mock_parser)
        result = adapter.detect("import boto3", Language.PYTHON)
        assert len(result) == 1
        assert result[0] == ("s3", 1, 5)

    # -- detect_provider() (lines 64-77) --
    def test_detect_provider_found(self):
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {
                "node_type": "call",
                "name": "client",
                "text": "boto3.client('s3')",
                "start_line": 1,
                "end_line": 1,
                "children": [],
                "metadata": {},
            }
        ]
        detection = self._stub_detection(provider="aws")
        self.core.py_detect_services.return_value = [detection]
        self.core.PyAstNode.return_value = MagicMock()

        adapter = self.mod.RustDetectorAdapter(parser=mock_parser)
        result = adapter.detect_provider("import boto3")
        assert result == CloudProvider.AWS

    def test_detect_provider_not_found(self):
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = []
        self.core.py_detect_services.return_value = []
        self.core.PyAstNode.return_value = MagicMock()

        adapter = self.mod.RustDetectorAdapter(parser=mock_parser)
        result = adapter.detect_provider("print('hello')")
        assert result is None

    def test_detect_provider_exception_continues(self):
        """When an exception occurs for one language, it continues to the next."""
        mock_parser = MagicMock()
        mock_parser.extract_constructs.side_effect = [
            RuntimeError("parse fail"),  # PYTHON fails
            RuntimeError("parse fail"),  # TYPESCRIPT fails
            RuntimeError("parse fail"),  # HCL fails
        ]
        adapter = self.mod.RustDetectorAdapter(parser=mock_parser)
        result = adapter.detect_provider("bad source")
        assert result is None

    def test_detect_provider_hits_but_no_detections_on_recheck(self):
        """detect() returns hits but detect_services on re-check returns empty."""
        mock_parser = MagicMock()
        # First call from detect() returns constructs, second from detect_provider re-check
        mock_parser.extract_constructs.return_value = [
            {
                "node_type": "call",
                "name": "client",
                "text": "boto3.client('s3')",
                "start_line": 1,
                "end_line": 1,
                "children": [],
                "metadata": {},
            }
        ]
        detection = self._stub_detection()
        # First detect_services call returns hits, second returns empty
        self.core.py_detect_services.side_effect = [[detection], []]
        self.core.PyAstNode.return_value = MagicMock()

        adapter = self.mod.RustDetectorAdapter(parser=mock_parser)
        result = adapter.detect_provider("import boto3")
        assert result is None

    def test_detect_provider_unknown_provider_keyword(self):
        """Provider string not in _PROVIDER_KEYWORDS returns None from .get()."""
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {
                "node_type": "call",
                "name": "client",
                "text": "some code",
                "start_line": 1,
                "end_line": 1,
                "children": [],
                "metadata": {},
            }
        ]
        detection = self._stub_detection(provider="unknown_cloud")
        self.core.py_detect_services.return_value = [detection]
        self.core.PyAstNode.return_value = MagicMock()

        adapter = self.mod.RustDetectorAdapter(parser=mock_parser)
        result = adapter.detect_provider("some code")
        # _PROVIDER_KEYWORDS.get("unknown_cloud") returns None
        assert result is None

    # -- detect_services_raw() (lines 83-85) --
    def test_detect_services_raw(self):
        detection = self._stub_detection()
        self.core.py_detect_services.return_value = [detection]
        self.core.PyAstNode.return_value = MagicMock()

        adapter = self.mod.RustDetectorAdapter()
        node = {
            "node_type": "call",
            "name": "s3",
            "text": "s3.put_object()",
            "start_line": 1,
            "end_line": 1,
            "children": [],
            "metadata": {},
        }
        result = adapter.detect_services_raw([node])
        assert len(result) == 1
        assert result[0]["service"] == "s3"
        assert result[0]["provider"] == "aws"
        assert result[0]["metadata"] == {"k": "v"}


# ===================================================================
# 3. RustPatternEngineAdapter
# ===================================================================

class TestRustPatternEngineAdapter:
    """Tests for pattern_engine_adapter.py."""

    @pytest.fixture(autouse=True)
    def _patch_core(self):
        import cloudshift.infrastructure.rust_adapters.pattern_engine_adapter as mod
        mock_core = MagicMock()
        with patch.object(mod, "core", mock_core):
            self.mod = mod
            self.core = mock_core
            yield

    # -- __init__ / _get_parser (lines 28-29, 32-36) --
    def test_init_and_get_parser_lazy(self):
        adapter = self.mod.RustPatternEngineAdapter()
        assert adapter._parser is None
        assert adapter._loaded is False
        mock_parser = MagicMock()
        with patch(
            "cloudshift.infrastructure.rust_adapters.parser_adapter.RustParserAdapter",
            return_value=mock_parser,
        ):
            parser = adapter._get_parser()
        assert adapter._parser is not None

    def test_get_parser_injected(self):
        mock_parser = MagicMock()
        adapter = self.mod.RustPatternEngineAdapter(parser=mock_parser)
        assert adapter._get_parser() is mock_parser

    # -- load_patterns (lines 40-42) --
    def test_load_patterns(self):
        self.core.py_load_patterns.return_value = 5
        adapter = self.mod.RustPatternEngineAdapter()
        count = adapter.load_patterns("/some/dir")
        assert count == 5
        assert adapter._loaded is True
        self.core.py_load_patterns.assert_called_once_with("/some/dir")

    # -- match() (lines 50-72) --
    def test_match_with_results(self):
        pattern = _make_pattern()
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {
                "node_type": "call",
                "name": "s3_client",
                "text": "boto3.client('s3')",
                "start_line": 3,
                "end_line": 5,
                "metadata": {"k": "v"},
            }
        ]
        mock_result = MagicMock()
        self.core.py_match_and_transform.return_value = mock_result

        adapter = self.mod.RustPatternEngineAdapter(parser=mock_parser)
        matches = adapter.match("source", [pattern], Language.PYTHON)

        assert len(matches) == 1
        assert matches[0] == (pattern, 3, 5)
        self.core.py_match_and_transform.assert_called_once_with(
            "call", "s3_client", "boto3.client('s3')",
            "aws", "s3", "python", {"k": "v"},
        )

    def test_match_no_results(self):
        pattern = _make_pattern()
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {
                "node_type": "call",
                "name": "x",
                "text": "x()",
                "start_line": 1,
                "end_line": 1,
                "metadata": {},
            }
        ]
        self.core.py_match_and_transform.return_value = None

        adapter = self.mod.RustPatternEngineAdapter(parser=mock_parser)
        matches = adapter.match("source", [pattern], Language.PYTHON)
        assert matches == []

    def test_match_metadata_default(self):
        """When node_dict has no 'metadata' key, empty dict is used."""
        pattern = _make_pattern()
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {"node_type": "call", "name": "x", "text": "x()", "start_line": 1, "end_line": 1}
        ]
        self.core.py_match_and_transform.return_value = None

        adapter = self.mod.RustPatternEngineAdapter(parser=mock_parser)
        adapter.match("source", [pattern], Language.HCL)
        self.core.py_match_and_transform.assert_called_once_with(
            "call", "x", "x()", "aws", "s3", "hcl", {},
        )

    # -- apply() (lines 80-99) --
    def test_apply_with_transform(self):
        pattern = _make_pattern()
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {
                "node_type": "call",
                "name": "s3",
                "text": "boto3.client('s3')",
                "start_line": 1,
                "end_line": 1,
                "metadata": {},
            }
        ]
        mock_result = MagicMock()
        mock_result.original_text = "boto3.client('s3')"
        mock_result.transformed_text = "storage.Client()"
        self.core.py_match_and_transform.return_value = mock_result

        adapter = self.mod.RustPatternEngineAdapter(parser=mock_parser)
        result = adapter.apply("x = boto3.client('s3')", pattern, Language.PYTHON)
        assert result == "x = storage.Client()"

    def test_apply_no_match(self):
        pattern = _make_pattern()
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {"node_type": "call", "name": "x", "text": "x()", "start_line": 1, "end_line": 1, "metadata": {}}
        ]
        self.core.py_match_and_transform.return_value = None

        adapter = self.mod.RustPatternEngineAdapter(parser=mock_parser)
        result = adapter.apply("x()", pattern, Language.PYTHON)
        assert result == "x()"

    # -- match_and_transform() raw (lines 112-119) --
    def test_match_and_transform_raw_found(self):
        mock_result = MagicMock()
        mock_result.pattern_id = "p1"
        mock_result.original_text = "old"
        mock_result.transformed_text = "new"
        mock_result.import_additions = ["import new"]
        mock_result.import_removals = ["import old"]
        mock_result.confidence = 0.95
        mock_result.metadata = {"a": "b"}
        self.core.py_match_and_transform.return_value = mock_result

        adapter = self.mod.RustPatternEngineAdapter()
        result = adapter.match_and_transform(
            "call", "fn", "fn()", "aws", "s3", "python", {"m": "v"},
        )
        assert result is not None
        assert result["pattern_id"] == "p1"
        assert result["original_text"] == "old"
        assert result["transformed_text"] == "new"
        assert result["import_additions"] == ["import new"]
        assert result["import_removals"] == ["import old"]
        assert result["confidence"] == 0.95
        assert result["metadata"] == {"a": "b"}

    def test_match_and_transform_raw_not_found(self):
        self.core.py_match_and_transform.return_value = None

        adapter = self.mod.RustPatternEngineAdapter()
        result = adapter.match_and_transform(
            "call", "fn", "fn()", "aws", "s3", "python",
        )
        assert result is None
        # Verify None metadata gets converted to {}
        self.core.py_match_and_transform.assert_called_once_with(
            "call", "fn", "fn()", "aws", "s3", "python", {},
        )


# ===================================================================
# 4. RustDiffAdapter
# ===================================================================

class TestRustDiffAdapter:
    """Tests for diff_adapter.py."""

    @pytest.fixture(autouse=True)
    def _patch_core(self):
        import cloudshift.infrastructure.rust_adapters.diff_adapter as mod
        mock_core = MagicMock()
        with patch.object(mod, "core", mock_core):
            self.mod = mod
            self.core = mock_core
            yield

    # -- compute_diff empty (lines 20-23) --
    def test_compute_diff_empty(self):
        self.core.py_unified_diff.return_value = ""
        adapter = self.mod.RustDiffAdapter()
        result = adapter.compute_diff("same", "same")
        assert result == []

    def test_compute_diff_whitespace_only(self):
        self.core.py_unified_diff.return_value = "  \n  \n"
        adapter = self.mod.RustDiffAdapter()
        result = adapter.compute_diff("same", "same")
        assert result == []

    # -- compute_diff with hunks (lines 20-23 + _parse_unified_diff lines 53-86) --
    def test_compute_diff_single_hunk(self):
        raw_diff = (
            "--- a/<diff>\n"
            "+++ b/<diff>\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-line2\n"
            "+line2_modified\n"
            " line3\n"
        )
        self.core.py_unified_diff.return_value = raw_diff
        adapter = self.mod.RustDiffAdapter()
        original = "line1\nline2\nline3\n"
        modified = "line1\nline2_modified\nline3\n"
        result = adapter.compute_diff(original, modified)
        assert len(result) == 1
        hunk = result[0]
        assert hunk.start_line == 1
        assert hunk.end_line == 3
        assert hunk.file_path == "<diff>"

    def test_compute_diff_multiple_hunks(self):
        raw_diff = (
            "--- a/<diff>\n"
            "+++ b/<diff>\n"
            "@@ -1,2 +1,2 @@\n"
            "-old1\n"
            "+new1\n"
            " same\n"
            "@@ -5,1 +5,1 @@\n"
            "-old5\n"
            "+new5\n"
        )
        self.core.py_unified_diff.return_value = raw_diff
        adapter = self.mod.RustDiffAdapter()
        original = "old1\nsame\nline3\nline4\nold5\n"
        modified = "new1\nsame\nline3\nline4\nnew5\n"
        result = adapter.compute_diff(original, modified)
        assert len(result) == 2

    def test_compute_diff_single_line_range(self):
        """Hunk range without comma (e.g., @@ -1 +1 @@) means count=1."""
        raw_diff = (
            "--- a/<diff>\n"
            "+++ b/<diff>\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        self.core.py_unified_diff.return_value = raw_diff
        adapter = self.mod.RustDiffAdapter()
        original = "old\n"
        modified = "new\n"
        result = adapter.compute_diff(original, modified)
        assert len(result) == 1
        assert result[0].start_line == 1
        assert result[0].end_line == 1

    # -- apply_diff (lines 26-33) --
    def test_apply_diff(self):
        adapter = self.mod.RustDiffAdapter()
        original = "line1\nline2\nline3\n"
        hunks = [
            DiffHunk(
                file_path="<diff>",
                start_line=2,
                end_line=2,
                original_text="line2\n",
                modified_text="modified_line2\n",
            )
        ]
        result = adapter.apply_diff(original, hunks)
        assert "modified_line2" in result
        assert "line1" in result
        assert "line3" in result

    def test_apply_diff_multiple_hunks_reverse_order(self):
        adapter = self.mod.RustDiffAdapter()
        original = "a\nb\nc\nd\n"
        hunks = [
            DiffHunk(file_path="f", start_line=1, end_line=1,
                     original_text="a\n", modified_text="A\n"),
            DiffHunk(file_path="f", start_line=3, end_line=3,
                     original_text="c\n", modified_text="C\n"),
        ]
        result = adapter.apply_diff(original, hunks)
        assert result == "A\nb\nC\nd\n"

    # -- unified_diff raw (line 37) --
    def test_unified_diff_raw(self):
        self.core.py_unified_diff.return_value = "diff output"
        adapter = self.mod.RustDiffAdapter()
        result = adapter.unified_diff("old", "new", "file.py")
        self.core.py_unified_diff.assert_called_with("old", "new", "file.py")
        assert result == "diff output"

    # -- ast_diff (lines 46-48) --
    def test_ast_diff(self):
        self.core.py_ast_diff.return_value = [{"change": "added"}]
        # Need to mock PyAstNode from the detector_adapter's core
        import cloudshift.infrastructure.rust_adapters.detector_adapter as det
        det.core.PyAstNode.return_value = MagicMock()

        adapter = self.mod.RustDiffAdapter()
        old_nodes = [{"node_type": "fn", "name": "a", "text": "a", "start_line": 1, "end_line": 1}]
        new_nodes = [{"node_type": "fn", "name": "b", "text": "b", "start_line": 1, "end_line": 1}]
        result = adapter.ast_diff(old_nodes, new_nodes, "test.py")
        assert result == [{"change": "added"}]

    # -- _build_hunk (lines 97-103) --
    def test_build_hunk(self):
        hunk = self.mod._build_hunk(
            old_start=2, old_count=3,
            orig_lines=["a\n", "b\n", "c\n", "d\n", "e\n"],
            mod_lines=["a\n", "X\n", "Y\n", "Z\n", "e\n"],
            new_start=2, new_count=3,
        )
        assert hunk.file_path == "<diff>"
        assert hunk.start_line == 2
        assert hunk.end_line == 4
        assert hunk.original_text == "b\nc\nd\n"
        assert hunk.modified_text == "X\nY\nZ\n"


# ===================================================================
# 5. RustWalkerAdapter
# ===================================================================

class TestRustWalkerAdapter:
    """Tests for walker_adapter.py."""

    @pytest.fixture(autouse=True)
    def _patch_core(self):
        import cloudshift.infrastructure.rust_adapters.walker_adapter as mod
        mock_core = MagicMock()
        with patch.object(mod, "core", mock_core):
            self.mod = mod
            self.core = mock_core
            yield

    # -- read (line 23) --
    def test_read(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world", encoding="utf-8")
        adapter = self.mod.RustWalkerAdapter()
        assert adapter.read(f) == "hello world"

    # -- write (lines 26-27) --
    def test_write(self, tmp_path):
        f = tmp_path / "subdir" / "out.txt"
        adapter = self.mod.RustWalkerAdapter()
        adapter.write(f, "content")
        assert f.read_text(encoding="utf-8") == "content"
        assert f.parent.exists()

    # -- list_files without patterns (lines 33-40) --
    def test_list_files_no_patterns(self, tmp_path):
        self.core.py_walk_directory.return_value = [
            str(tmp_path / "a.py"),
            str(tmp_path / "b.ts"),
        ]
        adapter = self.mod.RustWalkerAdapter()
        result = adapter.list_files(tmp_path)
        assert len(result) == 2
        assert all(isinstance(p, Path) for p in result)

    # -- list_files with patterns (lines 33-40) --
    def test_list_files_with_patterns(self, tmp_path):
        self.core.py_walk_directory.return_value = [
            str(tmp_path / "a.py"),
            str(tmp_path / "b.ts"),
            str(tmp_path / "c.py"),
        ]
        adapter = self.mod.RustWalkerAdapter()
        result = adapter.list_files(tmp_path, patterns=["*.py"])
        assert len(result) == 2
        assert all(str(p).endswith(".py") for p in result)

    # -- exists (line 43) --
    def test_exists_true(self, tmp_path):
        f = tmp_path / "exists.txt"
        f.write_text("x")
        adapter = self.mod.RustWalkerAdapter()
        assert adapter.exists(f) is True

    def test_exists_false(self, tmp_path):
        adapter = self.mod.RustWalkerAdapter()
        assert adapter.exists(tmp_path / "nope.txt") is False

    # -- walk_directory (line 49) --
    def test_walk_directory(self):
        self.core.py_walk_directory.return_value = ["/a.py", "/b.py"]
        adapter = self.mod.RustWalkerAdapter()
        result = adapter.walk_directory("/root")
        assert result == ["/a.py", "/b.py"]
        self.core.py_walk_directory.assert_called_once_with("/root")

    # -- build_dependency_graph (lines 55-56) --
    def test_build_dependency_graph(self):
        self.core.py_build_dependency_graph.return_value = (
            ["a.py", "b.py"],
            [(0, 1)],
            [0, 1],
        )
        adapter = self.mod.RustWalkerAdapter()
        nodes, edges, order = adapter.build_dependency_graph(["a.py", "b.py"])
        assert nodes == ["a.py", "b.py"]
        assert edges == [(0, 1)]
        assert order == [0, 1]

    # -- copy_file (lines 60-61) --
    def test_copy_file(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        dst = tmp_path / "sub" / "dst.txt"
        adapter = self.mod.RustWalkerAdapter()
        adapter.copy_file(str(src), str(dst))
        assert dst.read_text() == "data"


# ===================================================================
# 6. RustValidationAdapter
# ===================================================================

class TestRustValidationAdapter:
    """Tests for validation_adapter.py."""

    @pytest.fixture(autouse=True)
    def _patch_core(self):
        import cloudshift.infrastructure.rust_adapters.validation_adapter as mod
        mock_core = MagicMock()
        with patch.object(mod, "core", mock_core):
            self.mod = mod
            self.core = mock_core
            yield

    # -- __init__ / _get_parser (lines 24, 27-31) --
    def test_init_with_parser(self):
        parser = MagicMock()
        adapter = self.mod.RustValidationAdapter(parser=parser)
        assert adapter._get_parser() is parser

    def test_init_without_parser_lazy(self):
        adapter = self.mod.RustValidationAdapter()
        assert adapter._parser is None
        with patch(
            "cloudshift.infrastructure.rust_adapters.parser_adapter.RustParserAdapter",
            return_value=MagicMock(),
        ):
            parser = adapter._get_parser()
        assert adapter._parser is not None

    # -- validate_syntax success (lines 34-44) --
    def test_validate_syntax_ok(self):
        mock_parser = MagicMock()
        adapter = self.mod.RustValidationAdapter(parser=mock_parser)
        report = adapter.validate_syntax("valid code", Language.PYTHON)
        assert report.is_valid
        assert len(report.issues) == 0

    # -- validate_syntax failure (lines 34-44) --
    def test_validate_syntax_error(self):
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = SyntaxError("bad syntax")
        adapter = self.mod.RustValidationAdapter(parser=mock_parser)
        report = adapter.validate_syntax("invalid{{{", Language.PYTHON)
        assert not report.is_valid
        assert len(report.issues) == 1
        assert report.issues[0].severity == Severity.ERROR
        assert "Syntax error" in report.issues[0].message

    # -- validate_transformation success path (lines 47-92) --
    def test_validate_transformation_success(self):
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {"node_type": "fn", "name": "a", "text": "a", "start_line": 1, "end_line": 1}
        ]

        # Set up detector_adapter's core mock too
        import cloudshift.infrastructure.rust_adapters.detector_adapter as det
        det.core.PyAstNode.return_value = MagicMock()

        equiv_result = MagicMock()
        equiv_result.issues = []
        self.core.py_check_ast_equivalence.return_value = equiv_result

        residual_result = MagicMock()
        residual_result.issues = []
        self.core.py_scan_residual_refs.return_value = residual_result

        adapter = self.mod.RustValidationAdapter(parser=mock_parser)
        transformation = _make_transformation()
        report = adapter.validate_transformation(transformation)
        assert report.is_valid

    def test_validate_transformation_with_issues(self):
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {"node_type": "fn", "name": "a", "text": "a", "start_line": 1, "end_line": 1}
        ]

        import cloudshift.infrastructure.rust_adapters.detector_adapter as det
        det.core.PyAstNode.return_value = MagicMock()

        equiv_result = MagicMock()
        equiv_result.issues = [
            {"message": "AST mismatch", "severity": "warning", "file_path": "x.py", "line": "10", "category": "ast"},
        ]
        self.core.py_check_ast_equivalence.return_value = equiv_result

        residual_result = MagicMock()
        residual_result.issues = [
            {"message": "Residual ref", "severity": "error", "file_path": "x.py", "line": "5", "category": "residual"},
        ]
        self.core.py_scan_residual_refs.return_value = residual_result

        adapter = self.mod.RustValidationAdapter(parser=mock_parser)
        transformation = _make_transformation()
        report = adapter.validate_transformation(transformation)
        assert len(report.issues) == 2

    def test_validate_transformation_ast_exception(self):
        """When AST equivalence check throws, a warning is added."""
        mock_parser = MagicMock()
        mock_parser.extract_constructs.side_effect = RuntimeError("parse fail")

        residual_result = MagicMock()
        residual_result.issues = []
        self.core.py_scan_residual_refs.return_value = residual_result

        adapter = self.mod.RustValidationAdapter(parser=mock_parser)
        transformation = _make_transformation()
        report = adapter.validate_transformation(transformation)
        assert any("AST equivalence check failed" in i.message for i in report.issues)

    def test_validate_transformation_issue_without_line(self):
        """Issue dict without 'line' key should set line=None."""
        mock_parser = MagicMock()
        mock_parser.extract_constructs.return_value = [
            {"node_type": "fn", "name": "a", "text": "a", "start_line": 1, "end_line": 1}
        ]

        import cloudshift.infrastructure.rust_adapters.detector_adapter as det
        det.core.PyAstNode.return_value = MagicMock()

        equiv_result = MagicMock()
        equiv_result.issues = [
            {"message": "issue no line", "severity": "info"},
        ]
        self.core.py_check_ast_equivalence.return_value = equiv_result

        residual_result = MagicMock()
        residual_result.issues = [
            {"message": "residual no line"},
        ]
        self.core.py_scan_residual_refs.return_value = residual_result

        adapter = self.mod.RustValidationAdapter(parser=mock_parser)
        transformation = _make_transformation()
        report = adapter.validate_transformation(transformation)
        assert any(i.line is None for i in report.issues)

    # -- validate_manifest (lines 95-102) --
    def test_validate_manifest_empty(self):
        adapter = self.mod.RustValidationAdapter()
        manifest = MigrationManifest(entries=[])
        report = adapter.validate_manifest(manifest)
        assert len(report.issues) == 1
        assert "no entries" in report.issues[0].message

    def test_validate_manifest_with_entries(self):
        adapter = self.mod.RustValidationAdapter()
        entry = ManifestEntry(
            file_path="a.py",
            pattern_id="p1",
            source_construct="s3",
            target_construct="gcs",
        )
        manifest = MigrationManifest(entries=[entry])
        report = adapter.validate_manifest(manifest)
        assert report.is_valid
        assert len(report.issues) == 0

    # -- check_ast_equivalence_raw (lines 109-112) --
    def test_check_ast_equivalence_raw(self):
        import cloudshift.infrastructure.rust_adapters.detector_adapter as det
        det.core.PyAstNode.return_value = MagicMock()

        result_mock = MagicMock()
        result_mock.is_valid = True
        result_mock.issues = []
        result_mock.summary = "ok"
        self.core.py_check_ast_equivalence.return_value = result_mock

        adapter = self.mod.RustValidationAdapter()
        result = adapter.check_ast_equivalence_raw(
            [{"node_type": "fn", "name": "a", "text": "a", "start_line": 1, "end_line": 1}],
            [{"node_type": "fn", "name": "a", "text": "a", "start_line": 1, "end_line": 1}],
            "test.py",
        )
        assert result["is_valid"] is True
        assert result["summary"] == "ok"

    # -- scan_residual_refs_raw (lines 119-120) --
    def test_scan_residual_refs_raw(self):
        result_mock = MagicMock()
        result_mock.is_valid = True
        result_mock.issues = [{"message": "found ref"}]
        result_mock.summary = "1 ref"
        self.core.py_scan_residual_refs.return_value = result_mock

        adapter = self.mod.RustValidationAdapter()
        result = adapter.scan_residual_refs_raw("source code", "file.py")
        assert result["is_valid"] is True
        assert len(result["issues"]) == 1

    # -- _severity_from_str (line 128) --
    def test_severity_from_str(self):
        assert self.mod._severity_from_str("error") == Severity.ERROR
        assert self.mod._severity_from_str("warning") == Severity.WARNING
        assert self.mod._severity_from_str("info") == Severity.INFO
        assert self.mod._severity_from_str("critical") == Severity.CRITICAL
        assert self.mod._severity_from_str("ERROR") == Severity.ERROR
        assert self.mod._severity_from_str("unknown") == Severity.WARNING


# ===================================================================
# 7. OllamaAdapter
# ===================================================================

class TestOllamaAdapter:
    """Tests for ollama_adapter.py covering lines 28-30, 33-45, 50-60, 65-76, 79, 84-95."""

    @pytest.fixture(autouse=True)
    def _patch_httpx(self):
        with patch("cloudshift.infrastructure.llm.ollama_adapter.httpx") as mock_httpx:
            self.mock_httpx = mock_httpx
            # Use MagicMock for client so post() returns a coroutine via AsyncMock
            # but responses use MagicMock (json/raise_for_status are sync in httpx)
            self.mock_client = MagicMock()
            self.mock_client.post = AsyncMock()
            self.mock_client.aclose = AsyncMock()
            mock_httpx.AsyncClient.return_value = self.mock_client
            yield

    def _get_adapter(self):
        from cloudshift.infrastructure.llm.ollama_adapter import OllamaAdapter
        return OllamaAdapter(base_url="http://test:11434", model="test-model", timeout=30.0)

    # -- __init__ (lines 28-30) --
    def test_init(self):
        adapter = self._get_adapter()
        assert adapter._base_url == "http://test:11434"
        assert adapter._model == "test-model"
        self.mock_httpx.AsyncClient.assert_called_once_with(
            base_url="http://test:11434", timeout=30.0,
        )

    def test_init_strips_trailing_slash(self):
        from cloudshift.infrastructure.llm.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter(base_url="http://host:1234/", model="m")
        assert adapter._base_url == "http://host:1234"

    def _make_response(self, json_data):
        """Create a MagicMock response with sync json() and raise_for_status()."""
        resp = MagicMock()
        resp.json.return_value = json_data
        resp.raise_for_status.return_value = None
        return resp

    # -- complete() (lines 33-45) --
    @pytest.mark.asyncio
    async def test_complete_basic(self):
        resp = self._make_response({"response": "generated text"})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        result = await adapter.complete("hello")
        assert result == "generated text"
        call_args = self.mock_client.post.call_args
        assert call_args[0][0] == "/api/generate"
        payload = call_args[1]["json"]
        assert payload["model"] == "test-model"
        assert payload["prompt"] == "hello"
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_complete_with_system(self):
        resp = self._make_response({"response": "ok"})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        result = await adapter.complete("prompt", system="sys prompt", temperature=0.5)
        payload = self.mock_client.post.call_args[1]["json"]
        assert payload["system"] == "sys prompt"
        assert payload["options"]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_complete_empty_response(self):
        resp = self._make_response({})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        result = await adapter.complete("prompt")
        assert result == ""

    # -- transform_code() (lines 50-60) --
    @pytest.mark.asyncio
    async def test_transform_code_with_code_block(self):
        resp = self._make_response({
            "response": "Here is the code:\n```python\nresult = 42\n```\nDone."
        })
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        result = await adapter.transform_code(
            "x = 1", "change x to 42", Language.PYTHON,
        )
        assert result == "result = 42"

    @pytest.mark.asyncio
    async def test_transform_code_no_code_block(self):
        resp = self._make_response({"response": "just plain text"})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        result = await adapter.transform_code(
            "x = 1", "change x", Language.PYTHON,
        )
        assert result == "just plain text"

    # -- assess_confidence() (lines 65-76) --
    @pytest.mark.asyncio
    async def test_assess_confidence_valid(self):
        resp = self._make_response({"response": "0.85"})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        score = await adapter.assess_confidence("old code", "new code")
        assert score == ConfidenceScore(0.85)

    @pytest.mark.asyncio
    async def test_assess_confidence_with_extra_text(self):
        resp = self._make_response({"response": "0.92 is the score"})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        score = await adapter.assess_confidence("old", "new")
        assert score == ConfidenceScore(0.92)

    @pytest.mark.asyncio
    async def test_assess_confidence_invalid_returns_default(self):
        resp = self._make_response({"response": "I cannot rate this"})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        score = await adapter.assess_confidence("old", "new")
        assert score == ConfidenceScore(0.5)

    @pytest.mark.asyncio
    async def test_assess_confidence_empty_response(self):
        resp = self._make_response({"response": ""})
        self.mock_client.post.return_value = resp

        adapter = self._get_adapter()
        score = await adapter.assess_confidence("old", "new")
        assert score == ConfidenceScore(0.5)

    # -- close() (line 79) --
    @pytest.mark.asyncio
    async def test_close(self):
        adapter = self._get_adapter()
        await adapter.close()
        self.mock_client.aclose.assert_awaited_once()

    # -- _extract_code_block() (lines 84-95) --
    def test_extract_code_block_with_code(self):
        from cloudshift.infrastructure.llm.ollama_adapter import _extract_code_block
        text = "Here:\n```python\ncode line 1\ncode line 2\n```\nEnd"
        result = _extract_code_block(text)
        assert result == "code line 1\ncode line 2"

    def test_extract_code_block_no_code(self):
        from cloudshift.infrastructure.llm.ollama_adapter import _extract_code_block
        result = _extract_code_block("no code block here")
        assert result is None

    def test_extract_code_block_empty_block(self):
        from cloudshift.infrastructure.llm.ollama_adapter import _extract_code_block
        result = _extract_code_block("```\n```")
        assert result is None

    def test_extract_code_block_unclosed(self):
        from cloudshift.infrastructure.llm.ollama_adapter import _extract_code_block
        text = "```python\nline1\nline2"
        result = _extract_code_block(text)
        assert result == "line1\nline2"


# ===================================================================
# 7b. GeminiAdapter
# ===================================================================

class TestGeminiAdapter:
    """Tests for gemini_adapter.py (demo mode LLM)."""

    @pytest.fixture(autouse=True)
    def _patch_httpx(self):
        with patch("cloudshift.infrastructure.llm.gemini_adapter.httpx") as mock_httpx:
            self.mock_httpx = mock_httpx
            self.mock_client = MagicMock()
            self.mock_client.post = AsyncMock()
            self.mock_client.aclose = AsyncMock()
            mock_httpx.AsyncClient.return_value = self.mock_client
            yield

    def _get_adapter(self):
        from cloudshift.infrastructure.llm.gemini_adapter import GeminiAdapter
        return GeminiAdapter(api_key="test-key", model="gemini-1.5-flash", timeout=30.0)

    def _gemini_response(self, text: str):
        return {"candidates": [{"content": {"parts": [{"text": text}]}}]}

    def test_init(self):
        adapter = self._get_adapter()
        assert adapter._api_key == "test-key"
        assert adapter._model == "gemini-1.5-flash"

    def test_url_includes_api_key_and_model(self):
        adapter = self._get_adapter()
        url = adapter._url()
        assert "test-key" in url
        assert "gemini-1.5-flash" in url
        assert "generateContent" in url

    @pytest.mark.asyncio
    async def test_complete_basic(self):
        self.mock_client.post.return_value = MagicMock(
            json=lambda: self._gemini_response("hello from gemini"),
            raise_for_status=MagicMock(),
        )
        adapter = self._get_adapter()
        result = await adapter.complete("hello")
        assert result == "hello from gemini"

    @pytest.mark.asyncio
    async def test_complete_with_system_instruction(self):
        self.mock_client.post.return_value = MagicMock(
            json=lambda: self._gemini_response("ok"),
            raise_for_status=MagicMock(),
        )
        adapter = self._get_adapter()
        await adapter.complete("p", system="you are helpful")
        payload = self.mock_client.post.call_args[1]["json"]
        assert "systemInstruction" in payload
        assert payload["systemInstruction"]["parts"][0]["text"] == "you are helpful"

    @pytest.mark.asyncio
    async def test_complete_empty_candidates_returns_empty_string(self):
        self.mock_client.post.return_value = MagicMock(
            json=lambda: {},
            raise_for_status=MagicMock(),
        )
        adapter = self._get_adapter()
        result = await adapter.complete("p")
        assert result == ""

    @pytest.mark.asyncio
    async def test_transform_code_extracts_code_block(self):
        self.mock_client.post.return_value = MagicMock(
            json=lambda: self._gemini_response("```python\nresult = 99\n```"),
            raise_for_status=MagicMock(),
        )
        adapter = self._get_adapter()
        result = await adapter.transform_code("x=1", "change to 99", Language.PYTHON)
        assert result == "result = 99"

    @pytest.mark.asyncio
    async def test_assess_confidence_parses_float(self):
        self.mock_client.post.return_value = MagicMock(
            json=lambda: self._gemini_response("0.78"),
            raise_for_status=MagicMock(),
        )
        adapter = self._get_adapter()
        score = await adapter.assess_confidence("old", "new")
        assert float(score) == 0.78

    @pytest.mark.asyncio
    async def test_assess_confidence_invalid_returns_default(self):
        self.mock_client.post.return_value = MagicMock(
            json=lambda: self._gemini_response("nope"),
            raise_for_status=MagicMock(),
        )
        adapter = self._get_adapter()
        score = await adapter.assess_confidence("old", "new")
        assert float(score) == 0.5

    @pytest.mark.asyncio
    async def test_close(self):
        adapter = self._get_adapter()
        await adapter.close()
        self.mock_client.aclose.assert_awaited_once()


# ===================================================================
# 8. NullLLMAdapter
# ===================================================================

class TestNullLLMAdapter:
    """Tests for null_adapter.py covering lines 16, 21, 26."""

    @pytest.mark.asyncio
    async def test_complete(self):
        from cloudshift.infrastructure.llm.null_adapter import NullLLMAdapter
        adapter = NullLLMAdapter()
        result = await adapter.complete("any prompt", temperature=0.5)
        assert result == ""

    @pytest.mark.asyncio
    async def test_transform_code(self):
        from cloudshift.infrastructure.llm.null_adapter import NullLLMAdapter
        adapter = NullLLMAdapter()
        result = await adapter.transform_code("source", "instruction", Language.PYTHON)
        assert result == "source"

    @pytest.mark.asyncio
    async def test_assess_confidence(self):
        from cloudshift.infrastructure.llm.null_adapter import NullLLMAdapter
        adapter = NullLLMAdapter()
        score = await adapter.assess_confidence("old", "new")
        assert score == ConfidenceScore(0.0)


# ===================================================================
# 9. LocalPatternStore
# ===================================================================

class TestLocalPatternStore:
    """Tests for local_store.py."""

    def _write_pattern_yaml(self, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            yaml.dump(data, f)

    def _sample_pattern_dict(self, **overrides):
        defaults = {
            "id": "p1",
            "name": "s3-to-gcs",
            "description": "Migrate S3 to GCS",
            "source_provider": "aws",
            "source_service": "s3",
            "target_provider": "gcp",
            "target_service": "gcs",
            "language": "python",
            "match_pattern": "boto3.client('s3')",
            "transform_spec": {},
            "confidence": 0.9,
            "tags": ["storage"],
        }
        defaults.update(overrides)
        return defaults

    # -- __init__ with directory (line 47 via load_all) --
    def test_init_with_directory(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "p.yaml", self._sample_pattern_dict())
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore(directory=tmp_path)
        assert store.get("p1") is not None

    def test_init_without_directory(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        assert len(store.list_all()) == 0

    # -- load_all with nonexistent directory (line 47) --
    def test_load_all_nonexistent_dir(self, tmp_path):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        result = store.load_all(str(tmp_path / "nonexistent"))
        assert result == []

    # -- load_all with valid YAML (line 60) --
    def test_load_all_valid(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "a.yaml", self._sample_pattern_dict(id="p1"))
        self._write_pattern_yaml(tmp_path / "b.yml", self._sample_pattern_dict(id="p2"))
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        loaded = store.load_all(str(tmp_path))
        assert len(loaded) == 2

    # -- load_all with invalid YAML (exception -> continue) --
    def test_load_all_invalid_yaml(self, tmp_path):
        (tmp_path / "bad.yaml").write_text("{{{{invalid yaml", encoding="utf-8")
        self._write_pattern_yaml(tmp_path / "good.yaml", self._sample_pattern_dict())
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        loaded = store.load_all(str(tmp_path))
        assert len(loaded) == 1

    # -- load_all with YAML list --
    def test_load_all_yaml_list(self, tmp_path):
        data = [
            self._sample_pattern_dict(id="p1"),
            self._sample_pattern_dict(id="p2"),
        ]
        self._write_pattern_yaml(tmp_path / "multi.yaml", data)
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        loaded = store.load_all(str(tmp_path))
        assert len(loaded) == 2

    # -- load_all with empty YAML file (line 104) --
    def test_load_all_empty_yaml(self, tmp_path):
        (tmp_path / "empty.yaml").write_text("", encoding="utf-8")
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        loaded = store.load_all(str(tmp_path))
        assert loaded == []

    # -- load_all with invalid pattern dict (KeyError in _dict_to_pattern) --
    def test_load_all_invalid_pattern_dict(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "bad.yaml", {"id": "x"})  # missing required fields
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        loaded = store.load_all(str(tmp_path))
        assert loaded == []

    # -- get() (line 60) --
    def test_get_found(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "p.yaml", self._sample_pattern_dict())
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore(directory=tmp_path)
        p = store.get("p1")
        assert p is not None
        assert p.id == "p1"

    def test_get_not_found(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        assert store.get("nonexistent") is None

    # -- list_all with filters (lines 72, 74, 76) --
    def test_list_all_no_filter(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "p.yaml", self._sample_pattern_dict())
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore(directory=tmp_path)
        results = store.list_all()
        assert len(results) == 1

    def test_list_all_filter_source_provider(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "p.yaml", self._sample_pattern_dict())
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore(directory=tmp_path)
        results = store.list_all(source_provider=CloudProvider.AWS)
        assert len(results) == 1
        results = store.list_all(source_provider=CloudProvider.AZURE)
        assert len(results) == 0

    def test_list_all_filter_target_provider(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "p.yaml", self._sample_pattern_dict())
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore(directory=tmp_path)
        results = store.list_all(target_provider=CloudProvider.GCP)
        assert len(results) == 1
        results = store.list_all(target_provider=CloudProvider.AWS)
        assert len(results) == 0

    def test_list_all_filter_language(self, tmp_path):
        self._write_pattern_yaml(tmp_path / "p.yaml", self._sample_pattern_dict())
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore(directory=tmp_path)
        results = store.list_all(language=Language.PYTHON)
        assert len(results) == 1
        results = store.list_all(language=Language.TYPESCRIPT)
        assert len(results) == 0

    # -- save() (line 81) --
    def test_save(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        pattern = _make_pattern(id="new_p")
        store.save(pattern)
        assert store.get("new_p") is not None

    # -- delete() (line 84) --
    def test_delete(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        pattern = _make_pattern(id="del_p")
        store.save(pattern)
        store.delete("del_p")
        assert store.get("del_p") is None

    def test_delete_nonexistent(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        store.delete("nope")  # should not raise

    # -- find_by_id() (line 88) --
    def test_find_by_id(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        pattern = _make_pattern(id="find_me")
        store.save(pattern)
        assert store.find_by_id("find_me") is not None
        assert store.find_by_id("nope") is None

    # -- find_by_service() (lines 92-93) --
    def test_find_by_service(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        store.save(_make_pattern(id="p1", source_provider=CloudProvider.AWS, source_service="s3"))
        store.save(_make_pattern(id="p2", source_provider=CloudProvider.AZURE, source_service="blob"))
        results = store.find_by_service("aws", "s3")
        assert len(results) == 1
        assert results[0].id == "p1"

    def test_find_by_service_not_found(self):
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        store.save(_make_pattern(id="p1"))
        results = store.find_by_service("gcp", "storage")
        assert results == []

    # -- _dict_to_pattern with defaults --
    def test_dict_to_pattern_defaults(self, tmp_path):
        """Pattern YAML without name/description/match_pattern/transform_spec uses defaults."""
        data = {
            "id": "minimal",
            "source_provider": "aws",
            "source_service": "s3",
            "target_provider": "gcp",
            "target_service": "gcs",
            "language": "python",
        }
        self._write_pattern_yaml(tmp_path / "p.yaml", data)
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore(directory=tmp_path)
        p = store.get("minimal")
        assert p is not None
        assert p.name == "minimal"  # defaults to id
        assert p.description == ""
        assert p.match_pattern == ""
        assert p.transform_spec == {}
        assert p.confidence == ConfidenceScore(0.5)
        assert p.tags == []

    # -- load from subdirectory (recursive rglob) --
    def test_load_all_recursive(self, tmp_path):
        sub = tmp_path / "sub" / "dir"
        self._write_pattern_yaml(sub / "deep.yaml", self._sample_pattern_dict(id="deep1"))
        from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
        store = LocalPatternStore()
        loaded = store.load_all(str(tmp_path))
        assert len(loaded) == 1
        assert loaded[0].id == "deep1"


# ===================================================================
# 10. SQLiteProjectRepository
# ===================================================================

class TestSQLiteProjectRepository:
    """Tests for sqlite_repository.py using in-memory SQLite."""

    @pytest.fixture
    def repo(self, tmp_path):
        from cloudshift.infrastructure.persistence.sqlite_repository import SQLiteProjectRepository
        db_path = tmp_path / "test.db"
        return SQLiteProjectRepository(db_path=db_path)

    # -- __init__ (lines 50-55) --
    def test_init_creates_table(self, repo):
        # Table should exist after init
        row = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'",
        ).fetchone()
        assert row is not None

    # -- save() (lines 58-77) --
    def test_save(self, repo):
        project = _make_project()
        pid = repo.save(project)
        assert isinstance(pid, str)
        assert len(pid) == 12

    # -- get() (lines 80-85) --
    def test_get_existing(self, repo):
        project = _make_project()
        pid = repo.save(project)
        result = repo.get(pid)
        assert result is not None
        assert result.name == "test-project"
        assert result.source_provider == CloudProvider.AWS
        assert result.target_provider == CloudProvider.GCP
        assert result.status == ProjectStatus.CREATED
        assert result.file_patterns == ["*.py"]
        assert result.exclude_paths == ["venv"]

    def test_get_nonexistent(self, repo):
        assert repo.get("nonexistent") is None

    # -- list_all() (lines 88-91) --
    def test_list_all(self, repo):
        repo.save(_make_project(name="proj1"))
        repo.save(_make_project(name="proj2"))
        all_projects = repo.list_all()
        assert len(all_projects) == 2

    def test_list_all_empty(self, repo):
        assert repo.list_all() == []

    # -- delete() (lines 94-98) --
    def test_delete_existing(self, repo):
        pid = repo.save(_make_project())
        assert repo.delete(pid) is True
        assert repo.get(pid) is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete("nope") is False

    # -- update_status() (lines 101-105) --
    def test_update_status(self, repo):
        pid = repo.save(_make_project())
        repo.update_status(pid, "SCANNING")
        project = repo.get(pid)
        assert project is not None
        assert project.status == ProjectStatus.SCANNING

    # -- close() (line 108) --
    def test_close(self, repo):
        repo.close()
        # After close, operations should fail
        with pytest.raises(Exception):
            repo.list_all()

    # -- _row_to_project with different providers (line 112) --
    def test_row_to_project_azure(self, repo):
        project = _make_project(
            source_provider=CloudProvider.AZURE,
            target_provider=CloudProvider.AWS,
        )
        pid = repo.save(project)
        result = repo.get(pid)
        assert result.source_provider == CloudProvider.AZURE
        assert result.target_provider == CloudProvider.AWS

    def test_row_to_project_gcp(self, repo):
        project = _make_project(
            source_provider=CloudProvider.GCP,
            target_provider=CloudProvider.AZURE,
        )
        pid = repo.save(project)
        result = repo.get(pid)
        assert result.source_provider == CloudProvider.GCP
        assert result.target_provider == CloudProvider.AZURE

    def test_row_to_project_unknown_provider_defaults(self, repo):
        """Unknown provider string falls back to default in _PROVIDER_MAP.get()."""
        # Insert row with unknown provider directly
        repo._conn.execute(
            """INSERT INTO projects (id, name, root_path, source_prov, target_prov,
               status, file_patterns, exclude_paths) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("test_id", "test", "/tmp", "UNKNOWN", "UNKNOWN", "UNKNOWN", "[]", "[]"),
        )
        repo._conn.commit()
        result = repo.get("test_id")
        assert result is not None
        # Should get defaults
        assert result.source_provider == CloudProvider.AWS  # default
        assert result.target_provider == CloudProvider.GCP  # default
        assert result.status == ProjectStatus.CREATED  # default


# ===================================================================
# 11. LocalFileSystem
# ===================================================================

class TestLocalFileSystem:
    """Tests for local_fs.py."""

    @pytest.fixture
    def fs(self):
        from cloudshift.infrastructure.file_system.local_fs import LocalFileSystem
        return LocalFileSystem()

    # -- read (line 24) --
    def test_read(self, fs, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content", encoding="utf-8")
        assert fs.read(f) == "content"

    # -- write (lines 27-28) --
    def test_write(self, fs, tmp_path):
        f = tmp_path / "sub" / "out.txt"
        fs.write(f, "data")
        assert f.read_text(encoding="utf-8") == "data"

    # -- list_files (lines 33-41) --
    def test_list_files_nonexistent_dir(self, fs, tmp_path):
        result = fs.list_files(tmp_path / "nonexistent")
        assert result == []

    def test_list_files_no_patterns(self, fs, tmp_path):
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.ts").write_text("b")
        result = fs.list_files(tmp_path)
        assert len(result) == 2

    def test_list_files_with_patterns(self, fs, tmp_path):
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.ts").write_text("b")
        (tmp_path / "c.py").write_text("c")
        result = fs.list_files(tmp_path, patterns=["*.py"])
        assert len(result) == 2
        assert all(str(p).endswith(".py") for p in result)

    # -- exists (line 44) --
    def test_exists_true(self, fs, tmp_path):
        f = tmp_path / "exist.txt"
        f.write_text("x")
        assert fs.exists(f) is True

    def test_exists_false(self, fs, tmp_path):
        assert fs.exists(tmp_path / "nope.txt") is False

    # -- copy_file (lines 48-49) --
    def test_copy_file(self, fs, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        dst = tmp_path / "nested" / "dst.txt"
        fs.copy_file(src, dst)
        assert dst.read_text() == "hello"

    # -- remove (lines 53-56) --
    def test_remove_existing(self, fs, tmp_path):
        f = tmp_path / "del.txt"
        f.write_text("delete me")
        assert fs.remove(f) is True
        assert not f.exists()

    def test_remove_nonexistent(self, fs, tmp_path):
        assert fs.remove(tmp_path / "nope.txt") is False

    # -- mkdir (line 60) --
    def test_mkdir(self, fs, tmp_path):
        d = tmp_path / "a" / "b" / "c"
        fs.mkdir(d)
        assert d.is_dir()


# ===================================================================
# 12. SubprocessTestRunner
# ===================================================================

class TestSubprocessTestRunner:
    """Tests for test_runner.py."""

    @pytest.fixture
    def runner(self):
        from cloudshift.infrastructure.validation.test_runner import SubprocessTestRunner
        return SubprocessTestRunner()

    # -- run_tests with pyproject.toml (lines 26-28) --
    @pytest.mark.asyncio
    async def test_run_tests_python_project(self, runner, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        with patch("cloudshift.infrastructure.validation.test_runner.SubprocessTestRunner._run_pytest") as mock_pytest:
            mock_pytest.return_value = TestResult(passed=True, total=5, output="5 passed")
            result = await runner.run_tests(str(tmp_path))
        assert result.passed is True
        mock_pytest.assert_called_once()

    # -- run_tests with setup.py (lines 27-28) --
    @pytest.mark.asyncio
    async def test_run_tests_setup_py_project(self, runner, tmp_path):
        (tmp_path / "setup.py").write_text("setup()")
        with patch("cloudshift.infrastructure.validation.test_runner.SubprocessTestRunner._run_pytest") as mock_pytest:
            mock_pytest.return_value = TestResult(passed=True)
            result = await runner.run_tests(str(tmp_path))
        assert result.passed
        mock_pytest.assert_called_once()

    # -- run_tests with package.json (lines 29-30) --
    @pytest.mark.asyncio
    async def test_run_tests_node_project(self, runner, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        with patch("cloudshift.infrastructure.validation.test_runner.SubprocessTestRunner._run_npm_test") as mock_npm:
            mock_npm.return_value = TestResult(passed=True)
            result = await runner.run_tests(str(tmp_path))
        assert result.passed
        mock_npm.assert_called_once()

    # -- run_tests with no config (lines 31-34) --
    @pytest.mark.asyncio
    async def test_run_tests_no_config(self, runner, tmp_path):
        result = await runner.run_tests(str(tmp_path))
        assert result.passed is False
        assert "No test configuration found" in result.output

    # -- _run_pytest (lines 37-39) --
    @pytest.mark.asyncio
    async def test_run_pytest(self, runner, tmp_path):
        with patch("cloudshift.infrastructure.validation.test_runner.SubprocessTestRunner._exec") as mock_exec:
            mock_exec.return_value = TestResult(passed=True)
            result = await runner._run_pytest(tmp_path, timeout=60)
        assert result.passed

    # -- _run_npm_test (lines 42-44) --
    @pytest.mark.asyncio
    async def test_run_npm_test(self, runner, tmp_path):
        with patch("cloudshift.infrastructure.validation.test_runner.SubprocessTestRunner._exec") as mock_exec:
            mock_exec.return_value = TestResult(passed=True)
            result = await runner._run_npm_test(tmp_path, timeout=60)
        assert result.passed

    # -- _exec success (lines 49-69) --
    @pytest.mark.asyncio
    async def test_exec_success(self, runner, tmp_path):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"5 passed in 1.0s", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", return_value=(b"5 passed in 1.0s", b"")):
                mock_proc.communicate.return_value = (b"5 passed in 1.0s", b"")
                # Directly call _exec
                result = await runner._exec(["pytest"], tmp_path, timeout=60)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_exec_failure(self, runner, tmp_path):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"2 passed, 1 failed in 2.0s\nFAILED test_x.py::test_a", b"")
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", return_value=(b"2 passed, 1 failed in 2.0s\nFAILED test_x.py::test_a", b"")):
                result = await runner._exec(["pytest"], tmp_path, timeout=60)
        assert result.passed is False

    # -- _exec timeout (lines 70-74) --
    @pytest.mark.asyncio
    async def test_exec_timeout(self, runner, tmp_path):
        mock_proc = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                result = await runner._exec(["pytest"], tmp_path, timeout=1)
        assert result.passed is False
        assert "timed out" in result.output

    # -- _exec file not found (lines 75-78) --
    @pytest.mark.asyncio
    async def test_exec_file_not_found(self, runner, tmp_path):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("pytest not found")):
            result = await runner._exec(["pytest"], tmp_path, timeout=60)
        assert result.passed is False
        assert "not found" in result.output

    # -- _exec with None stdout (line 59) --
    @pytest.mark.asyncio
    async def test_exec_none_stdout(self, runner, tmp_path):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (None, b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", return_value=(None, b"")):
                result = await runner._exec(["pytest"], tmp_path, timeout=60)
        assert result.passed is True
        assert result.output == ""

    # -- _parse_test_output (lines 84-104) --
    def test_parse_test_output_passed(self):
        from cloudshift.infrastructure.validation.test_runner import _parse_test_output
        total, failures, errors, failed = _parse_test_output("5 passed in 1.0s")
        assert total == 5
        assert failures == 0
        assert errors == 0
        assert failed == []

    def test_parse_test_output_mixed(self):
        from cloudshift.infrastructure.validation.test_runner import _parse_test_output
        output = "3 passed, 2 failed, 1 error in 5.0s\nFAILED test_x.py::test_bad"
        total, failures, errors, failed = _parse_test_output(output)
        assert total == 3 + 2 + 1  # 6
        assert failures == 2
        assert errors == 1
        assert "FAILED test_x.py::test_bad" in failed

    def test_parse_test_output_no_summary(self):
        from cloudshift.infrastructure.validation.test_runner import _parse_test_output
        total, failures, errors, failed = _parse_test_output("no summary here")
        assert total == 0
        assert failures == 0
        assert errors == 0
        assert failed == []

    def test_parse_test_output_only_errors(self):
        from cloudshift.infrastructure.validation.test_runner import _parse_test_output
        total, failures, errors, failed = _parse_test_output("3 error in 2.0s")
        assert errors == 3
        assert total == 3

    def test_parse_test_output_errors_plural(self):
        from cloudshift.infrastructure.validation.test_runner import _parse_test_output
        total, failures, errors, failed = _parse_test_output("2 errors in 2.0s")
        assert errors == 2


# ===================================================================
# 13. Container (DI)
# ===================================================================

class TestContainer:
    """Tests for dependency_injection.py."""

    @pytest.fixture(autouse=True)
    def _patch_all(self):
        """Patch all adapter constructors to avoid real Rust/DB/HTTP initialization."""
        targets = [
            "RustParserAdapter",
            "RustDetectorAdapter",
            "RustPatternEngineAdapter",
            "RustDiffAdapter",
            "RustWalkerAdapter",
            "LocalFileSystem",
            "RustValidationAdapter",
            "SubprocessTestRunner",
            "SQLiteProjectRepository",
            "LocalPatternStore",
            "OllamaAdapter",
            "NullLLMAdapter",
        ]
        self._patchers = {}
        self._mocks = {}
        for name in targets:
            target = f"cloudshift.infrastructure.config.dependency_injection.{name}"
            p = patch(target)
            self._mocks[name] = p.start()
            self._patchers[name] = p

        yield

        for p in self._patchers.values():
            p.stop()

    def _make_container(self, **settings_kwargs):
        from cloudshift.infrastructure.config.dependency_injection import Container
        from cloudshift.infrastructure.config.settings import Settings
        s = Settings(**settings_kwargs)
        return Container(settings=s)

    # -- settings property (line 47) --
    def test_settings_property(self):
        c = self._make_container()
        assert c.settings is not None

    # -- parser (line 61 via _make_parser) --
    def test_parser_lazy_creation(self):
        c = self._make_container()
        p1 = c.parser
        p2 = c.parser
        assert p1 is p2  # cached

    # -- detector (line 67 via _make_detector) --
    def test_detector(self):
        c = self._make_container()
        d = c.detector
        assert d is not None
        # second call returns same instance
        assert c.detector is d

    # -- pattern_engine (line 77 via _make_pattern_engine) --
    def test_pattern_engine_no_patterns_dir(self, tmp_path):
        # patterns_dir doesn't exist as a directory
        c = self._make_container(patterns_dir=tmp_path / "nonexistent")
        pe = c.pattern_engine
        assert pe is not None

    def test_pattern_engine_with_patterns_dir(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        c = self._make_container(patterns_dir=tmp_path)
        pe = c.pattern_engine
        assert pe is not None

    # -- diff (line 83 via _make_diff) --
    def test_diff(self):
        c = self._make_container()
        assert c.diff is not None

    # -- walker (line 87 via _make_walker) --
    def test_walker(self):
        c = self._make_container()
        assert c.walker is not None

    # -- file_system (line 93 via _make_file_system) --
    def test_file_system(self):
        c = self._make_container()
        assert c.file_system is not None

    # -- validation (line 105 via _make_validation) --
    def test_validation(self):
        c = self._make_container()
        assert c.validation is not None

    # -- test_runner (line 116 via _make_test_runner) --
    def test_test_runner(self):
        c = self._make_container()
        assert c.test_runner is not None

    # -- project_repository (line 120 via _make_project_repository) --
    def test_project_repository(self):
        c = self._make_container()
        assert c.project_repository is not None

    # -- pattern_store (line 123 via _make_pattern_store) --
    def test_pattern_store(self):
        c = self._make_container()
        assert c.pattern_store is not None

    # -- llm with ollama enabled (lines 129, 132, 135, 138, 144-150) --
    def test_llm_ollama_enabled(self):
        c = self._make_container(llm_enabled=True)
        llm = c.llm
        assert llm is not None
        # Should have called OllamaAdapter
        self._mocks["OllamaAdapter"].assert_called_once()

    def test_llm_null_disabled(self):
        c = self._make_container(llm_enabled=False)
        llm = c.llm
        assert llm is not None
        self._mocks["NullLLMAdapter"].assert_called_once()

    # -- close() (lines 161-168) --
    @pytest.mark.asyncio
    async def test_close_with_llm_and_repo(self):
        c = self._make_container(llm_enabled=True)
        # Trigger creation of llm and project_repository
        _ = c.llm
        _ = c.project_repository

        # Make the llm mock have an async close
        llm_instance = c._instances["llm"]
        llm_instance.close = AsyncMock()

        repo_instance = c._instances["project_repository"]
        repo_instance.close = MagicMock()

        await c.close()
        llm_instance.close.assert_awaited_once()
        repo_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_resources(self):
        c = self._make_container()
        # Should not raise when no resources instantiated
        await c.close()

    @pytest.mark.asyncio
    async def test_close_llm_without_close_method(self):
        """LLM instance without close attribute should be handled gracefully."""
        c = self._make_container(llm_enabled=True)
        _ = c.llm
        # Remove close attribute from llm mock
        llm_instance = c._instances["llm"]
        del llm_instance.close
        # Should not raise
        await c.close()

    @pytest.mark.asyncio
    async def test_close_repo_without_close_method(self):
        """Repo without close attribute should be handled gracefully."""
        c = self._make_container()
        _ = c.project_repository
        repo_instance = c._instances["project_repository"]
        del repo_instance.close
        await c.close()

    # -- resolve() (lines 156-202) --
    def test_resolve_scan_project(self):
        from cloudshift.application.use_cases import ScanProjectUseCase
        c = self._make_container()
        uc = c.resolve(ScanProjectUseCase)
        assert isinstance(uc, ScanProjectUseCase)

    def test_resolve_generate_plan(self):
        from cloudshift.application.use_cases import GeneratePlanUseCase
        c = self._make_container()
        uc = c.resolve(GeneratePlanUseCase)
        assert isinstance(uc, GeneratePlanUseCase)

    def test_resolve_apply_transformation(self):
        from cloudshift.application.use_cases import ApplyTransformationUseCase
        c = self._make_container()
        uc = c.resolve(ApplyTransformationUseCase)
        assert isinstance(uc, ApplyTransformationUseCase)

    def test_resolve_validate_transformation(self):
        from cloudshift.application.use_cases import ValidateTransformationUseCase
        c = self._make_container()
        uc = c.resolve(ValidateTransformationUseCase)
        assert isinstance(uc, ValidateTransformationUseCase)

    def test_resolve_manage_patterns(self):
        from cloudshift.application.use_cases import ManagePatternsUseCase
        c = self._make_container()
        uc = c.resolve(ManagePatternsUseCase)
        assert isinstance(uc, ManagePatternsUseCase)

    def test_resolve_generate_report(self):
        from cloudshift.application.use_cases import GenerateReportUseCase
        c = self._make_container()
        uc = c.resolve(GenerateReportUseCase)
        assert isinstance(uc, GenerateReportUseCase)

    def test_resolve_unknown_raises(self):
        c = self._make_container()
        with pytest.raises(ValueError, match="Unknown use case"):
            c.resolve(str)

    # -- config() / _ConfigAccessor (lines 204-249) --
    def test_config_get_existing_key(self):
        c = self._make_container()
        cfg = c.config()
        assert cfg.get("project_name") == "cloudshift"

    def test_config_get_missing_key(self):
        c = self._make_container()
        cfg = c.config()
        assert cfg.get("nonexistent") is None

    def test_config_set_string(self):
        c = self._make_container()
        cfg = c.config()
        cfg.set("project_name", "newname")
        assert c.settings.project_name == "newname"

    def test_config_set_bool(self):
        c = self._make_container()
        cfg = c.config()
        cfg.set("llm_enabled", "true")
        assert c.settings.llm_enabled is True

    def test_config_set_int(self):
        c = self._make_container()
        cfg = c.config()
        cfg.set("test_timeout", "600")
        assert c.settings.test_timeout == 600

    def test_config_set_float(self):
        c = self._make_container()
        cfg = c.config()
        cfg.set("ollama_timeout", "60.5")
        assert c.settings.ollama_timeout == 60.5

    def test_config_as_dict(self):
        c = self._make_container()
        cfg = c.config()
        d = cfg.as_dict()
        assert isinstance(d, dict)
        assert "project_name" in d


# ===================================================================
# 14. Settings
# ===================================================================

class TestSettings:
    """Tests for settings.py."""

    def test_default_values(self):
        from cloudshift.infrastructure.config.settings import Settings
        s = Settings()
        assert s.project_name == "cloudshift"
        assert s.db_path == Path("cloudshift.db")
        assert s.patterns_dir == Path("patterns")
        assert s.deployment_mode == "client"
        assert s.llm_enabled is False
        assert s.ollama_base_url == "http://localhost:11434"
        assert s.ollama_model == "qwen2:latest"
        assert s.ollama_timeout == 120.0
        assert s.auth_mode == "api_key"
        assert s.gemini_api_key is None
        assert s.test_timeout == 300
        assert s.max_residual_refs == 0
        assert s.log_level == "INFO"
        assert s.debug is False

    def test_explicit_values(self):
        from cloudshift.infrastructure.config.settings import Settings
        s = Settings(
            project_name="myproject",
            db_path=Path("/tmp/my.db"),
            patterns_dir=Path("/patterns"),
            llm_enabled=True,
            ollama_base_url="http://other:1234",
            ollama_model="llama2",
            ollama_timeout=60.0,
            test_timeout=120,
            max_residual_refs=5,
            log_level="DEBUG",
            debug=True,
        )
        assert s.project_name == "myproject"
        assert s.db_path == Path("/tmp/my.db")
        assert s.llm_enabled is True
        assert s.ollama_model == "llama2"
        assert s.debug is True

    def test_env_var_loading(self, monkeypatch):
        from cloudshift.infrastructure.config.settings import Settings
        monkeypatch.setenv("CLOUDSHIFT_PROJECT_NAME", "env_project")
        monkeypatch.setenv("CLOUDSHIFT_LLM_ENABLED", "true")
        monkeypatch.setenv("CLOUDSHIFT_LOG_LEVEL", "WARNING")
        monkeypatch.setenv("CLOUDSHIFT_DEBUG", "1")
        monkeypatch.setenv("CLOUDSHIFT_OLLAMA_MODEL", "env_model")
        s = Settings()
        assert s.project_name == "env_project"
        assert s.llm_enabled is True
        assert s.log_level == "WARNING"
        assert s.debug is True
        assert s.ollama_model == "env_model"

    def test_extra_ignored(self):
        """Extra keys should be silently ignored (extra='ignore')."""
        from cloudshift.infrastructure.config.settings import Settings
        s = Settings(nonexistent_field="ignored")
        assert s.project_name == "cloudshift"
