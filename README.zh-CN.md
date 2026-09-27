# FailMin

**把冗长的 AI / Agent 失败轨迹，缩成更小、仍可复现的失败案例。**

[English](README.md) | [简体中文](README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/failmin)](https://pypi.org/project/failmin/)
[![Python](https://img.shields.io/pypi/pyversions/failmin)](https://pypi.org/project/failmin/)
[![Tests](https://github.com/xxPcy/failmin/actions/workflows/tests.yml/badge.svg)](https://github.com/xxPcy/failmin/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/xxPcy/failmin)](LICENSE)

```bash
pip install failmin
failmin demo
```

![FailMin demo](docs/demo.svg)

FailMin 把 **delta debugging** 用到 AI 工作流：不断尝试删除消息、工具调用、检索结果、文件和其它 trace event，然后 replay candidate，只保留那些“删除以后仍然能复现失败”的缩减结果。

可以把它理解成：**`git bisect` + delta debugging，但调试对象变成了 LLM / Agent trace。**

> 到底哪些上下文，是这个失败真正不可缺少的？

---

## 为什么需要 FailMin

AI 系统的错误通常埋在很长的执行轨迹里：

- Agent 调用了 20 个工具后才给错答案；
- RAG 检索了 30 个 chunk，但只有一个过期 chunk 真正导致错误；
- 长 Prompt 里只有一条 instruction 和其它规则冲突；
- Coding Agent 修改了很多文件以后才出现 regression；
- 多轮上下文混入了过期或互相矛盾的信息。

Observability 更擅长告诉你**发生了什么**。FailMin 进一步尝试找到**最小的 failure-inducing context**。

---

## 60 秒体验

内置 Demo 不需要 API Key，也不需要联网：

```bash
pip install failmin
failmin demo
```

典型输出：

```text
Original trace
Events        16
Failure rate  100.0%

Minimal failure
Events         3
Reduction     81.2%
Strategy      hierarchical

Critical elements:
- user (user_message)
- stale_policy (file)
- answer (model_output)

Failure still reproduced ✓
```

自己的 Generic JSON trace：

```bash
failmin minimize examples/trace.json \
  --output-contains "30 days" \
  --strategy hierarchical \
  --out minimal-trace.json \
  --report-json failmin-report.json \
  --report-html failmin-report.html
```

---

## 当前已经支持

- Framework-neutral `Trace` / `TraceEvent` schema
- Dependency validation 和 dependency-preserving reduction
- Dependency-aware `ddmin`
- Hierarchical coarse-to-fine minimization
- `runs + threshold` 概率式失败复现
- Replay decision cache
- Output / exception / callback predicates
- Generic JSON import/export
- JSON / HTML report
- 零配置 CLI demo
- Python API 自定义 replay 边界
- Python 3.10–3.13 CI

---

## Python API

最小接入只需要一个 replay 和一个 failure predicate：

```python
from failmin import RunResult, Trace, minimize


def replay(trace: Trace) -> RunResult:
    result = run_my_agent(trace)
    return RunResult(output=result.text)


result = minimize(
    items=my_trace,
    replay=replay,
    failure=lambda result: result.output == "wrong answer",
    runs=5,
    threshold=0.8,
)

print([event.id for event in result.minimal.events])
```

只要能把执行过程转换成 `Trace`，并且能够 replay candidate，FailMin Core 就不需要知道你具体使用哪个 Agent Framework。

---

## 处理 LLM / Agent 随机性

同一份输入可能一次失败、一次成功，所以 FailMin 可以按比例判断 failure 是否仍然成立：

```python
result = minimize(
    items=my_trace,
    replay=replay,
    failure=is_failure,
    runs=5,
    threshold=0.8,
)
```

这表示 candidate 需要在配置的 replay 样本中达到指定失败比例，才被认为仍然保留 failure。昂贵的 candidate evaluation 会在最小化过程中缓存。

---

## Hierarchical Reduction

Trace 天然存在大粒度结构：一份检索文档、一轮 Agent Turn、一组 Tool Call + Tool Result、一个文件等。

给 event 增加 group：

```json
{
  "id": "chunk_7",
  "type": "retrieval_result",
  "metadata": {"group": "document_refund_policy"}
}
```

然后：

```bash
failmin minimize trace.json \
  --output-contains "wrong answer" \
  --strategy hierarchical
```

FailMin 会先尝试粗粒度删除，再对剩余结果做更细粒度缩减。

---

## Report

```bash
failmin minimize trace.json \
  --output-contains "wrong answer" \
  --report-json failmin-report.json \
  --report-html failmin-report.html
```

报告包含缩减比例、Replay 次数、Failure Rate、Critical Elements、Dependencies 和 Minimal Trace。

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

设计原则：

1. Core 保持 Framework-neutral。
2. Reduction 必须保持依赖合法。
3. 删除元素前必须经过真实 replay 验证。
4. 显式处理 LLM 非确定性。
5. 第一次体验不需要任何凭证。

---

## Roadmap

### v0.1 — 基础 ✅
- Generic trace
- Failure predicate
- Dependency-aware delta debugging
- CLI
- 零配置 demo

### v0.2 — 稳定复现 + 报告 ✅
- Probabilistic reproduction
- Replay cache
- Hierarchical reduction
- JSON / HTML report
- 更严格 validation

### v0.3 — Framework Adapter 🚧
- LangGraph adapter
- OpenAI / Agents adapter
- Executable replay protocol
- 外部状态 snapshot / mock hook

### v0.4 — 智能最小化
- LLM-guided candidate ordering
- Root cause explanation
- Minimal reproduction bundle

### v0.5 — 生态
- Observability integration
- Trace importer
- Adapter / plugin ecosystem

---

## 开发

```bash
git clone https://github.com/xxPcy/failmin.git
cd failmin
pip install -e '.[dev]'
pytest
```

构建：

```bash
python -m build
```

欢迎贡献代码，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

推广和首发文案整理在 [docs/LAUNCH.md](docs/LAUNCH.md)。

## License

MIT
