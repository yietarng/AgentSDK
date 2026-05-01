"""
Unit tests for tools/verifier.py.

No external dependencies — fully testable without mocks.
"""
import pytest
from tools.verifier import verify_tool_output, OutputQuality


# ---------------------------------------------------------------------------
# Empty / whitespace inputs
# ---------------------------------------------------------------------------

def test_empty_string_returns_empty_quality():
    result = verify_tool_output("")
    assert result.quality == OutputQuality.EMPTY


def test_whitespace_only_returns_empty_quality():
    result = verify_tool_output("   \n\t  ")
    assert result.quality == OutputQuality.EMPTY


def test_empty_content_includes_no_results_tag():
    result = verify_tool_output("", query="refund policy")
    assert "[NO RESULTS]" in result.content
    assert "refund policy" in result.content


def test_empty_without_query_still_returns_tag():
    result = verify_tool_output("")
    assert "[NO RESULTS]" in result.content


# ---------------------------------------------------------------------------
# Error-prefix detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "error connecting to database",
    "Error: something went wrong",
    "no results found",
    "No results for that query",
    "No knowledge base articles found for 'xyz'.",
    "No web search results found for 'abc'.",
    "no memory facts",
    "No memory found",
    "0 results returned",
    "not found in the system",
    "Not found",
])
def test_error_prefix_returns_low_quality(text):
    result = verify_tool_output(text)
    assert result.quality == OutputQuality.EMPTY
    assert "[LOW QUALITY RESULT]" in result.content


def test_error_prefix_preserves_original_text():
    raw = "No results for that query"
    result = verify_tool_output(raw)
    assert raw in result.content


# ---------------------------------------------------------------------------
# Valid / OK results
# ---------------------------------------------------------------------------

def test_normal_result_returns_ok_quality():
    raw = "1. [Return Policy] You can return items within 30 days of delivery."
    result = verify_tool_output(raw)
    assert result.quality == OutputQuality.OK


def test_ok_result_content_is_unchanged():
    raw = "Your order #12345 has been dispatched and will arrive in 2 business days."
    result = verify_tool_output(raw, query="order status")
    assert result.content == raw


def test_short_but_valid_result_is_ok():
    # Previously this would fail with len < 50 check; confirmed fixed
    raw = "Order delivered on April 30th."
    result = verify_tool_output(raw)
    assert result.quality == OutputQuality.OK


def test_multiline_result_is_ok():
    raw = (
        "Knowledge base results for: 'shipping'\n\n"
        "1. [Shipping Policy] (category: shipping)\n"
        "   Standard delivery takes 3-5 business days..."
    )
    result = verify_tool_output(raw)
    assert result.quality == OutputQuality.OK
    assert result.content == raw.strip()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_result_with_leading_whitespace_is_trimmed():
    raw = "   Valid result content here.   "
    result = verify_tool_output(raw)
    assert result.quality == OutputQuality.OK
    assert result.content == raw.strip()


def test_error_check_is_case_insensitive():
    result = verify_tool_output("ERROR: timeout reached")
    assert result.quality == OutputQuality.EMPTY


def test_query_shown_in_no_results_message():
    result = verify_tool_output("", query="password reset")
    assert "password reset" in result.content


def test_query_not_shown_when_result_is_ok():
    raw = "You can reset your password via the settings page."
    result = verify_tool_output(raw, query="password reset")
    assert result.quality == OutputQuality.OK
    assert result.content == raw
