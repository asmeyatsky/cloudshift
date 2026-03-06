"""Test runner adapter that executes pytest or npm test in a subprocess."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from cloudshift.domain.ports.test_runner_port import TestResult


class SubprocessTestRunner:
    """Implements TestRunnerPort by spawning pytest or npm test.

    Auto-detects the project type by checking for ``pyproject.toml`` /
    ``setup.py`` (Python) or ``package.json`` (Node).

    Protocol methods:
        run_tests(project_root, *, timeout) -> TestResult
    """

    async def run_tests(
        self, project_root: str, *, timeout: int = 300,
    ) -> TestResult:
        root = Path(project_root)
        if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
            return await self._run_pytest(root, timeout)
        if (root / "package.json").exists():
            return await self._run_npm_test(root, timeout)
        return TestResult(
            passed=False,
            output="No test configuration found (pyproject.toml, setup.py, or package.json).",
        )

    async def _run_pytest(self, root: Path, timeout: int) -> TestResult:
        pytest_bin = shutil.which("pytest") or "pytest"
        cmd = [pytest_bin, "--tb=short", "-q", "--no-header"]
        return await self._exec(cmd, root, timeout)

    async def _run_npm_test(self, root: Path, timeout: int) -> TestResult:
        npm_bin = shutil.which("npm") or "npm"
        cmd = [npm_bin, "test", "--", "--passWithNoTests"]
        return await self._exec(cmd, root, timeout)

    async def _exec(
        self, cmd: list[str], cwd: Path, timeout: int,
    ) -> TestResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout_bytes, _ = await asyncio.wait_for(
                proc.communicate(), timeout=timeout,
            )
            output = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
            passed = proc.returncode == 0
            total, failures, errors, failed_tests = _parse_test_output(output)
            return TestResult(
                passed=passed,
                total=total,
                failures=failures,
                errors=errors,
                output=output,
                failed_tests=failed_tests,
            )
        except asyncio.TimeoutError:
            return TestResult(
                passed=False,
                output=f"Test run timed out after {timeout}s.",
            )
        except FileNotFoundError as exc:
            return TestResult(
                passed=False,
                output=f"Test runner not found: {exc}",
            )


def _parse_test_output(output: str) -> tuple[int, int, int, list[str]]:
    """Best-effort parse of pytest summary line."""
    total = failures = errors = 0
    failed_tests: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        # pytest summary: "5 passed, 2 failed, 1 error in 3.4s"
        if "passed" in stripped or "failed" in stripped or "error" in stripped:
            for token in stripped.replace(",", " ").split():
                if token.isdigit():
                    num = int(token)
                elif token == "passed":
                    total += num  # type: ignore[possibly-undefined]
                elif token == "failed":
                    failures += num  # type: ignore[possibly-undefined]
                    total += num
                elif token.startswith("error"):
                    errors += num  # type: ignore[possibly-undefined]
                    total += num
        # Collect FAILED lines
        if stripped.startswith("FAILED"):
            failed_tests.append(stripped)
    return total, failures, errors, failed_tests
