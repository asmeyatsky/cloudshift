"""DAG-based parallel-safe workflow orchestrator with topological ordering."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine


class NodeStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class DAGNode:
    """A single node in the execution DAG."""

    node_id: str
    action: Callable[..., Coroutine[Any, Any, Any]]
    depends_on: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Exception | None = None


class DAGOrchestrator:
    """Execute a DAG of async tasks with bounded parallelism and topological ordering.

    Usage::

        dag = DAGOrchestrator(max_parallel=4)
        dag.add_node("scan", scan_coro)
        dag.add_node("plan", plan_coro, depends_on=["scan"])
        dag.add_node("transform", transform_coro, depends_on=["plan"])
        results = await dag.execute()
    """

    def __init__(self, max_parallel: int = 4) -> None:
        self._nodes: dict[str, DAGNode] = {}
        self._semaphore = asyncio.Semaphore(max_parallel)

    def add_node(
        self,
        node_id: str,
        action: Callable[..., Coroutine[Any, Any, Any]],
        depends_on: list[str] | None = None,
    ) -> None:
        """Register a node in the DAG."""
        if node_id in self._nodes:
            raise ValueError(f"Duplicate node id: {node_id!r}")
        self._nodes[node_id] = DAGNode(
            node_id=node_id,
            action=action,
            depends_on=depends_on or [],
        )

    def reset(self) -> None:
        """Reset all node statuses for re-execution."""
        for node in self._nodes.values():
            node.status = NodeStatus.PENDING
            node.result = None
            node.error = None

    async def execute(self) -> dict[str, Any]:
        """Execute the DAG respecting dependencies and parallelism bounds.

        Returns a mapping of ``node_id -> result`` for completed nodes.
        Raises :class:`DAGExecutionError` if a cycle is detected.
        """
        self._validate_no_cycles()

        # Build reverse dependency index: node_id -> set of nodes that depend on it.
        dependents: dict[str, set[str]] = defaultdict(set)
        for node in self._nodes.values():
            for dep in node.depends_on:
                dependents[dep].add(node.node_id)

        # Track in-degree for each node.
        in_degree: dict[str, int] = {}
        for node in self._nodes.values():
            in_degree[node.node_id] = len([d for d in node.depends_on if d in self._nodes])

        done_event: dict[str, asyncio.Event] = {nid: asyncio.Event() for nid in self._nodes}
        ready_queue: asyncio.Queue[str] = asyncio.Queue()

        # Seed the queue with zero-dependency nodes.
        for nid, deg in in_degree.items():
            if deg == 0:
                await ready_queue.put(nid)

        completed_count = 0
        total = len(self._nodes)

        async def worker() -> None:
            nonlocal completed_count
            while completed_count < total:
                try:
                    nid = await asyncio.wait_for(ready_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if completed_count >= total:
                        break
                    continue

                node = self._nodes[nid]
                async with self._semaphore:
                    # Skip if any dependency failed.
                    failed_deps = [
                        d for d in node.depends_on if self._nodes[d].status == NodeStatus.FAILED
                    ]
                    if failed_deps:
                        node.status = NodeStatus.SKIPPED
                    else:
                        node.status = NodeStatus.RUNNING
                        try:
                            # Pass results of dependencies to the action.
                            dep_results = {d: self._nodes[d].result for d in node.depends_on}
                            node.result = await node.action(dep_results) if node.depends_on else await node.action()
                            node.status = NodeStatus.COMPLETED
                        except Exception as exc:
                            node.error = exc
                            node.status = NodeStatus.FAILED

                completed_count += 1
                done_event[nid].set()

                # Unblock dependents.
                for dep_nid in dependents.get(nid, set()):
                    in_degree[dep_nid] -= 1
                    if in_degree[dep_nid] <= 0:
                        await ready_queue.put(dep_nid)

        # Spawn workers equal to parallelism limit.
        workers = [asyncio.create_task(worker()) for _ in range(min(self._semaphore._value, total))]
        await asyncio.gather(*workers)

        return {nid: node.result for nid, node in self._nodes.items() if node.status == NodeStatus.COMPLETED}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_no_cycles(self) -> None:
        """Raise if the DAG contains a cycle (Kahn's algorithm)."""
        in_deg = {nid: 0 for nid in self._nodes}
        for node in self._nodes.values():
            for dep in node.depends_on:
                if dep in in_deg:
                    in_deg[node.node_id] += 1

        queue = [nid for nid, d in in_deg.items() if d == 0]
        visited = 0
        while queue:
            nid = queue.pop()
            visited += 1
            for node in self._nodes.values():
                if nid in node.depends_on:
                    in_deg[node.node_id] -= 1
                    if in_deg[node.node_id] == 0:
                        queue.append(node.node_id)

        if visited != len(self._nodes):
            raise DAGExecutionError("Cycle detected in DAG; cannot determine execution order.")

    @property
    def nodes(self) -> dict[str, DAGNode]:
        return dict(self._nodes)


class DAGExecutionError(Exception):
    """Raised when the DAG cannot be executed (e.g., cycle detected)."""
