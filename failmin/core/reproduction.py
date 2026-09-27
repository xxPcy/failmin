from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

from .cache import ReplayCache
from .models import RunResult, Trace


@dataclass(frozen=True)
class ReproductionPolicy:
    """How many times a candidate must reproduce a failure.

    Example: runs=5, threshold=0.8 means at least 4/5 sampled replays must fail.
    """

    runs: int = 1
    threshold: float = 1.0

    def __post_init__(self) -> None:
        if self.runs < 1:
            raise ValueError("runs must be >= 1")
        if not 0 < self.threshold <= 1:
            raise ValueError("threshold must be in the interval (0, 1]")

    @property
    def required_failures(self) -> int:
        return math.ceil(self.runs * self.threshold)


@dataclass(frozen=True)
class ReproductionSample:
    reproduced: bool
    failures: int
    runs: int

    @property
    def failure_rate(self) -> float:
        return self.failures / self.runs if self.runs else 0.0


class ReproductionEvaluator:
    """Evaluate failure reproduction with optional probabilistic sampling and cache."""

    def __init__(
        self,
        replay: Callable[[Trace], RunResult],
        failure: Callable[[RunResult], bool],
        policy: ReproductionPolicy | None = None,
        cache: ReplayCache | None = None,
    ) -> None:
        self.replay = replay
        self.failure = failure
        self.policy = policy or ReproductionPolicy()
        self.cache = cache
        self.replay_calls = 0
        self.evaluations = 0

    def evaluate(self, trace: Trace) -> ReproductionSample:
        self.evaluations += 1
        cached = self.cache.get(trace) if self.cache is not None else None
        if cached is not None:
            failures = sum(cached)
            return ReproductionSample(
                reproduced=failures >= self.policy.required_failures,
                failures=failures,
                runs=len(cached),
            )

        outcomes: list[bool] = []
        failures = 0
        required = self.policy.required_failures

        for _ in range(self.policy.runs):
            result = self.replay(trace)
            self.replay_calls += 1
            failed = bool(self.failure(result))
            outcomes.append(failed)
            failures += int(failed)

        sample_tuple = tuple(outcomes)
        if self.cache is not None:
            self.cache.put(trace, sample_tuple)

        return ReproductionSample(
            reproduced=failures >= required,
            failures=failures,
            runs=self.policy.runs,
        )
