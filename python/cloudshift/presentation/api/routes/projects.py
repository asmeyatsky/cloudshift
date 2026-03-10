"""Project routes: create from snippet (client mode - load code)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cloudshift.presentation.api.dependencies import get_settings

router = APIRouter(prefix="/api/projects", tags=["projects"])


class FromSnippetBody(BaseModel):
    name: str = Field(description="Project name")
    content: str = Field(description="Source code content")
    language: str = Field(default="PYTHON", description="PYTHON, TYPESCRIPT, etc.")
    source_provider: str = Field(default="AWS", description="AWS or AZURE")
    target_provider: str = Field(default="GCP", description="Target cloud (GCP)")
    filename: str | None = Field(default=None, description="Filename (e.g. main.py)")


def _default_filename(language: str) -> str:
    lang = language.upper()
    if lang == "PYTHON":
        return "main.py"
    if lang == "TYPESCRIPT" or lang == "JAVASCRIPT":
        return "main.ts"
    return "main.txt"


@router.post("/from-snippet", summary="Create a project from a code snippet (client)")
async def create_from_snippet(
    body: FromSnippetBody,
    settings=Depends(get_settings),
) -> dict:
    """Write snippet to a temp directory under data_dir and return project_id and root_path for scanning."""
    project_id = uuid.uuid4().hex[:12]
    snippets_dir = settings.data_dir / "snippets"
    project_dir = snippets_dir / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    filename = body.filename or _default_filename(body.language)
    # Security: strip path components to prevent path traversal (e.g. ../../../etc/passwd)
    safe_name = Path(filename).name
    if not safe_name or safe_name.startswith("."):
        safe_name = _default_filename(body.language)
    if not safe_name.endswith((".py", ".ts", ".js", ".tf", ".yaml", ".yml", ".json")):
        safe_name = _default_filename(body.language)
    path = (project_dir / safe_name).resolve()
    if not path.is_relative_to(project_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path.write_text(body.content, encoding="utf-8")

    root_path = str(project_dir.resolve())
    return {"project_id": project_id, "root_path": root_path, "name": body.name}
