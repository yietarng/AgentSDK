"""
Async unit tests for tools/memory_tools.py.

save_memory and recall_memories are mocked at the module level so no
real DB connections are made.
"""
import pytest
from unittest.mock import patch
from memory.long_term import MemoryFact


# ---------------------------------------------------------------------------
# save_user_memory
# ---------------------------------------------------------------------------

async def test_save_calls_save_memory_with_user_id(mock_wrapper):
    from tools.memory_tools import save_user_memory

    with patch("tools.memory_tools.save_memory") as mock_save:
        await save_user_memory(mock_wrapper, "account_tier", "premium")

    mock_save.assert_called_once_with("u_test", "account_tier", "premium")


async def test_save_returns_confirmation_message(mock_wrapper):
    from tools.memory_tools import save_user_memory

    with patch("tools.memory_tools.save_memory"):
        result = await save_user_memory(mock_wrapper, "name", "Alice")

    assert "name" in result
    assert "Alice" in result


async def test_save_includes_user_id_in_confirmation(mock_wrapper):
    from tools.memory_tools import save_user_memory

    with patch("tools.memory_tools.save_memory"):
        result = await save_user_memory(mock_wrapper, "k", "v")

    assert "u_test" in result  # user_id from fixture


async def test_save_returns_string(mock_wrapper):
    from tools.memory_tools import save_user_memory

    with patch("tools.memory_tools.save_memory"):
        result = await save_user_memory(mock_wrapper, "k", "v")

    assert isinstance(result, str)


async def test_save_uses_wrapper_context_user_id(mock_wrapper):
    from tools.memory_tools import save_user_memory
    from agent.context import AppContext

    mock_wrapper.context = AppContext(user_id="specific_user", session_id="s", memories=[])

    with patch("tools.memory_tools.save_memory") as mock_save:
        await save_user_memory(mock_wrapper, "tier", "plus")

    assert mock_save.call_args[0][0] == "specific_user"


# ---------------------------------------------------------------------------
# recall_user_memory
# ---------------------------------------------------------------------------

async def test_recall_returns_no_facts_message_when_empty(mock_wrapper):
    from tools.memory_tools import recall_user_memory

    with patch("tools.memory_tools.recall_memories", return_value=[]):
        result = await recall_user_memory(mock_wrapper)

    assert "No memory facts" in result
    assert "u_test" in result


async def test_recall_formats_facts_correctly(mock_wrapper):
    from tools.memory_tools import recall_user_memory

    facts = [
        MemoryFact("name", "Bob"),
        MemoryFact("account_tier", "standard"),
    ]
    with patch("tools.memory_tools.recall_memories", return_value=facts):
        result = await recall_user_memory(mock_wrapper)

    assert "name" in result and "Bob" in result
    assert "account_tier" in result and "standard" in result


async def test_recall_uses_wrapper_user_id(mock_wrapper):
    from tools.memory_tools import recall_user_memory
    from agent.context import AppContext

    mock_wrapper.context = AppContext(user_id="charlie", session_id="s", memories=[])

    with patch("tools.memory_tools.recall_memories") as mock_recall:
        mock_recall.return_value = []
        await recall_user_memory(mock_wrapper)

    mock_recall.assert_called_once_with("charlie")


async def test_recall_includes_user_id_in_output(mock_wrapper):
    from tools.memory_tools import recall_user_memory

    facts = [MemoryFact("k", "v")]
    with patch("tools.memory_tools.recall_memories", return_value=facts):
        result = await recall_user_memory(mock_wrapper)

    assert "u_test" in result


async def test_recall_uses_bullet_format(mock_wrapper):
    from tools.memory_tools import recall_user_memory

    facts = [MemoryFact("preferred_contact", "email")]
    with patch("tools.memory_tools.recall_memories", return_value=facts):
        result = await recall_user_memory(mock_wrapper)

    assert "- preferred_contact: email" in result


async def test_recall_returns_string(mock_wrapper):
    from tools.memory_tools import recall_user_memory

    with patch("tools.memory_tools.recall_memories", return_value=[]):
        result = await recall_user_memory(mock_wrapper)

    assert isinstance(result, str)
