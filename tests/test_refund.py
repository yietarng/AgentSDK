"""
Unit tests for tools/refund.py (submit_refund_request, check_refund_status).

MySQL is mocked via get_connection; no real DB or network calls are made.
"""
import pytest
from unittest.mock import MagicMock, patch
from tools.refund import submit_refund_request, check_refund_status


def _conn_ctx(cursor):
    """Return a mock context manager that yields a connection with the given cursor."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# submit_refund_request
# ---------------------------------------------------------------------------

async def test_submit_returns_confirmation_string(mock_wrapper):
    cursor = MagicMock()
    cursor.lastrowid = 101
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await submit_refund_request(mock_wrapper, "ORD-001", "Item arrived damaged")

    assert isinstance(result, str)
    assert "submitted successfully" in result.lower()


async def test_submit_includes_request_id(mock_wrapper):
    cursor = MagicMock()
    cursor.lastrowid = 42
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await submit_refund_request(mock_wrapper, "ORD-002", "Wrong item sent")

    assert "42" in result


async def test_submit_includes_order_id(mock_wrapper):
    cursor = MagicMock()
    cursor.lastrowid = 1
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await submit_refund_request(mock_wrapper, "ORD-XYZ", "Changed my mind")

    assert "ORD-XYZ" in result


async def test_submit_includes_pending_status(mock_wrapper):
    cursor = MagicMock()
    cursor.lastrowid = 1
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await submit_refund_request(mock_wrapper, "ORD-003", "Not as described")

    assert "pending" in result.lower()


async def test_submit_inserts_with_correct_user_id(mock_wrapper):
    cursor = MagicMock()
    cursor.lastrowid = 5
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        await submit_refund_request(mock_wrapper, "ORD-004", "Defective")

    _, args = cursor.execute.call_args[0][0], cursor.execute.call_args[0][1]
    assert "u_test" in args  # user_id from mock_wrapper fixture


async def test_submit_passes_order_id_and_reason_to_db(mock_wrapper):
    cursor = MagicMock()
    cursor.lastrowid = 7
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        await submit_refund_request(mock_wrapper, "ORD-005", "Late delivery")

    _, params = cursor.execute.call_args[0][0], cursor.execute.call_args[0][1]
    assert "ORD-005" in params
    assert "Late delivery" in params


async def test_submit_closes_cursor(mock_wrapper):
    cursor = MagicMock()
    cursor.lastrowid = 1
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        await submit_refund_request(mock_wrapper, "ORD-006", "reason")

    cursor.close.assert_called_once()


# ---------------------------------------------------------------------------
# check_refund_status
# ---------------------------------------------------------------------------

async def test_check_returns_not_found_when_no_row(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await check_refund_status(mock_wrapper, "ORD-999")

    assert "No refund request found" in result
    assert "ORD-999" in result


async def test_check_returns_status_when_row_exists(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": 10,
        "order_id": "ORD-010",
        "reason": "Damaged",
        "status": "approved",
        "amount": 29.99,
        "requested_at": "2024-01-15 10:00:00",
        "updated_at": "2024-01-16 09:00:00",
    }
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await check_refund_status(mock_wrapper, "ORD-010")

    assert "approved" in result
    assert "ORD-010" in result


async def test_check_formats_amount_as_dollars(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": 11,
        "order_id": "ORD-011",
        "reason": "Wrong size",
        "status": "processed",
        "amount": 49.95,
        "requested_at": "2024-02-01 08:00:00",
        "updated_at": "2024-02-03 12:00:00",
    }
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await check_refund_status(mock_wrapper, "ORD-011")

    assert "$49.95" in result


async def test_check_shows_pending_review_when_amount_is_none(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": 12,
        "order_id": "ORD-012",
        "reason": "Not delivered",
        "status": "pending",
        "amount": None,
        "requested_at": "2024-03-01 07:00:00",
        "updated_at": "2024-03-01 07:00:00",
    }
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await check_refund_status(mock_wrapper, "ORD-012")

    assert "pending review" in result


async def test_check_queries_with_correct_user_id(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        await check_refund_status(mock_wrapper, "ORD-013")

    _, params = cursor.execute.call_args[0][0], cursor.execute.call_args[0][1]
    assert "u_test" in params


async def test_check_queries_with_correct_order_id(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        await check_refund_status(mock_wrapper, "ORD-014")

    _, params = cursor.execute.call_args[0][0], cursor.execute.call_args[0][1]
    assert "ORD-014" in params


async def test_check_closes_cursor(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        await check_refund_status(mock_wrapper, "ORD-015")

    cursor.close.assert_called_once()


async def test_check_includes_reason_in_output(mock_wrapper):
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": 20,
        "order_id": "ORD-020",
        "reason": "Product was counterfeit",
        "status": "approved",
        "amount": 99.00,
        "requested_at": "2024-04-01 10:00:00",
        "updated_at": "2024-04-02 10:00:00",
    }
    ctx = _conn_ctx(cursor)

    with patch("tools.refund.get_connection", return_value=ctx):
        result = await check_refund_status(mock_wrapper, "ORD-020")

    assert "Product was counterfeit" in result
