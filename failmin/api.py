from __future__ import annotations

from typing import Callable, Literal

from .core.cache import ReplayCache
from .core.graph import validate_trace
from .core.models import MinimizeResult, RunResult, Trace
from .core.reducer import ddmin, hierarchical_ddmin
from .core.reproduction import ReproductionEvaluator, ReproductionPolicy


def minimize(
    items: Trace,
    replay: Callable[[Trace], RunResult],
    failure: Callable[[RunResult], bool],
    *,
    runs: int = 1,
    threshold: float = 1.0,
    cache: bool = True,
    strategy: Literal["delta", "hierarchical"] = "delta",
    group_metadata_key: str = "group",
) -> MinimizeResult:
    """Minimize a failure-inducing trace.

    Existing v0.1 calls remain valid. ``runs`` and ``threshold`` enable probabilistic
    reproduction for non-deterministic agents. ``strategy='hierarchical'`` first
    removes coarse metadata groups, then performs event-level ddmin.
    """
    validate_trace(items)
    policy = ReproductionPolicy(runs=runs, threshold=threshold)
    replay_cache = ReplayCache() if cache else None
    evaluator = ReproductionEvaluator(replay, failure, policy=policy, cache=replay_cache)

    initial = evaluator.evaluate(items)
    if not initial.reproduced:
        raise ValueError(
            "the original trace does not reproduce the requested failure "
            f"({initial.failures}/{initial.runs} failed; threshold={threshold:.0%})"
        )

    def reproduces(candidate: Trace) -> bool:
        return evaluator.evaluate(candidate).reproduced

    if strategy == "delta":
        minimal, reducer_tests = ddmin(items, reproduces)
    elif strategy == "hierarchical":
        minimal, reducer_tests = hierarchical_ddmin(
            items,
            reproduces,
            group_metadata_key=group_metadata_key,
        )
    else:
        raise ValueError(f"unknown minimization strategy: {strategy!r}")

    return MinimizeResult(
        original=items,
        minimal=minimal,
        tests_run=reducer_tests + 1,
        replay_calls=evaluator.replay_calls,
        cache_hits=replay_cache.hits if replay_cache is not None else 0,
        original_failures=initial.failures,
        original_runs=initial.runs,
        strategy=strategy,
    )
