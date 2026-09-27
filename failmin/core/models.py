from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


SCHEMA_VERSION = "0.2"


@dataclass(frozen=True)
class TraceEvent:
    id: str
    type: str
    timestamp: float | None = None
    input: Any = None
    output: Any = None
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TraceEvent":
        return cls(
            id=str(value["id"]),
            type=str(value["type"]),
            timestamp=value.get("timestamp"),
            input=value.get("input"),
            output=value.get("output"),
            dependencies=tuple(value.get("dependencies", [])),
            metadata=dict(value.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["dependencies"] = list(self.dependencies)
        return data


@dataclass(frozen=True)
class Trace:
    events: tuple[TraceEvent, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | list[dict[str, Any]]) -> "Trace":
        if isinstance(value, list):
            return cls(tuple(TraceEvent.from_dict(x) for x in value))
        return cls(
            tuple(TraceEvent.from_dict(x) for x in value.get("events", [])),
            dict(value.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "events": [e.to_dict() for e in self.events],
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class RunResult:
    output: Any = None
    exception: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MinimizeResult:
    original: Trace
    minimal: Trace
    tests_run: int
    replay_calls: int = 0
    cache_hits: int = 0
    original_failures: int = 1
    original_runs: int = 1
    strategy: str = "delta"

    @property
    def reduction(self) -> float:
        if not self.original.events:
            return 0.0
        return 1.0 - (len(self.minimal.events) / len(self.original.events))

    @property
    def original_failure_rate(self) -> float:
        if self.original_runs == 0:
            return 0.0
        return self.original_failures / self.original_runs
