from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ..core.models import Trace


def load_trace(path: str | Path) -> Trace:
    with Path(path).open("r", encoding="utf-8") as f:
        return Trace.from_dict(json.load(f))


def save_trace(trace: Trace, path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(trace.to_dict(), f, indent=2, ensure_ascii=False)
        f.write("\n")
