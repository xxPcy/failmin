from __future__ import annotations

from typing import Any, Iterable

from ..core.models import Trace, TraceEvent


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _message_type(message: Any) -> str:
    kind = _get(message, "type") or message.__class__.__name__.lower()
    mapping = {
        "human": "user_message",
        "humanmessage": "user_message",
        "user": "user_message",
        "ai": "assistant_message",
        "aimessage": "assistant_message",
        "assistant": "assistant_message",
        "system": "system_message",
        "systemmessage": "system_message",
        "tool": "tool_result",
        "toolmessage": "tool_result",
    }
    return mapping.get(str(kind).lower(), "message")


def from_messages(messages: Iterable[Any], *, metadata: dict[str, Any] | None = None) -> Trace:
    """Convert a LangGraph/LangChain-style message history into a FailMin Trace.

    This adapter intentionally uses duck typing so importing FailMin does not require
    LangGraph or LangChain. It accepts message objects with ``type``/``content``
    attributes as well as equivalent dictionaries.

    The adapter is an import boundary only; executable replay is supplied separately
    by the caller so application-specific graph state and external side effects remain
    under user control.
    """

    events: list[TraceEvent] = []
    previous_id: str | None = None

    for index, message in enumerate(messages):
        event_id = str(_get(message, "id") or f"message_{index}")
        event_type = _message_type(message)
        content = _get(message, "content")
        additional_kwargs = _get(message, "additional_kwargs", {}) or {}
        response_metadata = _get(message, "response_metadata", {}) or {}

        dependencies: tuple[str, ...] = (previous_id,) if previous_id else ()
        event_metadata: dict[str, Any] = {
            "adapter": "langgraph",
            "source_type": str(_get(message, "type") or message.__class__.__name__),
        }
        if additional_kwargs:
            event_metadata["additional_kwargs"] = additional_kwargs
        if response_metadata:
            event_metadata["response_metadata"] = response_metadata

        tool_call_id = _get(message, "tool_call_id")
        if tool_call_id is not None:
            event_metadata["tool_call_id"] = tool_call_id

        events.append(
            TraceEvent(
                id=event_id,
                type=event_type,
                output=content,
                dependencies=dependencies,
                metadata=event_metadata,
            )
        )
        previous_id = event_id

    trace_metadata = {"adapter": "langgraph"}
    if metadata:
        trace_metadata.update(metadata)
    return Trace(tuple(events), trace_metadata)
