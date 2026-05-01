"""
Async unit tests for tools/retrieval.py (search_knowledge_base).

MySQL is mocked at get_connection; agents SDK is stubbed in conftest.
"""
import pytest
from unittest.mock import MagicMock, patch


def _conn_ctx(cursor):
    conn = MagicMock()
    conn.cursor.return_value = cursor
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# No results — verifier path
# ---------------------------------------------------------------------------

async def test_no_rows_returns_no_results_tag(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        result = await search_knowledge_base(mock_wrapper, "unknown topic")

    assert "[NO RESULTS]" in result or "[LOW QUALITY RESULT]" in result


# ---------------------------------------------------------------------------
# Successful results
# ---------------------------------------------------------------------------

async def test_returns_formatted_article_titles(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {
            "title": "Return Policy",
            "content": "We accept returns within 30 days of purchase for unused items.",
            "category": "returns",
        }
    ]
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        result = await search_knowledge_base(mock_wrapper, "return policy")

    assert "Return Policy" in result
    assert "returns" in result


async def test_returns_content_excerpt(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    long_content = "A" * 700
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"title": "Article", "content": long_content, "category": "general"}
    ]
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        result = await search_knowledge_base(mock_wrapper, "something")

    # Excerpt is capped at 600 chars from content
    assert "A" * 600 in result
    assert "A" * 700 not in result


async def test_multiple_articles_all_numbered(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"title": "Article One", "content": "Content one.", "category": "cat"},
        {"title": "Article Two", "content": "Content two.", "category": "cat"},
    ]
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        result = await search_knowledge_base(mock_wrapper, "articles")

    assert "1." in result
    assert "2." in result
    assert "Article One" in result
    assert "Article Two" in result


async def test_result_quality_ok_for_valid_rows(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"title": "Shipping", "content": "Standard delivery in 3-5 days.", "category": "shipping"}
    ]
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        result = await search_knowledge_base(mock_wrapper, "shipping")

    assert "[NO RESULTS]" not in result
    assert "[LOW QUALITY RESULT]" not in result


# ---------------------------------------------------------------------------
# Query routing — FULLTEXT vs LIKE
# ---------------------------------------------------------------------------

async def test_long_query_uses_fulltext(mock_wrapper):
    """Words ≥ 3 chars trigger the FULLTEXT MATCH...AGAINST path."""
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        await search_knowledge_base(mock_wrapper, "return refund policy")

    sql = cursor.execute.call_args[0][0]
    assert "MATCH" in sql and "AGAINST" in sql


async def test_very_short_query_uses_like_fallback(mock_wrapper):
    """Words shorter than 3 chars trigger the LIKE fallback."""
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        # All words are < 3 chars — the words list is empty → LIKE path
        await search_knowledge_base(mock_wrapper, "a b")

    sql = cursor.execute.call_args[0][0]
    assert "LIKE" in sql


async def test_fulltext_params_include_boolean_query(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        await search_knowledge_base(mock_wrapper, "refund policy")

    params = cursor.execute.call_args[0][1]
    # Boolean query should contain '+' prefixed words
    assert any("+" in str(p) for p in params)


async def test_max_results_passed_to_query(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        await search_knowledge_base(mock_wrapper, "shipping", max_results=2)

    params = cursor.execute.call_args[0][1]
    assert 2 in params


async def test_cursor_closed_after_query(mock_wrapper):
    from tools.retrieval import search_knowledge_base

    cursor = MagicMock()
    cursor.fetchall.return_value = []
    ctx = _conn_ctx(cursor)

    with patch("tools.retrieval.get_connection", return_value=ctx):
        await search_knowledge_base(mock_wrapper, "anything")

    cursor.close.assert_called_once()
