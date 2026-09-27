from __future__ import annotations

from .api import minimize
from .core.models import RunResult, Trace, TraceEvent


def demo_trace() -> Trace:
    events = []
    for i in range(1, 13):
        events.append(
            TraceEvent(
                id=f"context_{i}",
                type="retrieval_result",
                output=f"irrelevant chunk {i}",
                metadata={"group": f"noise_doc_{(i - 1) // 3 + 1}"},
            )
        )
    events.extend(
        [
            TraceEvent(id="user", type="user_message", input="What is the refund period?"),
            TraceEvent(
                id="stale_policy",
                type="file",
                output="Refunds are allowed within 30 days.",
                metadata={"group": "policy_context"},
            ),
            TraceEvent(
                id="current_policy",
                type="file",
                output="Refunds are allowed within 14 days.",
                metadata={"group": "policy_context"},
            ),
            TraceEvent(
                id="answer",
                type="model_output",
                output="30 days",
                dependencies=("user", "stale_policy"),
            ),
        ]
    )
    return Trace(tuple(events), {"demo": True})


def replay_demo(trace: Trace) -> RunResult:
    ids = {e.id for e in trace.events}
    # Deterministic stand-in for an expensive real Agent replay.
    output = "30 days" if {"user", "stale_policy", "answer"}.issubset(ids) else "14 days"
    return RunResult(output=output)


def run_demo(**kwargs):
    trace = demo_trace()
    return minimize(trace, replay_demo, lambda r: r.output == "30 days", **kwargs)
