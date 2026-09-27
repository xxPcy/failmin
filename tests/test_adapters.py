from failmin.adapters.langgraph import from_messages
from failmin.adapters.openai import from_response_items


def test_langgraph_message_adapter():
    trace = from_messages(
        [
            {"id": "u1", "type": "human", "content": "hello"},
            {"id": "a1", "type": "ai", "content": "hi"},
            {"id": "t1", "type": "tool", "content": "42", "tool_call_id": "call_1"},
        ]
    )

    assert [event.type for event in trace.events] == [
        "user_message",
        "assistant_message",
        "tool_result",
    ]
    assert trace.events[1].dependencies == ("u1",)
    assert trace.events[2].dependencies == ("a1",)
    assert trace.metadata["adapter"] == "langgraph"


def test_openai_response_adapter_preserves_tool_dependency():
    trace = from_response_items(
        [
            {
                "id": "m1",
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "weather?"}],
            },
            {
                "id": "fc1",
                "type": "function_call",
                "call_id": "call_1",
                "name": "weather",
                "arguments": "{}",
            },
            {
                "id": "fo1",
                "type": "function_call_output",
                "call_id": "call_1",
                "output": "sunny",
            },
        ]
    )

    assert [event.type for event in trace.events] == [
        "user_message",
        "tool_call",
        "tool_result",
    ]
    assert trace.events[2].dependencies == ("fc1",)
    assert trace.metadata["adapter"] == "openai"
