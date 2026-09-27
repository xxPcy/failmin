# FailMin

**Delta debugging for AI / Agent failures.**

[English](README.md) | [简体中文](README.zh-CN.md)

FailMin turns a long AI / Agent failure trace into a **small reproducible failure** while preserving event dependencies.

Instead of only telling you *what failed*, FailMin tries to answer:

> Which messages, tool calls, retrieved documents, files, or context are actually necessary for this failure to happen?

```text
Original trace
Events        16
Failure rate  100.0%

Minimal failure
Events        3
Reduction     81.2%
Strategy      hierarchical

Critical elements:
- user (user_message)
- stale_policy (file)
- answer (model_output)

Failure still reproduced ✓
```

> **Status:** v0.2 alpha. The framework-neutral core, Generic JSON workflow, probabilistic reproduction, replay cache, hierarchical reduction, and reports work today. Framework-specific executable replay adapters are the next major milestone.

---

## Why FailMin?

AI failures are often buried inside large execution traces:

- an Agent called 20 tools before producing the wrong answer;
- a RAG pipeline retrieved 30 chunks but only one stale chunk caused the failure;
- a long system prompt contains one conflicting instruction;
- a coding Agent touched many files before a regression appeared;
- a multi-turn conversation contains stale or contradictory context.

Reading the whole trace manually is slow. FailMin applies ideas from **delta debugging** and `git bisect` to AI workflows and automatically searches for a much smaller failure-inducing subset.

---

## 60-second demo

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
failmin demo
```

The demo is deterministic and requires **no API key** and **no network access**.

Try the included Generic JSON example:

```bash
failmin minimize examples/trace.json \
  --output-contains "30 days" \
  --strategy hierarchical \
  --out minimal-trace.json \
  --report-json failmin-report.json \
  --report-html failmin-report.html
```

---

## What works in v0.2

- Framework-neutral `Trace` / `TraceEvent` schema
- Dependency validation and dependency-preserving projection
- Dependency-aware `ddmin`
- Hierarchical coarse-to-fine reduction
- Probabilistic reproduction with `runs` + `threshold`
- In-memory replay-decision cache
- Output / exception / callback failure predicates
- Generic JSON loader and writer
- JSON report output
- Self-contained HTML report output
- Zero-config CLI demo
- Python SDK boundary for custom frameworks
- GitHub Actions test matrix for Python 3.10–3.13

---

## Generic JSON trace

```json
{
  "schema_version": "0.2",
  "events": [
    {
      "id": "message_10",
      "type": "user_message",
      "input": "What is the refund period?",
      "dependencies": [],
      "metadata": {}
    },
    {
      "id": "policy_1",
      "type": "file",
      "output": "Refund period is 30 days.",
      "dependencies": [],
      "metadata": {"group": "policy_context"}
    },
    {
      "id": "answer_1",
      "type": "model_output",
      "output": "30 days",
      "dependencies": ["message_10", "policy_1"],
      "metadata": {}
    }
  ]
}
```

The core does not depend on OpenAI Agents, LangGraph, CrewAI, AutoGen, or another Agent framework. Framework-specific integrations belong in adapters.

---

## Python API

The minimal integration boundary is a replay function plus a failure predicate:

```python
from failmin import RunResult, Trace, minimize


def replay(trace: Trace) -> RunResult:
    result = run_my_agent(trace)
    return RunResult(output=result.text)


result = minimize(
    items=my_trace,
    replay=replay,
    failure=lambda result: result.output == "wrong answer",
)

print([event.id for event in result.minimal.events])
```

This design means FailMin can work with a framework it has never heard of, as long as you can convert the execution into a `Trace` and replay a candidate trace.

---

## Non-deterministic Agents

LLM and Agent runs are not always deterministic. A candidate might fail once and succeed on the next replay.

Use probabilistic reproduction:

```python
result = minimize(
    items=my_trace,
    replay=replay,
    failure=is_failure,
    runs=5,
    threshold=0.8,
)
```

This means a candidate is considered failure-inducing when at least 80% of the configured replay sample fails.

Equivalent CLI options:

```bash
failmin minimize trace.json \
  --output-contains "wrong answer" \
  --runs 5 \
  --threshold 0.8
```

For expensive replays, FailMin caches evaluated candidates during the minimization run.

---

## Hierarchical reduction

Flat event-by-event minimization can require many replays. FailMin can first remove larger groups and then refine the result.

Add a group to event metadata:

```json
{
  "id": "chunk_7",
  "type": "retrieval_result",
  "metadata": {
    "group": "document_refund_policy"
  }
}
```

Then run:

```bash
failmin minimize trace.json \
  --output-contains "wrong answer" \
  --strategy hierarchical
```

Typical groups include:

- all chunks from one retrieved document;
- one Agent turn;
- one tool-call/result bundle;
- one file or workspace unit.

You can use another metadata field with `--group-key`.

---

## Failure predicates

### Output predicate

```bash
failmin minimize trace.json --output-contains "30 days"
```

### Exception predicate

```bash
failmin minimize trace.json --exception-contains "KeyError"
```

### Python predicate

```python
result = minimize(
    items=my_trace,
    replay=replay,
    failure=lambda result: result.metadata["accuracy"] < 0.5,
)
```

A future milestone will add an optional LLM-judge predicate, but the minimizer itself does not require an LLM.

---

## Reports

Generate a machine-readable report:

```bash
--report-json failmin-report.json
```

Generate a standalone HTML report that can be opened locally or attached to a bug report:

```bash
--report-html failmin-report.html
```

Reports include reduction statistics, replay counts, failure rate, critical elements, dependencies, and the minimal trace.

---

## Architecture

```text
                 FailMin
                    │
        ┌───────────┴───────────┐
        │                       │
     Adapters                  Core
        │                       │
 Generic JSON              Trace Schema
 Framework adapters        Dependency Graph
        │                  Reducers
        │                  Reproduction
        └───────────┬───────────┘
                    │
               Replay Boundary
                    │
             Failure Predicate
                    │
                 Report
```

Repository layout:

```text
failmin/
├── failmin/
│   ├── adapters/
│   │   └── generic.py
│   ├── core/
│   │   ├── cache.py
│   │   ├── graph.py
│   │   ├── models.py
│   │   ├── predicates.py
│   │   ├── reducer.py
│   │   └── reproduction.py
│   ├── api.py
│   ├── cli.py
│   ├── demo.py
│   └── reports.py
├── examples/
├── tests/
└── .github/workflows/
```

---

## Design principles

1. **The core stays framework-neutral.** Adapters translate framework traces into the common schema.
2. **Reduction must preserve dependencies.** A tool result should not survive without the tool call it depends on.
3. **Deletion is only accepted after replay verification.** Heuristics can rank candidates, but they do not decide correctness.
4. **Non-determinism is explicit.** Failure reproduction can be sampled instead of assuming one run is truth.
5. **The first experience should be zero-config.** The demo works without credentials.

---

## Roadmap

### v0.1 — foundation ✅

- Generic trace model
- failure predicates
- dependency-aware delta debugging
- CLI
- zero-config demo

### v0.2 — reproducibility + reporting ✅

- probabilistic reproduction
- replay cache
- hierarchical reduction
- JSON / HTML reports
- stronger validation

### v0.3 — framework adapters

- LangGraph adapter
- OpenAI / Agents adapter
- executable replay protocol
- external-state snapshot / mock hooks

### v0.4 — smarter minimization

- LLM-guided candidate ordering
- root-cause explanation
- richer reproduction bundles

### v0.5 — ecosystem

- observability integrations
- trace importers
- adapter/plugin ecosystem

---

## Development

```bash
pip install -e '.[dev]'
pytest
```

Build the package:

```bash
python -m build
```

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT
