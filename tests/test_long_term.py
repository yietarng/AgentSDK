"""
Unit tests for memory/long_term.py.

MySQL is mocked at the get_connection context-manager level.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from memory.long_term import recall_memories, save_memory, MemoryFact


def _make_conn_mock(cursor):
    """Return (conn, ctx) where ctx is a mock context manager yielding conn."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return conn, ctx


# ---------------------------------------------------------------------------
# recall_memories
# ---------------------------------------------------------------------------

def test_recall_returns_empty_list_when_no_rows():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        result = recall_memories("user_1")

    assert result == []


def test_recall_returns_memory_facts():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"memory_key": "name", "memory_value": "Alice"},
        {"memory_key": "account_tier", "memory_value": "premium"},
    ]
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        result = recall_memories("user_1")

    assert len(result) == 2
    assert result[0] == MemoryFact("name", "Alice")
    assert result[1] == MemoryFact("account_tier", "premium")


def test_recall_executes_query_with_correct_user_id():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        recall_memories("alice_42")

    cursor.execute.assert_called_once()
    args = cursor.execute.call_args[0]
    assert "user_id" in args[0]      # SQL contains user_id
    assert args[1] == ("alice_42",)  # Param is the user_id


def test_recall_closes_cursor():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        recall_memories("user_x")

    cursor.close.assert_called_once()


def test_recall_returns_correct_types():
    cursor = MagicMock()
    cursor.fetchall.return_value = [{"memory_key": "k", "memory_value": "v"}]
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        result = recall_memories("u")

    assert isinstance(result[0], MemoryFact)
    assert result[0].memory_key == "k"
    assert result[0].memory_value == "v"


# ---------------------------------------------------------------------------
# save_memory
# ---------------------------------------------------------------------------

def test_save_executes_upsert_sql():
    cursor = MagicMock()
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        save_memory("user_1", "name", "Bob")

    cursor.execute.assert_called_once()
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO user_memory" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params == ("user_1", "name", "Bob")


def test_save_closes_cursor():
    cursor = MagicMock()
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        save_memory("user_1", "k", "v")

    cursor.close.assert_called_once()


def test_save_passes_all_three_fields():
    cursor = MagicMock()
    _, ctx = _make_conn_mock(cursor)

    with patch("memory.long_term.get_connection", return_value=ctx):
        save_memory("uid", "preferred_contact", "email")

    _, params = cursor.execute.call_args[0]
    assert "uid" in params
    assert "preferred_contact" in params
    assert "email" in params


# ---------------------------------------------------------------------------
# MemoryFact dataclass
# ---------------------------------------------------------------------------

def test_memory_fact_equality():
    a = MemoryFact("key", "value")
    b = MemoryFact("key", "value")
    assert a == b


def test_memory_fact_inequality():
    assert MemoryFact("k", "v1") != MemoryFact("k", "v2")
