#!/usr/bin/env python3
"""
Run the CloudShift pipeline (import → scan → plan → apply → validate) against
AWS and Azure sample repos (~5k–10k lines each).

Requires:
  - CloudShift API server running (e.g. uvicorn, default http://localhost:8000).
  - Git installed.
  - No extra Python deps (uses stdlib urllib). Set CLOUDSHIFT_BASE_URL and optional auth if needed.

Usage:
  python scripts/run_pipeline_e2e.py
  CLOUDSHIFT_BASE_URL=http://localhost:8000 python scripts/run_pipeline_e2e.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

BASE_URL = os.environ.get("CLOUDSHIFT_BASE_URL", "http://localhost:8000").rstrip("/")

# Repos: AWS (medium), Azure (smaller to avoid clone timeout; still 1k+ lines of cloud code).
AWS_REPO = "https://github.com/aws-samples/aws-cdk-examples"
AWS_BRANCH = "main"
AZURE_REPO = "https://github.com/Azure-Samples/bicep-github-actions"
AZURE_BRANCH = "main"


def headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    api_key = os.environ.get("CLOUDSHIFT_API_KEY")
    if api_key:
        h["X-API-Key"] = api_key
    token = os.environ.get("CLOUDSHIFT_BEARER_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _req(method: str, path: str, data: dict[str, Any] | None = None, timeout: int = 60) -> tuple[int, dict[str, Any]]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method, headers={**headers(), "Accept": "application/json"})
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            out = json.loads(body)
        except Exception:
            out = {"detail": body or f"{e.code} {e.reason}"}
        # Return (status, body) for 404 so poll_until can retry; raise for other errors.
        if e.code == 404:
            return 404, out
        raise RuntimeError(out.get("detail", out)) from e


def post(path: str, data: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    status, out = _req("POST", path, data, timeout=timeout)
    if status not in (200, 201, 202):
        raise RuntimeError(f"POST {path} -> {status}: {out}")
    return out


def get(path: str) -> tuple[int, dict[str, Any]]:
    status, out = _req("GET", path)
    return status, out


def poll_until(
    get_url: str,
    fail_if_error: bool = True,
    interval: float = 1.0,
    max_wait: float = 300,
) -> dict[str, Any]:
    """Poll GET get_url until 200 (result ready), then return JSON."""
    start = time.monotonic()
    while True:
        status, data = get(get_url)
        if status == 200:
            if fail_if_error and data.get("error"):
                raise RuntimeError(data["error"])
            return data
        if status != 404:
            raise RuntimeError(f"GET {get_url} -> {status}: {data}")
        if time.monotonic() - start > max_wait:
            raise TimeoutError(f"Polling {get_url} timed out after {max_wait}s")
        time.sleep(interval)


# Git clone can take several minutes for large repos (e.g. azure-quickstart-templates).
FROM_GIT_TIMEOUT = 600  # 10 minutes

def run_from_git(repo_url: str, branch: str, name: str, source: str, target: str) -> dict[str, Any]:
    return post("/api/projects/from-git", {
        "repo_url": repo_url,
        "branch": branch,
        "name": name,
        "source_provider": source,
        "target_provider": target,
    }, timeout=FROM_GIT_TIMEOUT)


def run_scan(root_path: str, source: str, target: str, project_id: str) -> str:
    r = post("/api/scan", {
        "root_path": root_path,
        "source_provider": source,
        "target_provider": target,
        "project_id": project_id,
    })
    job_id = r.get("job_id")
    if not job_id:
        raise RuntimeError("No job_id in scan response")
    return job_id


def run_plan(project_id: str, manifest_id: str) -> str:
    r = post("/api/plan", {
        "project_id": project_id,
        "manifest_id": manifest_id,
    })
    job_id = r.get("job_id")
    if not job_id:
        raise RuntimeError("No job_id in plan response")
    return job_id


def run_apply(plan_id: str) -> str:
    r = post("/api/apply", {"plan_id": plan_id})
    job_id = r.get("job_id")
    if not job_id:
        raise RuntimeError("No job_id in apply response")
    return job_id


def run_validate(plan_id: str) -> str:
    r = post("/api/validate", {"plan_id": plan_id})
    job_id = r.get("job_id")
    if not job_id:
        raise RuntimeError("No job_id in validate response")
    return job_id


def pipeline_one(name: str, root_path: str, project_id: str, source: str, target: str) -> dict[str, Any]:
    """Run scan → plan → apply → validate for one project. Returns summary dict."""
    summary: dict[str, Any] = {"name": name, "project_id": project_id, "error": None}
    try:
        # Scan
        scan_job = run_scan(root_path, source, target, project_id)
        scan_result = poll_until(f"/api/scan/{scan_job}", fail_if_error=True)
        summary["scan"] = {
            "total_files_scanned": scan_result.get("total_files_scanned", 0),
            "services_found": scan_result.get("services_found", []),
            "files_with_findings": len(scan_result.get("files", [])),
        }
        if not scan_result.get("files"):
            summary["plan"] = {"plan_id": None, "steps": 0, "message": "No files to plan"}
            return summary

        # Plan
        plan_job = run_plan(project_id, project_id)
        plan_result = poll_until(f"/api/plan/{plan_job}", fail_if_error=False)
        plan_id = plan_result.get("plan_id") or plan_result.get("error")
        summary["plan"] = {
            "plan_id": plan_id,
            "steps": len(plan_result.get("steps", [])),
            "error": plan_result.get("error"),
        }

        if not plan_id or plan_result.get("error"):
            return summary

        # Apply
        apply_job = run_apply(plan_id)
        apply_result = poll_until(f"/api/apply/{apply_job}", fail_if_error=False)
        summary["apply"] = {
            "files_modified": apply_result.get("files_modified", 0),
            "success": apply_result.get("success", False),
            "error": apply_result.get("error"),
        }

        # Validate
        validate_job = run_validate(plan_id)
        validate_result = poll_until(f"/api/validate/{validate_job}", fail_if_error=False)
        summary["validate"] = {
            "passed": validate_result.get("passed", False),
            "issues": len(validate_result.get("issues", [])),
            "error": validate_result.get("error"),
        }
    except Exception as e:
        summary["error"] = str(e)
    return summary


def main() -> None:
    print(f"CloudShift E2E pipeline – BASE_URL={BASE_URL}")
    print("Importing AWS and Azure sample repos...")

    # Import
    aws = run_from_git(AWS_REPO, AWS_BRANCH, "aws-demo", "AWS", "GCP")
    azure = run_from_git(AZURE_REPO, AZURE_BRANCH, "azure-demo", "AZURE", "GCP")

    aws_root = aws["root_path"]
    aws_id = aws["project_id"]
    azure_root = azure["root_path"]
    azure_id = azure["project_id"]

    print(f"  AWS   project_id={aws_id}  root_path={aws_root}")
    print(f"  Azure project_id={azure_id}  root_path={azure_root}")
    print()

    # Run pipeline for each
    for label, root_path, project_id, source in [
        ("AWS (aws-cdk-examples)", aws_root, aws_id, "AWS"),
        ("Azure (azure-quickstart-templates)", azure_root, azure_id, "AZURE"),
    ]:
        print(f"--- Pipeline: {label} ---")
        summary = pipeline_one(label, root_path, project_id, source, "GCP")
        if summary.get("error"):
            print(f"  ERROR: {summary['error']}")
        else:
            print(f"  Scan:   files_scanned={summary.get('scan', {}).get('total_files_scanned')}  files_with_findings={summary.get('scan', {}).get('files_with_findings')}")
            print(f"  Plan:   steps={summary.get('plan', {}).get('steps')}  plan_id={summary.get('plan', {}).get('plan_id')}")
            if "apply" in summary:
                print(f"  Apply:  files_modified={summary['apply'].get('files_modified')}  success={summary['apply'].get('success')}")
            if "validate" in summary:
                print(f"  Validate: passed={summary['validate'].get('passed')}  issues={summary['validate'].get('issues')}")
        print()

    print("Done. Check server logs for any backend errors.")


if __name__ == "__main__":
    main()
