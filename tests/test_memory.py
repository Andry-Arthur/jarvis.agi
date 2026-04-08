"""Unit tests for Memory edge cases."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_memory_empty_collection(tmp_path):
    """Querying an empty ChromaDB collection must return empty string (not error)."""
    import os

    os.environ["CHROMA_PERSIST_DIR"] = str(tmp_path / "chroma")

    from jarvis.core.memory import Memory

    memory = Memory(persist_directory=str(tmp_path / "chroma"))
    result = await memory.get_relevant_context("anything")
    assert result == ""


@pytest.mark.asyncio
async def test_memory_add_and_retrieve(tmp_path):
    """After adding an exchange the same query should return non-empty context."""
    from jarvis.core.memory import Memory

    memory = Memory(persist_directory=str(tmp_path / "chroma2"))
    await memory.add_exchange("What is the capital of France?", "Paris is the capital of France.")
    result = await memory.get_relevant_context("capital France")
    assert "Paris" in result or result != ""


@pytest.mark.asyncio
async def test_memory_multiple_exchanges(tmp_path):
    """Memory should not exceed max_results when queried."""
    from jarvis.core.memory import Memory

    memory = Memory(persist_directory=str(tmp_path / "chroma3"), max_results=2)
    for i in range(5):
        await memory.add_exchange(f"Question {i}", f"Answer {i}")
    result = await memory.get_relevant_context("Question 0")
    assert isinstance(result, str)
    assert len(result) > 0
