"""
Async unit tests for memory/short_term.py (MySQLSession).

MySQL is mocked at the get_connection level.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from memory.short_term import MySQLSession


def _conn_ctx(cursor):
    """Return a mock context manager that yields a connection with the given cursor."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# get_items
# ---------------------------------------------------------------------------

async def test_get_items_empty_session():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        items = await session.get_items()

    assert items == []


async def test_get_items_deserialises_json():
    item1 = {"role": "user", "content": "Hello"}
    item2 = {"role": "assistant", "content": "Hi there"}
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"content": json.dumps(item1)},
        {"content": json.dumps(item2)},
    ]
    ctx = _conn_ctx(cursor)

    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        items = await session.get_items()

    assert items == [item1, item2]


async def test_get_items_query_uses_session_id():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    session = MySQLSession("sess_abc", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.get_items()

    sql, params = cursor.execute.call_args[0]
    assert "session_id" in sql
    assert "sess_abc" in params


async def test_get_items_applies_max_history_limit():
    """MAX_HISTORY_ITEMS (20 in test env) must be in the SQL params."""
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.get_items()

    _, params = cursor.execute.call_args[0]
    assert 20 in params  # MAX_HISTORY_ITEMS=20 from test env


async def test_get_items_closes_cursor():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.get_items()

    cursor.close.assert_called_once()


# ---------------------------------------------------------------------------
# add_items
# ---------------------------------------------------------------------------

async def test_add_items_empty_list_is_noop():
    cursor = MagicMock()
    ctx = _conn_ctx(cursor)

    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.add_items([])

    cursor.executemany.assert_not_called()


async def test_add_items_inserts_all_records():
    cursor = MagicMock()
    ctx = _conn_ctx(cursor)

    items = [
        {"role": "user", "content": "Q1"},
        {"role": "assistant", "content": "A1"},
    ]
    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.add_items(items)

    cursor.executemany.assert_called_once()
    _, records = cursor.executemany.call_args[0]
    assert len(records) == 2


async def test_add_items_serialises_to_json():
    cursor = MagicMock()
    ctx = _conn_ctx(cursor)

    item = {"role": "user", "content": "Hello", "extra": [1, 2]}
    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.add_items([item])

    _, records = cursor.executemany.call_args[0]
    stored_json = records[0][3]  # 4th element is the content blob
    assert json.loads(stored_json) == item


async def test_add_items_extracts_role_from_item():
    cursor = MagicMock()
    ctx = _conn_ctx(cursor)

    item = {"role": "assistant", "content": "Hi"}
    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.add_items([item])

    _, records = cursor.executemany.call_args[0]
    role_col = records[0][2]
    assert role_col == "assistant"


async def test_add_items_falls_back_to_type_when_no_role():
    cursor = MagicMock()
    ctx = _conn_ctx(cursor)

    item = {"type": "tool_result", "content": "..."}
    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.add_items([item])

    _, records = cursor.executemany.call_args[0]
    assert records[0][2] == "tool_result"


async def test_add_items_truncates_role_to_32_chars():
    cursor = MagicMock()
    ctx = _conn_ctx(cursor)

    item = {"role": "x" * 100, "content": "c"}
    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.add_items([item])

    _, records = cursor.executemany.call_args[0]
    assert len(records[0][2]) == 32


# ---------------------------------------------------------------------------
# pop_item
# ---------------------------------------------------------------------------

async def test_pop_item_returns_none_when_empty():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    ctx = _conn_ctx(cursor)

    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        result = await session.pop_item()

    assert result is None


async def test_pop_item_returns_and_deletes_last_item():
    item = {"role": "user", "content": "Last message"}
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": 42, "content": json.dumps(item)}
    ctx = _conn_ctx(cursor)

    session = MySQLSession("s1", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        result = await session.pop_item()

    assert result == item
    # Verify DELETE was called with the returned id
    delete_call = cursor.execute.call_args_list[-1]
    assert "DELETE" in delete_call[0][0]
    assert 42 in delete_call[0][1]


# ---------------------------------------------------------------------------
# clear_session
# ---------------------------------------------------------------------------

async def test_clear_session_deletes_all_for_session():
    cursor = MagicMock()
    ctx = _conn_ctx(cursor)

    session = MySQLSession("sess_xyz", "u1")
    with patch("memory.short_term.get_connection", return_value=ctx):
        await session.clear_session()

    sql, params = cursor.execute.call_args[0]
    assert "DELETE" in sql
    assert "conversations" in sql
    assert "sess_xyz" in params
