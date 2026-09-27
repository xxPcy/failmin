import json
from pathlib import Path

import pytest

from failmin import RunResult, Trace, TraceEvent, minimize
from failmin.core.graph import project, validate_trace
from failmin.reports import report_dict, write_html_report, write_json_report


def test_dependency_projection_keeps_required_parent():
    trace = Trace((
        TraceEvent("call", "tool_call"),
        TraceEvent("result", "tool_result", dependencies=("call",)),
        TraceEvent("noise", "retrieval_result"),
    ))
    projected = project(trace, {"result"})
    assert [e.id for e in projected.events] == ["call", "result"]


def test_validate_trace_rejects_cycles():
    trace = Trace((
        TraceEvent("a", "message", dependencies=("b",)),
        TraceEvent("b", "message", dependencies=("a",)),
    ))
    with pytest.raises(ValueError, match="cycle"):
        validate_trace(trace)


def test_minimize_removes_noise_and_keeps_failure():
    trace = Trace((
        TraceEvent("noise1", "retrieval_result"),
        TraceEvent("user", "user_message"),
        TraceEvent("bad_doc", "file"),
        TraceEvent("noise2", "retrieval_result"),
        TraceEvent("answer", "model_output", dependencies=("user", "bad_doc")),
    ))

    def replay(candidate):
        ids = {e.id for e in candidate.events}
        return RunResult(output="wrong" if {"user", "bad_doc", "answer"}.issubset(ids) else "right")

    result = minimize(trace, replay, lambda r: r.output == "wrong")
    assert {e.id for e in result.minimal.events} == {"user", "bad_doc", "answer"}
    assert result.reduction == pytest.approx(0.4)


def test_probabilistic_reproduction_uses_threshold():
    trace = Trace((TraceEvent("failure", "model_output"),))
    outcomes = iter([True, True, True, True, False])

    def replay(_candidate):
        return RunResult(output="wrong" if next(outcomes) else "right")

    result = minimize(
        trace,
        replay,
        lambda r: r.output == "wrong",
        runs=5,
        threshold=0.8,
    )
    assert result.original_failures == 4
    assert result.original_runs == 5
    assert result.original_failure_rate == pytest.approx(0.8)


def test_probabilistic_reproduction_rejects_unstable_original():
    trace = Trace((TraceEvent("failure", "model_output"),))
    outcomes = iter([True, False, False, False, False])

    def replay(_candidate):
        return RunResult(output="wrong" if next(outcomes) else "right")

    with pytest.raises(ValueError, match="does not reproduce"):
        minimize(trace, replay, lambda r: r.output == "wrong", runs=5, threshold=0.8)


def test_hierarchical_strategy_reduces_grouped_noise():
    trace = Trace((
        TraceEvent("noise_a1", "retrieval_result", metadata={"group": "doc_a"}),
        TraceEvent("noise_a2", "retrieval_result", metadata={"group": "doc_a"}),
        TraceEvent("noise_b1", "retrieval_result", metadata={"group": "doc_b"}),
        TraceEvent("user", "user_message"),
        TraceEvent("bad_doc", "file", metadata={"group": "bad"}),
        TraceEvent("answer", "model_output", dependencies=("user", "bad_doc")),
    ))

    def replay(candidate):
        ids = {event.id for event in candidate.events}
        return RunResult(output="wrong" if {"user", "bad_doc", "answer"}.issubset(ids) else "right")

    result = minimize(
        trace,
        replay,
        lambda r: r.output == "wrong",
        strategy="hierarchical",
    )
    assert result.strategy == "hierarchical"
    assert {e.id for e in result.minimal.events} == {"user", "bad_doc", "answer"}


def test_reports_include_summary_and_trace(tmp_path: Path):
    trace = Trace((TraceEvent("failure", "model_output", output="wrong"),))
    result = minimize(trace, lambda _: RunResult(output="wrong"), lambda r: r.output == "wrong")

    data = report_dict(result)
    assert data["summary"]["minimal_events"] == 1
    assert data["critical_elements"][0]["id"] == "failure"

    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    write_json_report(result, json_path)
    write_html_report(result, html_path)

    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    assert parsed["summary"]["original_events"] == 1
    assert "FailMin Report" in html_path.read_text(encoding="utf-8")
