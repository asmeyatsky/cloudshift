"""Git safety adapter for verifying repository state before transformations."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitSafety:
    """Provides git-related safety checks for project directories."""

    def is_repo_clean(self, project_path: str) -> bool:
        """Return True if the project is a clean git repository (no unstaged changes)."""
        try:
            # Check if it's a git repo
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=project_path,
                capture_output=True,
                check=True,
                text=True,
            )

            # Check for changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                check=True,
                text=True,
            )
            return not bool(result.stdout.strip())

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Not a git repo or git not installed; treat as "not clean" for safety
            # unless the user explicitly bypasses it.
            return False
