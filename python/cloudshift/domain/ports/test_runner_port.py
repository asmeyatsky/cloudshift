"""Test runner port protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TestResult:
    """Outcome of a test run."""

    passed: bool
    total: int = 0
    failures: int = 0
    errors: int = 0
    output: str = ""
    duration_seconds: float = 0.0
    failed_tests: list[str] = field(default_factory=list)


class TestRunnerPort(Protocol):
    """Port for running test suites against transformed code."""

    async def run_tests(self, project_root: str, *, timeout: int = 300) -> TestResult: ...
