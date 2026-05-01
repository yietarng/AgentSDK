"""
Async unit tests for agent/react_agent.py.

Runner.run, recall_memories, and MySQLSession are all mocked so no real
external calls are made.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from memory.long_term import MemoryFact


def _make_run_result(text="Agent response."):
    r = MagicMock()
    r.final_output = text
    return r


# ---------------------------------------------------------------------------
# run_turn — basic contract
# ---------------------------------------------------------------------------

async def test_run_turn_returns_string():
    from agent.react_agent import run_turn

    mock_result = _make_run_result("Hello!")
    with (
        patch("agent.react_agent.recall_memories", return_value=[]),
        patch("agent.react_agent.MySQLSession"),
        patch("agent.react_agent.Runner.run", new=AsyncMock(return_value=mock_result)),
    ):
        result = await run_turn("Hi", "u1", "s1")

    assert isinstance(result, str)
    assert result == "Hello!"


async def test_run_turn_returns_final_output_as_string():
    from agent.react_agent import run_turn

    mock_result = _make_run_result(42)  # non-string final_output
    with (
        patch("agent.react_agent.recall_memories", return_value=[]),
        patch("agent.react_agent.MySQLSession"),
        patch("agent.react_agent.Runner.run", new=AsyncMock(return_value=mock_result)),
    ):
        result = await run_turn("q", "u1", "s1")

    assert result == "42"  # must be str()


# ---------------------------------------------------------------------------
# run_turn — memory loading
# ---------------------------------------------------------------------------

async def test_run_turn_calls_recall_memories_with_user_id():
    from agent.react_agent import run_turn

    mock_result = _make_run_result()
    with (
        patch("agent.react_agent.recall_memories", return_value=[]) as mock_recall,
        patch("agent.react_agent.MySQLSession"),
        patch("agent.react_agent.Runner.run", new=AsyncMock(return_value=mock_result)),
    ):
        await run_turn("msg", "alice", "s1")

    mock_recall.assert_called_once_with("alice")


async def test_run_turn_passes_memories_to_context():
    from agent.react_agent import run_turn
    from agent.context import AppContext

    facts = [MemoryFact("name", "Alice")]
    captured_context = {}

    async def capture_run(agent, input, context, session, run_config, max_turns):
        captured_context["ctx"] = context
        return _make_run_result()

    with (
        patch("agent.react_agent.recall_memories", return_value=facts),
        patch("agent.react_agent.MySQLSession"),
        patch("agent.react_agent.Runner.run", new=capture_run),
    ):
        await run_turn("msg", "alice", "s1")

    ctx = captured_context["ctx"]
    assert isinstance(ctx, AppContext)
    assert ctx.memories == facts
    assert ctx.user_id == "alice"
    assert ctx.session_id == "s1"


# ---------------------------------------------------------------------------
# run_turn — session management
# ---------------------------------------------------------------------------

async def test_run_turn_creates_mysql_session_with_correct_ids():
    from agent.react_agent import run_turn

    mock_result = _make_run_result()
    with (
        patch("agent.react_agent.recall_memories", return_value=[]),
        patch("agent.react_agent.MySQLSession") as mock_session_cls,
        patch("agent.react_agent.Runner.run", new=AsyncMock(return_value=mock_result)),
    ):
        await run_turn("msg", "u1", "sess_999")

    mock_session_cls.assert_called_once_with(session_id="sess_999", user_id="u1")


# ---------------------------------------------------------------------------
# run_turn — Runner.run call contract
# ---------------------------------------------------------------------------

async def test_run_turn_passes_max_turns_to_runner():
    from agent.react_agent import run_turn

    captured = {}

    async def capture_run(agent, input, context, session, run_config, max_turns):
        captured["max_turns"] = max_turns
        return _make_run_result()

    with (
        patch("agent.react_agent.recall_memories", return_value=[]),
        patch("agent.react_agent.MySQLSession"),
        patch("agent.react_agent.Runner.run", new=capture_run),
    ):
        await run_turn("msg", "u", "s")

    assert captured["max_turns"] == 10  # AGENT_MAX_TURNS=10 from test env


async def test_run_turn_passes_user_message_as_input():
    from agent.react_agent import run_turn

    captured = {}

    async def capture_run(agent, input, context, session, run_config, max_turns):
        captured["input"] = input
        return _make_run_result()

    with (
        patch("agent.react_agent.recall_memories", return_value=[]),
        patch("agent.react_agent.MySQLSession"),
        patch("agent.react_agent.Runner.run", new=capture_run),
    ):
        await run_turn("What is your return policy?", "u", "s")

    assert captured["input"] == "What is your return policy?"


# ---------------------------------------------------------------------------
# _build_instructions — dynamic prompt
# ---------------------------------------------------------------------------

def test_build_instructions_includes_memory_facts():
    from agent.react_agent import _build_instructions

    facts = [MemoryFact("account_tier", "premium")]
    wrapper = MagicMock()
    wrapper.context.memories = facts
    agent = MagicMock()

    prompt = _build_instructions(wrapper, agent)

    assert "account_tier" in prompt
    assert "premium" in prompt


def test_build_instructions_no_memory_shows_none_on_file():
    from agent.react_agent import _build_instructions

    wrapper = MagicMock()
    wrapper.context.memories = []
    agent = MagicMock()

    prompt = _build_instructions(wrapper, agent)

    assert "None on file" in prompt


def test_build_instructions_returns_string():
    from agent.react_agent import _build_instructions

    wrapper = MagicMock()
    wrapper.context.memories = []
    agent = MagicMock()

    result = _build_instructions(wrapper, agent)

    assert isinstance(result, str)


def test_build_instructions_contains_react_keywords():
    from agent.react_agent import _build_instructions

    wrapper = MagicMock()
    wrapper.context.memories = []
    agent = MagicMock()

    prompt = _build_instructions(wrapper, agent)

    assert "THINK" in prompt
    assert "OBSERVE" in prompt
    assert "RESPOND" in prompt
