from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from .models import Trace


def trace_fingerprint(trace: Trace) -> str:
    """Return a stable content fingerprint for a trace candidate."""
    payload = json.dumps(
        trace.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=repr,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass
class ReplayCache:
    """In-memory cache for candidate reproduction decisions.

    A cache entry stores the sampled failure outcomes for one exact trace candidate.
    This is safe for probabilistic reproduction within a minimization run because a
    candidate is evaluated once, then the same sampled batch is reused.
    """

    _entries: dict[str, tuple[bool, ...]] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def get(self, trace: Trace) -> tuple[bool, ...] | None:
        value = self._entries.get(trace_fingerprint(trace))
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        return value

    def put(self, trace: Trace, outcomes: tuple[bool, ...]) -> None:
        self._entries[trace_fingerprint(trace)] = outcomes

    def __len__(self) -> int:
        return len(self._entries)
