from __future__ import annotations

from typing import Any, Iterable

from ..core.models import Trace, TraceEvent


def from_response_items(items: Iterable[dict[str, Any]], *, metadata: dict[str, Any] | None = None) -> Trace:
    """Convert OpenAI Responses-style output items into a FailMin Trace.

    Supported item types include ``message``, ``function_call`` and
    ``function_call_output``. Unknown item types are preserved as generic events.
    This module has no OpenAI SDK dependency; pass dictionaries from your captured
    response/trace data.
    """

    events: list[TraceEvent] = []
    previous_id: str | None = None
    call_event_by_call_id: dict[str, str] = {}

    for index, item in enumerate(items):
        item_type = str(item.get("type", "event"))
        event_id = str(item.get("id") or f"openai_{index}")
        deps: list[str] = []

        if previous_id:
            deps.append(previous_id)

        event_type = item_type
        input_value: Any = item.get("input")
        output_value: Any = item.get("output")

        if item_type == "message":
            role = str(item.get("role", "assistant"))
            event_type = {
                "system": "system_message",
                "user": "user_message",
                "assistant": "assistant_message",
            }.get(role, "message")
            output_value = item.get("content")
        elif item_type == "function_call":
            event_type = "tool_call"
            call_id = str(item.get("call_id") or event_id)
            call_event_by_call_id[call_id] = event_id
            input_value = {
                "name": item.get("name"),
                "arguments": item.get("arguments"),
                "call_id": call_id,
            }
        elif item_type == "function_call_output":
            event_type = "tool_result"
            call_id = str(item.get("call_id") or "")
            if call_id and call_id in call_event_by_call_id:
                deps = [call_event_by_call_id[call_id]]
            output_value = item.get("output")

        event_metadata = {
            "adapter": "openai",
            "source_type": item_type,
        }
        for key in ("status", "role", "call_id", "name"):
            if key in item:
                event_metadata[key] = item[key]

        events.append(
            TraceEvent(
                id=event_id,
                type=event_type,
                input=input_value,
                output=output_value,
                dependencies=tuple(dict.fromkeys(deps)),
                metadata=event_metadata,
            )
        )
        previous_id = event_id

    trace_metadata = {"adapter": "openai"}
    if metadata:
        trace_metadata.update(metadata)
    return Trace(tuple(events), trace_metadata)
