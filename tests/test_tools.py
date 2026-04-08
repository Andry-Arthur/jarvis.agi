"""Unit tests for Tool classes and ToolRegistry."""

from __future__ import annotations

import pytest

from jarvis.core.tools import Tool, ToolRegistry


class EchoTool(Tool):
    name = "echo"
    description = "Echoes its input."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to echo"},
        },
        "required": ["text"],
    }

    async def execute(self, text: str) -> str:
        return f"echo: {text}"


class FailTool(Tool):
    name = "fail"
    description = "Always raises an error."
    parameters = {"type": "object", "properties": {}}

    async def execute(self) -> str:
        raise RuntimeError("intentional failure")


class AddTool(Tool):
    name = "add"
    description = "Adds two numbers."
    parameters = {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    }

    async def execute(self, a: float, b: float) -> str:
        return str(a + b)


# -----------------------------------------------------------------------


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(EchoTool())
    reg.register(AddTool())
    return reg


@pytest.mark.asyncio
async def test_echo_tool():
    tool = EchoTool()
    result = await tool.execute(text="hello")
    assert result == "echo: hello"


@pytest.mark.asyncio
async def test_add_tool():
    tool = AddTool()
    result = await tool.execute(a=2, b=3)
    assert result == "5.0"


@pytest.mark.asyncio
async def test_registry_execute(registry):
    result = await registry.execute("echo", {"text": "world"})
    assert result == "echo: world"


@pytest.mark.asyncio
async def test_registry_unknown_tool(registry):
    result = await registry.execute("nonexistent", {})
    assert "Unknown tool" in result


@pytest.mark.asyncio
async def test_registry_failing_tool():
    reg = ToolRegistry()
    reg.register(FailTool())
    result = await reg.execute("fail", {})
    assert "error" in result.lower() or "intentional" in result.lower()


def test_registry_schema(registry):
    schemas = registry.get_all_schemas()
    names = {s["function"]["name"] for s in schemas}
    assert "echo" in names
    assert "add" in names


def test_registry_list_tools(registry):
    tools = registry.list_tools()
    assert "echo" in tools
    assert "add" in tools


def test_registry_register_many():
    reg = ToolRegistry()
    reg.register_many([EchoTool(), AddTool()])
    assert len(reg.list_tools()) == 2
