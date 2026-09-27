from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol
from .models import RunResult


class FailurePredicate(Protocol):
    def __call__(self, result: RunResult) -> bool: ...


@dataclass(frozen=True)
class ExceptionPredicate:
    contains: str | None = None

    def __call__(self, result: RunResult) -> bool:
        if result.exception is None:
            return False
        return self.contains is None or self.contains in result.exception


@dataclass(frozen=True)
class OutputContainsPredicate:
    contains: str

    def __call__(self, result: RunResult) -> bool:
        return self.contains in str(result.output)


@dataclass(frozen=True)
class CallbackPredicate:
    callback: Callable[[RunResult], bool]

    def __call__(self, result: RunResult) -> bool:
        return bool(self.callback(result))
