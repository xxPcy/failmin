from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any

from .core.models import MinimizeResult


def report_dict(result: MinimizeResult) -> dict[str, Any]:
    before = len(result.original.events)
    after = len(result.minimal.events)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "original_events": before,
            "minimal_events": after,
            "reduction": result.reduction,
            "evaluations": result.tests_run,
            "replay_calls": result.replay_calls,
            "cache_hits": result.cache_hits,
            "strategy": result.strategy,
            "original_failure_rate": result.original_failure_rate,
        },
        "critical_elements": [
            {
                "id": event.id,
                "type": event.type,
                "dependencies": list(event.dependencies),
                "metadata": event.metadata,
            }
            for event in result.minimal.events
        ],
        "minimal_trace": result.minimal.to_dict(),
    }


def write_json_report(result: MinimizeResult, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(report_dict(result), indent=2, ensure_ascii=False, default=repr) + "\n",
        encoding="utf-8",
    )


def write_html_report(result: MinimizeResult, path: str | Path) -> None:
    data = report_dict(result)
    summary = data["summary"]
    rows = "\n".join(
        "<tr>"
        f"<td><code>{escape(str(item['id']))}</code></td>"
        f"<td>{escape(str(item['type']))}</td>"
        f"<td>{escape(', '.join(item['dependencies']) or '—')}</td>"
        "</tr>"
        for item in data["critical_elements"]
    )
    minimal_json = escape(
        json.dumps(data["minimal_trace"], indent=2, ensure_ascii=False, default=repr)
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FailMin Report</title>
<style>
:root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ max-width: 980px; margin: 0 auto; padding: 32px 20px 64px; line-height: 1.5; }}
h1 {{ margin-bottom: 4px; }}
.muted {{ opacity: .72; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 12px; margin: 24px 0; }}
.card {{ border: 1px solid #8885; border-radius: 12px; padding: 16px; }}
.value {{ font-size: 1.5rem; font-weight: 700; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0 28px; }}
th, td {{ text-align: left; border-bottom: 1px solid #8885; padding: 10px 8px; vertical-align: top; }}
pre {{ overflow: auto; border: 1px solid #8885; border-radius: 12px; padding: 16px; }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
</style>
</head>
<body>
<h1>FailMin Report</h1>
<div class="muted">Generated {escape(data['generated_at'])}</div>
<div class="grid">
  <div class="card"><div class="muted">Original events</div><div class="value">{summary['original_events']}</div></div>
  <div class="card"><div class="muted">Minimal events</div><div class="value">{summary['minimal_events']}</div></div>
  <div class="card"><div class="muted">Reduction</div><div class="value">{summary['reduction']:.1%}</div></div>
  <div class="card"><div class="muted">Replay calls</div><div class="value">{summary['replay_calls']}</div></div>
</div>
<p><strong>Strategy:</strong> {escape(str(summary['strategy']))} &nbsp; · &nbsp;
<strong>Original failure rate:</strong> {summary['original_failure_rate']:.1%} &nbsp; · &nbsp;
<strong>Cache hits:</strong> {summary['cache_hits']}</p>
<h2>Critical elements</h2>
<table>
<thead><tr><th>ID</th><th>Type</th><th>Dependencies</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<h2>Minimal trace</h2>
<pre><code>{minimal_json}</code></pre>
</body>
</html>
"""
    Path(path).write_text(html, encoding="utf-8")
