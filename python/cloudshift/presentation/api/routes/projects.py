"""Project routes: create from snippet or clone from Git (client/demo - load code)."""

from __future__ import annotations

import re
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cloudshift.presentation.api.dependencies import get_settings

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Base dir for cloned repos (must match allowed_scan_paths).
GIT_IMPORT_BASE = Path("/tmp/cloudshift")


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


class FromGitBody(BaseModel):
    repo_url: str = Field(description="HTTPS Git repository URL (can be a GitHub tree URL, e.g. .../tree/main/python/)")
    branch: str = Field(default="main", description="Branch to clone")
    name: str = Field(description="Project name (used as directory under /tmp/cloudshift)")
    subpath: str | None = Field(default=None, description="Subfolder to use as scan root (e.g. 'python'). Overrides URL-derived subpath if set.")
    source_provider: str = Field(default="AWS", description="AWS or AZURE")
    target_provider: str = Field(default="GCP", description="Target cloud (GCP)")


def _safe_dir_name(name: str) -> str:
    """Sanitize name for use as a directory name (no path traversal, no leading dot)."""
    safe = re.sub(r"[^\w\-.]", "_", name.strip()).strip("._") or "repo"
    return safe[:128]


def _normalize_git_clone_url(repo_url: str) -> tuple[str, str | None]:
    """Convert GitHub/GitLab browser URLs to clone URLs. Returns (clone_url, subpath_or_none).
    e.g. https://github.com/owner/repo/tree/main/python/ -> (https://github.com/owner/repo.git, 'python')
    """
    url = repo_url.strip().rstrip("/")
    subpath: str | None = None
    # GitHub: .../owner/repo/tree/<branch>/path or /blob/<branch>/path
    m = re.match(r"(https?://github\.com/[^/]+/[^/]+?)(?:/tree/[^/]+(?:/(.+))?)?/?(?:#.*)?$", url, re.I)
    if m:
        base = m.group(1)
        if base.endswith(".git"):
            clone_url = base
        else:
            clone_url = base if base.endswith("/") else base + ".git"
        if m.lastindex >= 2 and m.group(2):
            subpath = m.group(2).rstrip("/").split("/")[0] or None  # first segment only for safety
        return (clone_url, subpath)
    # GitLab: .../owner/repo/-/tree/branch/path
    m = re.match(r"(https?://gitlab\.com/[^/]+(?:/[^/]+)*?)(?:/-/tree/[^/]+(?:/(.+))?)?/?(?:#.*)?$", url, re.I)
    if m:
        base = m.group(1).rstrip("/")
        clone_url = base + ".git" if not base.endswith(".git") else base
        if m.lastindex >= 2 and m.group(2):
            subpath = m.group(2).rstrip("/").split("/")[0] or None
        return (clone_url, subpath)
    # Already a clone URL or unknown; no subpath
    if "/tree/" in url or "/blob/" in url:
        # Strip trailing /tree/... or /blob/... so clone at least gets repo root
        for sep in ["/tree/", "/blob/"]:
            if sep in url:
                url = url.split(sep)[0].rstrip("/")
                break
        if re.match(r"https?://github\.com/[^/]+/[^/]+$", url, re.I):
            url = url if url.endswith(".git") else url + ".git"
    return (url, None)


@router.post("/from-git", summary="Clone a Git repo and register for scanning (AWS/Azure → GCP)")
async def create_from_git(
    body: FromGitBody,
    settings=Depends(get_settings),
) -> dict:
    """Clone repo into /tmp/cloudshift/{name} and return project_id and root_path for the pipeline."""
    if not body.repo_url.strip().lower().startswith("https://"):
        raise HTTPException(status_code=400, detail="Only HTTPS repo URLs are allowed")
    if not shutil.which("git"):
        raise HTTPException(status_code=503, detail="Git is not available in this environment")

    clone_url, subpath = _normalize_git_clone_url(body.repo_url)
    if not clone_url.lower().startswith("https://"):
        raise HTTPException(status_code=400, detail="Only HTTPS clone URLs are allowed")

    project_id = uuid.uuid4().hex[:12]
    dir_name = _safe_dir_name(body.name) or "repo"
    project_dir = (GIT_IMPORT_BASE / dir_name).resolve()
    if not str(project_dir).startswith(str(GIT_IMPORT_BASE.resolve())):
        raise HTTPException(status_code=400, detail="Invalid project name")

    GIT_IMPORT_BASE.mkdir(parents=True, exist_ok=True)
    if project_dir.exists():
        shutil.rmtree(project_dir)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", body.branch, clone_url, str(project_dir)],
            check=True,
            timeout=600,  # 10 min for large repos (e.g. azure-quickstart-templates)
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(status_code=504, detail="Clone timed out")
    except subprocess.CalledProcessError as e:
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Clone failed: {e.stderr or e.stdout or str(e)}")

    # Use explicit subpath from request, or URL-derived subpath (e.g. from .../tree/main/python/)
    use_subpath = (body.subpath or "").strip() or subpath
    root_path = str(project_dir)
    if use_subpath:
        # Disallow path traversal: only a single segment
        use_subpath = use_subpath.replace("\\", "/").strip("/").split("/")[0] or ""
    if use_subpath:
        subdir = (project_dir / use_subpath).resolve()
        if subdir.is_dir() and str(subdir).startswith(str(project_dir)):
            root_path = str(subdir)
        else:
            # Case-insensitive match (e.g. repo has "Python", user asked for "python")
            try:
                for entry in project_dir.iterdir():
                    if entry.is_dir() and entry.name.lower() == use_subpath.lower():
                        subdir = entry.resolve()
                        if str(subdir).startswith(str(project_dir)):
                            root_path = str(subdir)
                        break
            except OSError:
                pass
        # else: subpath not present in repo, keep full clone as root

    return {
        "project_id": project_id,
        "root_path": root_path,
        "name": body.name,
        "repo_url": clone_url,
        "branch": body.branch,
        "subpath": body.subpath.strip() if (body.subpath or "").strip() else (subpath or None),
    }
