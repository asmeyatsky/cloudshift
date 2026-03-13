"""Unit tests for apply route: _infer_language, _llm_fallback_refactor, and _run_apply with LLM fallback.

Covers:
- _infer_language for .py, .ts, .tsx, .js, .jsx, .tf, .hcl, template files, unknown
- _llm_fallback_refactor returns [] when no LLM or NullLLMAdapter
- _llm_fallback_refactor returns [] when root is not a dir or manifest has no entries
- _llm_fallback_refactor with real temp dir + file and mocked LLM returns refactored details
- _run_apply when pattern apply returns 0 modified_file_details and LLM fallback fills them
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cloudshift.domain.value_objects.types import Language


# ---------------------------------------------------------------------------
# _infer_language
# ---------------------------------------------------------------------------


class TestInferLanguage:
    """Tests for _infer_language helper."""

    def test_python(self):
        from cloudshift.presentation.api.routes.apply import _infer_language

        assert _infer_language("main.py") == Language.PYTHON
        assert _infer_language("src/foo.py") == Language.PYTHON
        assert _infer_language(".py") == Language.PYTHON

    def test_typescript_and_js(self):
        from cloudshift.presentation.api.routes.apply import _infer_language

        assert _infer_language("app.ts") == Language.TYPESCRIPT
        assert _infer_language("app.tsx") == Language.TYPESCRIPT
        assert _infer_language("index.js") == Language.TYPESCRIPT
        assert _infer_language("index.jsx") == Language.TYPESCRIPT

    def test_hcl_terraform(self):
        from cloudshift.presentation.api.routes.apply import _infer_language

        assert _infer_language("main.tf") == Language.HCL
        assert _infer_language("vars.hcl") == Language.HCL

    def test_cloudformation_template(self):
        from cloudshift.presentation.api.routes.apply import _infer_language

        assert _infer_language("config.yaml") == Language.PYTHON  # no "template" in path
        assert _infer_language("template.yaml") == Language.CLOUDFORMATION  # "template" in path
        assert _infer_language("template.yml") == Language.CLOUDFORMATION
        assert _infer_language("my-template.yaml") == Language.CLOUDFORMATION
        assert _infer_language("cf/template.json") == Language.CLOUDFORMATION

    def test_unknown_defaults_python(self):
        from cloudshift.presentation.api.routes.apply import _infer_language

        assert _infer_language("file.txt") == Language.PYTHON
        assert _infer_language("") == Language.PYTHON


# ---------------------------------------------------------------------------
# _llm_fallback_refactor
# ---------------------------------------------------------------------------


class TestLlmFallbackRefactor:
    """Tests for _llm_fallback_refactor."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_llm(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        container = SimpleNamespace(llm=None)
        plan = SimpleNamespace(project_id="p1")
        manifest = SimpleNamespace(root_path="/tmp", entries=[SimpleNamespace(file_path="x.py")])
        result = await _llm_fallback_refactor(container, plan, manifest)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_null_llm_adapter(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        class NullLLMAdapter:
            pass

        container = SimpleNamespace(llm=NullLLMAdapter())
        plan = SimpleNamespace(project_id="p1")
        manifest = SimpleNamespace(root_path="/nonexistent", entries=[])
        result = await _llm_fallback_refactor(container, plan, manifest)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_root_not_dir(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        llm = AsyncMock()
        container = SimpleNamespace(llm=llm)
        plan = SimpleNamespace(project_id="p1")
        manifest = SimpleNamespace(root_path="/nonexistent/path", entries=[SimpleNamespace(file_path="x.py")])
        result = await _llm_fallback_refactor(container, plan, manifest)
        assert result == []
        llm.transform_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_entries(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        llm = AsyncMock()
        container = SimpleNamespace(llm=llm)
        plan = SimpleNamespace(project_id="p1")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = SimpleNamespace(
                root_path=tmp,
                source_provider="aws",
                target_provider="gcp",
                entries=[],
            )
            result = await _llm_fallback_refactor(container, plan, manifest)
        assert result == []
        llm.transform_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_refactored_detail_when_file_exists_and_llm_returns_code(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        llm = AsyncMock()
        llm.transform_code = AsyncMock(return_value="from google.cloud import storage\n# GCP code")
        container = SimpleNamespace(llm=llm)
        plan = SimpleNamespace(project_id="p1")
        with tempfile.TemporaryDirectory() as tmp:
            py_file = Path(tmp) / "main.py"
            py_file.write_text("import boto3\ns3 = boto3.client('s3')", encoding="utf-8")
            manifest = SimpleNamespace(
                root_path=tmp,
                source_provider="AWS",
                target_provider="GCP",
                entries=[SimpleNamespace(file_path="main.py", path="main.py")],
            )
            result = await _llm_fallback_refactor(container, plan, manifest)
        assert len(result) == 1
        assert result[0]["path"] == "main.py"
        assert result[0]["original_content"] == "import boto3\ns3 = boto3.client('s3')"
        assert result[0]["modified_content"] == "from google.cloud import storage\n# GCP code"
        assert result[0]["language"] == "python"
        llm.transform_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_entry_with_empty_file_path(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        llm = AsyncMock()
        container = SimpleNamespace(llm=llm)
        plan = SimpleNamespace(project_id="p1")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = SimpleNamespace(
                root_path=tmp,
                source_provider="aws",
                target_provider="gcp",
                entries=[SimpleNamespace(file_path="", path="")],
            )
            result = await _llm_fallback_refactor(container, plan, manifest)
        assert result == []
        llm.transform_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_path_outside_root(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        llm = AsyncMock()
        container = SimpleNamespace(llm=llm)
        plan = SimpleNamespace(project_id="p1")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = SimpleNamespace(
                root_path=tmp,
                source_provider="aws",
                target_provider="gcp",
                entries=[SimpleNamespace(file_path="../../../etc/passwd", path="../../../etc/passwd")],
            )
            result = await _llm_fallback_refactor(container, plan, manifest)
        assert result == []
        llm.transform_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_original_content_when_llm_raises(self):
        from cloudshift.presentation.api.routes.apply import _llm_fallback_refactor

        llm = AsyncMock()
        llm.transform_code = AsyncMock(side_effect=RuntimeError("LLM error"))
        container = SimpleNamespace(llm=llm)
        plan = SimpleNamespace(project_id="p1")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "main.py").write_text("original", encoding="utf-8")
            manifest = SimpleNamespace(
                root_path=tmp,
                source_provider="aws",
                target_provider="gcp",
                entries=[SimpleNamespace(file_path="main.py", path="main.py")],
            )
            result = await _llm_fallback_refactor(container, plan, manifest)
        assert len(result) == 1
        assert result[0]["modified_content"] == "original"


# ---------------------------------------------------------------------------
# _run_apply with LLM fallback
# ---------------------------------------------------------------------------


class TestRunApplyLlmFallback:
    """Tests for _run_apply when pattern apply returns 0 files and LLM fallback runs."""

    @pytest.mark.asyncio
    async def test_run_apply_fills_modified_file_details_via_llm_fallback_when_zero_from_use_case(self):
        from cloudshift.application.dtos.transform import TransformRequest
        from cloudshift.presentation.api.routes.apply import _run_apply, _results
        from cloudshift.presentation.api.websocket import manager

        use_case = AsyncMock()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "plan_id": "plan1",
            "applied_steps": [],
            "diffs": [],
            "files_modified": 0,
            "success": True,
            "errors": [],
            "modified_file_details": [],
        }
        use_case.execute.return_value = mock_result

        plan = SimpleNamespace(plan_id="plan1", project_id="proj1")
        manifest = SimpleNamespace(
            root_path="/tmp",
            source_provider="aws",
            target_provider="gcp",
            entries=[SimpleNamespace(file_path="main.py", path="main.py")],
        )
        project_repo = MagicMock()
        project_repo.get_manifest = AsyncMock(return_value=None)  # no manifest -> no fallback files to read

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "main.py").write_text("import boto3", encoding="utf-8")
            manifest.root_path = tmp
            manifest.entries = [SimpleNamespace(file_path="main.py", path="main.py")]
            project_repo.get_manifest = AsyncMock(return_value=manifest)

            llm = AsyncMock()
            llm.transform_code = AsyncMock(return_value="from google.cloud import storage")
            container = MagicMock()
            container.project_repository = project_repo
            container.llm = llm

            dto = TransformRequest(plan_id="plan1")

            with patch("cloudshift.presentation.api.routes.apply.get_plan", AsyncMock(return_value=plan)):
                with patch.object(manager, "broadcast", new_callable=AsyncMock):
                    await _run_apply("job-llm", use_case, dto, container)

        assert "job-llm" in _results
        data = _results["job-llm"]
        assert data["files_modified"] == 1
        assert len(data["modified_file_details"]) == 1
        assert data["modified_file_details"][0]["path"] == "main.py"
        assert data["modified_file_details"][0]["modified_content"] == "from google.cloud import storage"
        _results.pop("job-llm", None)

    @pytest.mark.asyncio
    async def test_run_apply_no_fallback_when_plan_not_found(self):
        from cloudshift.application.dtos.transform import TransformRequest
        from cloudshift.presentation.api.routes.apply import _run_apply, _results
        from cloudshift.presentation.api.websocket import manager

        use_case = AsyncMock()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "plan_id": "plan1",
            "applied_steps": [],
            "diffs": [],
            "files_modified": 0,
            "success": True,
            "errors": [],
            "modified_file_details": [],
        }
        use_case.execute.return_value = mock_result
        container = MagicMock()
        container.project_repository = MagicMock()

        dto = TransformRequest(plan_id="plan1")
        with patch("cloudshift.presentation.api.routes.apply.get_plan", AsyncMock(return_value=None)):
            with patch.object(manager, "broadcast", new_callable=AsyncMock):
                await _run_apply("job-noplan", use_case, dto, container)

        assert _results["job-noplan"]["files_modified"] == 0
        assert _results["job-noplan"]["modified_file_details"] == []
        _results.pop("job-noplan", None)
