"""
Async unit tests for tools/web_search.py.

The Tavily client is mocked via the module-level _tavily_client singleton.
"""
import pytest
from unittest.mock import patch, AsyncMock


def _make_results(*titles):
    return {
        "results": [
            {"title": t, "url": f"https://example.com/{i}", "content": f"Content for {t}."}
            for i, t in enumerate(titles)
        ]
    }


# ---------------------------------------------------------------------------
# No results — verifier path
# ---------------------------------------------------------------------------

async def test_empty_results_returns_no_results_tag(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": []}

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "something obscure")

    assert "[NO RESULTS]" in result or "[LOW QUALITY RESULT]" in result


async def test_missing_results_key_returns_no_results_tag(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = {}  # no 'results' key

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "query")

    assert "[NO RESULTS]" in result or "[LOW QUALITY RESULT]" in result


# ---------------------------------------------------------------------------
# Successful results
# ---------------------------------------------------------------------------

async def test_results_include_titles(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = _make_results("OpenAI Blog Post")

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "openai news")

    assert "OpenAI Blog Post" in result


async def test_results_include_url(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = {
        "results": [{"title": "T", "url": "https://example.com/page", "content": "Some content here."}]
    }

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "query")

    assert "https://example.com/page" in result


async def test_multiple_results_numbered(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = _make_results("Result A", "Result B", "Result C")

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "topic")

    assert "1." in result
    assert "2." in result
    assert "3." in result


async def test_content_snippet_is_capped_at_400_chars(mock_wrapper):
    from tools.web_search import web_search

    long_content = "X" * 600
    mock_client = AsyncMock()
    mock_client.search.return_value = {
        "results": [{"title": "T", "url": "u", "content": long_content}]
    }

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "q")

    assert "X" * 400 in result
    assert "X" * 600 not in result


async def test_valid_results_no_quality_tags(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = _make_results("Normal Article About Shipping Policy")

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "shipping")

    assert "[NO RESULTS]" not in result
    assert "[LOW QUALITY RESULT]" not in result


# ---------------------------------------------------------------------------
# API call parameters
# ---------------------------------------------------------------------------

async def test_search_called_with_correct_query(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = _make_results("Article")

    with patch("tools.web_search._tavily_client", mock_client):
        await web_search(mock_wrapper, "shipping times")

    mock_client.search.assert_called_once()
    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["query"] == "shipping times"


async def test_default_max_results_is_five(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": []}

    with patch("tools.web_search._tavily_client", mock_client):
        await web_search(mock_wrapper, "q")

    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["max_results"] == 5


async def test_custom_max_results_respected(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": []}

    with patch("tools.web_search._tavily_client", mock_client):
        await web_search(mock_wrapper, "q", max_results=3)

    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["max_results"] == 3


async def test_search_depth_is_basic(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": []}

    with patch("tools.web_search._tavily_client", mock_client):
        await web_search(mock_wrapper, "q")

    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["search_depth"] == "basic"


# ---------------------------------------------------------------------------
# Missing fields in results (defensive handling)
# ---------------------------------------------------------------------------

async def test_missing_title_falls_back_to_no_title(mock_wrapper):
    from tools.web_search import web_search

    mock_client = AsyncMock()
    mock_client.search.return_value = {
        "results": [{"url": "https://x.com", "content": "Some content about the topic."}]
    }

    with patch("tools.web_search._tavily_client", mock_client):
        result = await web_search(mock_wrapper, "q")

    assert "No title" in result
