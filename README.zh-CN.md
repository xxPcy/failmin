# FailMin

**面向 AI / Agent 失败的 Delta Debugging 工具。**

[English](README.md) | [简体中文](README.zh-CN.md)

FailMin 可以把一条很长的 AI / Agent 失败执行轨迹，自动缩减成一个**更小、仍然可以复现失败的案例**，同时保证事件之间的依赖关系不会被破坏。

它不只是告诉你“哪里失败了”，而是进一步回答：

> 到底哪些消息、工具调用、检索文档、文件或上下文，是维持这个失败所必需的？

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

> **当前状态：** v0.2 alpha。框架无关的核心算法、Generic JSON、概率式失败复现、Replay Cache、Hierarchical Reduction 和报告输出已经可用。下一阶段重点是接入 LangGraph、OpenAI Agents 等真实 Agent Framework 的可执行 Replay。

---

## 为什么需要 FailMin？

AI 系统的失败经常隐藏在非常长的执行轨迹里，例如：

- Agent 调用了 20 个工具以后才产生错误回答；
- RAG 一次检索了 30 个 chunk，但真正导致错误的只有一个过期文档；
- System Prompt 很长，其中只有一条 instruction 和其它规则发生冲突；
- Coding Agent 修改了很多文件以后出现 regression；
- 多轮会话中混入了过期、污染或互相矛盾的上下文。

手动阅读整条 Trace 非常低效。FailMin 把 **delta debugging** 和 `git bisect` 类似的思想应用到 AI Workflow 中，自动寻找一个更小的 failure-inducing subset。

---

## 60 秒体验

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
failmin demo
```

内置 Demo 是确定性的，**不需要 API Key，也不需要联网**。

也可以直接运行仓库里的 Generic JSON 示例：

```bash
failmin minimize examples/trace.json \
  --output-contains "30 days" \
  --strategy hierarchical \
  --out minimal-trace.json \
  --report-json failmin-report.json \
  --report-html failmin-report.html
```

---

## v0.2 已支持

- 框架无关的 `Trace` / `TraceEvent` Schema
- Trace 依赖关系校验和 dependency-preserving projection
- Dependency-aware `ddmin`
- Hierarchical coarse-to-fine reduction
- `runs + threshold` 概率式失败复现
- 内存 Replay Decision Cache
- Output / Exception / Callback Failure Predicate
- Generic JSON 读取和写入
- JSON 报告
- 自包含 HTML 报告
- 零配置 CLI Demo
- 方便其它框架接入的 Python SDK 边界
- Python 3.10–3.13 GitHub Actions 测试矩阵

---

## Generic JSON Trace

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

FailMin Core 不直接依赖 OpenAI Agents、LangGraph、CrewAI、AutoGen 或其它 Agent Framework。所有框架相关逻辑都应该放在 Adapter 层。

---

## Python API

最小接入方式只需要提供：

1. 一个 `replay(trace)`；
2. 一个用于判断失败是否发生的 `failure(result)`。

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

这也是 FailMin 迁移性的关键：即使 FailMin 完全不认识你的 Agent Framework，只要你能转换成 `Trace` 并且能够 Replay Candidate Trace，就可以使用核心算法。

---

## 处理 LLM / Agent 随机性

LLM 和 Agent 并不一定是确定性的。同一份输入可能：

```text
第一次 -> 失败
第二次 -> 成功
第三次 -> 失败
```

所以不能简单认为“一次失败 = 这个 Candidate 一定会失败”。

FailMin 支持概率式复现：

```python
result = minimize(
    items=my_trace,
    replay=replay,
    failure=is_failure,
    runs=5,
    threshold=0.8,
)
```

含义是：一个 Candidate 会被重放若干次，并达到配置的失败比例后，才认为“失败仍然被保留”。

CLI：

```bash
failmin minimize trace.json \
  --output-contains "wrong answer" \
  --runs 5 \
  --threshold 0.8
```

对于昂贵的 Agent Replay，FailMin 会在一次 Minimization 过程中缓存已经测试过的 Candidate，避免重复执行。

---

## Hierarchical Reduction

如果一条 Trace 有几十甚至几百个 Event，逐个删除测试可能需要大量 Replay。

FailMin 可以先按较大的逻辑单元删除，再进入 Event 级别精简。

例如给同一文档产生的 chunk 添加相同 group：

```json
{
  "id": "chunk_7",
  "type": "retrieval_result",
  "metadata": {
    "group": "document_refund_policy"
  }
}
```

然后：

```bash
failmin minimize trace.json \
  --output-contains "wrong answer" \
  --strategy hierarchical
```

典型 Group 可以是：

- 同一个 RAG Document 的所有 chunks；
- 一轮 Agent Turn；
- 一组 Tool Call + Tool Result；
- 一个文件或 Workspace 单元。

如果你的元数据字段不是 `group`，可以用 `--group-key` 指定其它字段。

---

## Failure Predicate

### Output Predicate

```bash
failmin minimize trace.json --output-contains "30 days"
```

### Exception Predicate

```bash
failmin minimize trace.json --exception-contains "KeyError"
```

### Python Predicate

```python
result = minimize(
    items=my_trace,
    replay=replay,
    failure=lambda result: result.metadata["accuracy"] < 0.5,
)
```

后续版本计划增加可选的 LLM Judge Predicate，但核心 Minimizer 本身不会强制依赖 LLM。

---

## 报告输出

生成机器可读 JSON Report：

```bash
--report-json failmin-report.json
```

生成可以直接在浏览器打开、也方便附加到 Issue/Bug Report 的独立 HTML：

```bash
--report-html failmin-report.html
```

报告会包含：

- 缩减前后的事件数量；
- Reduction 百分比；
- Replay 次数；
- Failure Rate；
- Critical Elements；
- Dependencies；
- Minimal Trace。

---

## 架构

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

项目结构：

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

## 设计原则

1. **Core 永远保持 Framework-neutral。** 不把 LangGraph/OpenAI 等依赖写死在核心算法中。
2. **Reduction 必须保持 Dependency 合法。** 不能留下 Tool Result 却删除它所依赖的 Tool Call。
3. **真正删除前必须经过 Replay 验证。** Heuristic 或 LLM 可以决定“先测试谁”，但不能直接决定某个元素一定可以删除。
4. **明确处理非确定性。** 不把单次 Replay 当成绝对真相。
5. **第一次体验必须足够简单。** 用户不应该为了理解项目价值先申请 API Key。

---

## Roadmap

### v0.1 — 基础能力 ✅

- Generic Trace
- Failure Predicate
- Dependency-aware Delta Debugging
- CLI
- 零配置 Demo

### v0.2 — 复现稳定性 + 报告 ✅

- Probabilistic Reproduction
- Replay Cache
- Hierarchical Reduction
- JSON / HTML Report
- 更严格的 Trace Validation

### v0.3 — Framework Adapter

- LangGraph Adapter
- OpenAI / Agents Adapter
- Executable Replay Protocol
- 外部状态 Snapshot / Mock Hook

### v0.4 — 智能最小化

- LLM-guided Candidate Ordering
- Root Cause Explanation
- 更完整的 Minimal Reproduction Bundle

### v0.5 — 生态

- Observability Integration
- Trace Importers
- Adapter / Plugin Ecosystem

---

## 开发

```bash
pip install -e '.[dev]'
pytest
```

构建 Package：

```bash
python -m build
```

欢迎贡献代码，开发规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## License

MIT
