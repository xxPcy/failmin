from __future__ import annotations

from collections import defaultdict
from typing import Callable

from .graph import project
from .models import Trace


def _partition(items: list[str], n: int) -> list[list[str]]:
    chunk_size = max(1, (len(items) + n - 1) // n)
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def ddmin(trace: Trace, reproduces: Callable[[Trace], bool]) -> tuple[Trace, int]:
    """Dependency-aware ddmin over event IDs.

    Minimality is 1-minimal with respect to removable event IDs after dependency closure.
    """
    current = trace
    tests = 0
    n = 2

    while len(current.events) >= 2:
        ids = [e.id for e in current.events]
        chunks = _partition(ids, n)
        reduced = False

        for chunk in chunks:
            keep = set(ids) - set(chunk)
            if not keep:
                continue
            candidate = project(current, keep)
            if len(candidate.events) >= len(current.events):
                continue
            tests += 1
            if reproduces(candidate):
                current = candidate
                n = max(n - 1, 2)
                reduced = True
                break

        if reduced:
            continue
        if n >= len(current.events):
            break
        n = min(len(current.events), n * 2)

    # Final linear pass catches dependency-closure cases that partitioning can miss.
    changed = True
    while changed:
        changed = False
        for event in list(current.events):
            keep = {e.id for e in current.events if e.id != event.id}
            if not keep:
                continue
            candidate = project(current, keep)
            if len(candidate.events) >= len(current.events):
                continue
            tests += 1
            if reproduces(candidate):
                current = candidate
                changed = True
                break

    return current, tests


def hierarchical_ddmin(
    trace: Trace,
    reproduces: Callable[[Trace], bool],
    group_metadata_key: str = "group",
) -> tuple[Trace, int]:
    """Coarse-to-fine minimization using metadata groups before event-level ddmin.

    Events sharing ``metadata[group_metadata_key]`` are treated as one coarse unit.
    This is useful for retrieval documents/chunks, tool-call bundles, or conversation
    turns. Ungrouped events are left for the fine-grained ddmin pass.
    """
    current = trace
    tests = 0

    groups: dict[str, list[str]] = defaultdict(list)
    for event in current.events:
        group = event.metadata.get(group_metadata_key)
        if group is not None:
            groups[str(group)].append(event.id)

    group_names = list(groups)
    if len(group_names) >= 2:
        n = 2
        while len(group_names) >= 2:
            reduced = False
            for group_chunk in _partition(group_names, n):
                remove_ids = {
                    event_id
                    for group_name in group_chunk
                    for event_id in groups.get(group_name, [])
                }
                keep = {event.id for event in current.events} - remove_ids
                if not keep:
                    continue
                candidate = project(current, keep)
                if len(candidate.events) >= len(current.events):
                    continue
                tests += 1
                if reproduces(candidate):
                    current = candidate
                    retained = {event.id for event in current.events}
                    groups = {
                        name: [event_id for event_id in ids if event_id in retained]
                        for name, ids in groups.items()
                    }
                    groups = {name: ids for name, ids in groups.items() if ids}
                    group_names = list(groups)
                    n = max(2, n - 1)
                    reduced = True
                    break
            if reduced:
                continue
            if n >= len(group_names):
                break
            n = min(len(group_names), n * 2)

    fine, fine_tests = ddmin(current, reproduces)
    return fine, tests + fine_tests
