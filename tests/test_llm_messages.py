"""Unit tests for LLM message format conversion and ToolCall serialization."""

from __future__ import annotations

import json

import pytest

from jarvis.llm.base import LLMResponse, StreamChunk, ToolCall


def test_tool_call_to_openai_dict():
    tc = ToolCall(id="abc", name="my_tool", arguments={"key": "value"})
    d = tc.to_openai_dict()
    assert d["id"] == "abc"
    assert d["type"] == "function"
    assert d["function"]["name"] == "my_tool"
    # Arguments must be JSON-serialized string for OpenAI format
    assert isinstance(d["function"]["arguments"], str)
    assert json.loads(d["function"]["arguments"]) == {"key": "value"}


def test_llm_response_defaults():
    resp = LLMResponse(content="hello")
    assert resp.tool_calls == []
    assert resp.model == ""


def test_stream_chunk_defaults():
    chunk = StreamChunk()
    assert chunk.delta == ""
    assert chunk.tool_calls == []
    assert chunk.done is False


def test_anthropic_message_conversion():
    from jarvis.llm.anthropic_llm import AnthropicLLM

    llm = AnthropicLLM.__new__(AnthropicLLM)

    messages = [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": "Sure",
            "tool_calls": [
                {
                    "id": "t1",
                    "type": "function",
                    "function": {"name": "echo", "arguments": '{"text": "hi"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "t1", "content": "echo: hi"},
        {"role": "user", "content": "Thanks"},
    ]
    converted = llm._to_anthropic_messages(messages)

    roles = [m["role"] for m in converted]
    assert roles[0] == "user"
    assert roles[1] == "assistant"
    # Tool results fold into a user message
    assert roles[2] == "user"
    assert roles[3] == "user"

    # Tool use block in assistant turn
    assistant_content = converted[1]["content"]
    tool_use_blocks = [b for b in assistant_content if b.get("type") == "tool_use"]
    assert len(tool_use_blocks) == 1
    assert tool_use_blocks[0]["name"] == "echo"
    assert tool_use_blocks[0]["input"] == {"text": "hi"}


def test_anthropic_tool_conversion():
    from jarvis.llm.anthropic_llm import AnthropicLLM

    llm = AnthropicLLM.__new__(AnthropicLLM)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]
    converted = llm._to_anthropic_tools(tools)
    assert converted[0]["name"] == "search"
    assert "input_schema" in converted[0]


def test_ollama_prepare_messages():
    from jarvis.llm.ollama_llm import OllamaLLM

    llm = OllamaLLM.__new__(OllamaLLM)
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "x",
                    "function": {"name": "echo", "arguments": '{"text": "hello"}'},
                }
            ],
        }
    ]
    result = llm._prepare_messages(messages)
    args = result[0]["tool_calls"][0]["function"]["arguments"]
    assert isinstance(args, dict)
    assert args == {"text": "hello"}


def test_ollama_prepare_messages_already_dict():
    from jarvis.llm.ollama_llm import OllamaLLM

    llm = OllamaLLM.__new__(OllamaLLM)
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "x",
                    "function": {"name": "echo", "arguments": {"text": "hello"}},
                }
            ],
        }
    ]
    result = llm._prepare_messages(messages)
    args = result[0]["tool_calls"][0]["function"]["arguments"]
    assert isinstance(args, dict)
