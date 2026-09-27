from __future__ import annotations

from .models import Trace


def validate_trace(trace: Trace) -> None:
    ids = [e.id for e in trace.events]
    if len(ids) != len(set(ids)):
        raise ValueError("trace contains duplicate event ids")

    known = set(ids)
    by_id = {event.id: event for event in trace.events}
    for event in trace.events:
        missing = set(event.dependencies) - known
        if missing:
            raise ValueError(f"event {event.id!r} has missing dependencies: {sorted(missing)}")

    # Dependency relations should form a DAG. Cycles make replay ordering ambiguous.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(event_id: str) -> None:
        if event_id in visited:
            return
        if event_id in visiting:
            raise ValueError(f"trace dependency cycle detected at {event_id!r}")
        visiting.add(event_id)
        for dependency in by_id[event_id].dependencies:
            visit(dependency)
        visiting.remove(event_id)
        visited.add(event_id)

    for event_id in ids:
        visit(event_id)


def dependency_closure(trace: Trace, keep_ids: set[str]) -> set[str]:
    by_id = {e.id: e for e in trace.events}
    unknown = set(keep_ids) - set(by_id)
    if unknown:
        raise ValueError(f"unknown event ids: {sorted(unknown)}")

    keep = set(keep_ids)
    stack = list(keep)
    while stack:
        event_id = stack.pop()
        event = by_id[event_id]
        for dep in event.dependencies:
            if dep not in keep:
                keep.add(dep)
                stack.append(dep)
    return keep


def project(trace: Trace, keep_ids: set[str]) -> Trace:
    closed = dependency_closure(trace, keep_ids)
    return Trace(tuple(e for e in trace.events if e.id in closed), dict(trace.metadata))
