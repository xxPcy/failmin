# FailMin Launch Kit

Use these as starting points. Adapt the wording to each community and follow each community's self-promotion rules.

## Core story

An AI agent failed after a long trace. The useful question was not only "what failed?" but "which pieces of context were actually necessary for the failure?"

FailMin applies delta debugging to AI/Agent traces. In the bundled demo it reduces a 16-event failure to 3 critical events while preserving the failure.

```text
Original trace: 16 events
Minimal failure: 3 events
Reduction: 81.2%
Failure still reproduced ✓
```

Install:

```bash
pip install failmin
failmin demo
```

Repository: https://github.com/xxPcy/failmin
PyPI: https://pypi.org/project/failmin/

---

## Hacker News

Suggested title:

> Show HN: FailMin – Delta debugging for AI agent failures

Suggested body:

> I built FailMin, a small Python tool for reducing long AI/Agent failure traces into minimal reproducible failures.
>
> The idea is similar to git bisect / delta debugging, but the removable units are messages, tool calls, retrieval results, files, and other trace events. Candidate reductions are replayed, dependencies are preserved, and non-deterministic failures can be sampled with a reproduction threshold.
>
> The bundled demo goes from 16 events to 3 while preserving the failure. It works without an API key:
>
> `pip install failmin && failmin demo`
>
> The core is framework-neutral. LangGraph/OpenAI adapters are the next milestone. Feedback on the trace model and replay boundary would be especially useful.
>
> https://github.com/xxPcy/failmin

---

## Reddit

Suggested title:

> I built a delta debugger for long LLM/agent failure traces

Suggested post:

> Debugging agent failures gets painful when a run contains many turns, tools, retrieved chunks, and stale context. I wanted a way to answer: which pieces are actually required for the failure to happen?
>
> I built FailMin, an open-source Python tool that repeatedly removes parts of a trace, preserves dependencies, replays the candidate, and keeps only removals that still reproduce the failure.
>
> Demo: 16 events → 3 critical events, 81.2% reduction, failure still reproduced.
>
> `pip install failmin`
>
> Repo: https://github.com/xxPcy/failmin
>
> I would especially appreciate feedback from people debugging RAG/agent/tool-use systems. What trace formats or frameworks would be most useful to support next?

---

## X / Twitter

> I built FailMin: delta debugging for AI/Agent failures.
>
> Long agent trace → repeatedly remove messages/tools/docs → replay → keep only what is required to reproduce the failure.
>
> Demo: 16 events → 3 events (81.2% smaller) ✓
>
> `pip install failmin`
>
> https://github.com/xxPcy/failmin

---

## LinkedIn

> AI agent debugging often produces the wrong artifact: a giant trace.
>
> The more useful artifact is a minimal reproducible failure.
>
> I built FailMin, an open-source Python tool inspired by delta debugging and git bisect. It minimizes messages, tool calls, retrieval results, files, and other trace elements while preserving dependencies and replaying candidates to verify that the failure still occurs.
>
> The built-in demo reduces 16 events to 3 critical events (81.2%) with no API key required.
>
> `pip install failmin`
>
> https://github.com/xxPcy/failmin

---

## V2EX

Suggested title:

> [开源] FailMin：把 AI Agent 的长失败轨迹缩成最小可复现案例

Suggested body:

> 做 Agent / RAG 的时候经常遇到一个问题：一次错误执行可能有几十条消息、很多次 tool call、很多检索 chunk，最后知道“错了”，但不知道到底哪些上下文是导致错误所必需的。
>
> 我做了一个开源工具 FailMin，思路类似 git bisect + delta debugging：不断删掉 trace 的一部分，保持依赖关系，再 replay 验证失败是否还存在，最终得到更小的 minimal reproducible failure。
>
> 内置 demo：16 个 event → 3 个关键 event，缩减 81.2%，失败仍可复现。
>
> 安装：`pip install failmin`
>
> GitHub: https://github.com/xxPcy/failmin
>
> 目前核心、概率式复现、cache、hierarchical reduction、HTML/JSON report 已经可用，接下来准备做 LangGraph / OpenAI adapter。欢迎提意见，尤其想知道大家最常用什么 Agent trace 格式。

---

## 掘金 / 知乎文章题目

- 我把 git bisect 的思路用到了 AI Agent 调试：FailMin 的设计与实现
- Agent 跑了几十步才失败，怎么找到真正导致错误的那几步？
- 从 16 个事件缩到 3 个：用 Delta Debugging 调试 LLM Agent

Recommended article structure:

1. A concrete long-trace failure.
2. Why logs/observability alone do not isolate causal context.
3. Delta debugging and dependency-preserving reduction.
4. Non-determinism: runs + threshold.
5. Before/after demo.
6. Architecture and framework-neutral replay boundary.
7. Install command and repository link.
8. Ask readers which adapter should be built next.

---

## What not to do

- Do not post only "please star my repo".
- Do not spam unrelated issues or communities.
- Do not claim framework support that is still experimental.
- Lead with a concrete debugging problem and measurable before/after result.
