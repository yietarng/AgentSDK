"""
Unit tests for agent/prompts.py.

Pure Python — no mocks needed.
"""
import pytest
from memory.long_term import MemoryFact
from agent.prompts import build_memory_section, render_prompt, REACT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# build_memory_section
# ---------------------------------------------------------------------------

def test_no_memories_returns_none_on_file():
    result = build_memory_section([])
    assert "None on file" in result


def test_single_memory_appears_in_section():
    facts = [MemoryFact("account_tier", "premium")]
    result = build_memory_section(facts)
    assert "account_tier" in result
    assert "premium" in result


def test_multiple_memories_all_appear():
    facts = [
        MemoryFact("name", "Alice"),
        MemoryFact("account_tier", "plus"),
        MemoryFact("preferred_contact", "email"),
    ]
    result = build_memory_section(facts)
    assert "name" in result and "Alice" in result
    assert "account_tier" in result and "plus" in result
    assert "preferred_contact" in result and "email" in result


def test_memory_section_has_header():
    facts = [MemoryFact("k", "v")]
    result = build_memory_section(facts)
    assert "Known User Facts" in result


def test_memory_section_uses_bullet_format():
    facts = [MemoryFact("plan", "pro")]
    result = build_memory_section(facts)
    assert "- plan: pro" in result


# ---------------------------------------------------------------------------
# render_prompt — normal usage
# ---------------------------------------------------------------------------

def test_render_prompt_returns_string():
    result = render_prompt([])
    assert isinstance(result, str)


def test_render_prompt_contains_react_sections():
    result = render_prompt([])
    assert "THINK" in result
    assert "ACT" in result
    assert "OBSERVE" in result
    assert "RESPOND" in result


def test_render_prompt_contains_tool_priority():
    result = render_prompt([])
    assert "search_knowledge_base" in result
    assert "web_search" in result
    assert "save_user_memory" in result


def test_render_prompt_injects_memory_section_with_facts():
    facts = [MemoryFact("account_tier", "premium")]
    result = render_prompt(facts)
    assert "account_tier" in result
    assert "premium" in result


def test_render_prompt_injects_none_on_file_when_empty():
    result = render_prompt([])
    assert "None on file" in result


def test_render_prompt_placeholder_is_replaced():
    result = render_prompt([])
    # The raw {memory_section} placeholder must not appear in the output
    assert "{memory_section}" not in result


# ---------------------------------------------------------------------------
# render_prompt — curly-brace safety (regression for the .format() bug)
# ---------------------------------------------------------------------------

def test_render_prompt_safe_with_curly_braces_in_value():
    """Memory values containing { or } must not cause a crash."""
    facts = [MemoryFact("account_type", "{premium}")]
    # This would have raised KeyError with .format(); must succeed now
    result = render_prompt(facts)
    assert "{premium}" in result


def test_render_prompt_safe_with_double_curly_braces():
    facts = [MemoryFact("note", "{{special}} user")]
    result = render_prompt(facts)
    assert "{{special}}" in result


def test_render_prompt_safe_with_nested_braces():
    facts = [MemoryFact("data", '{"key": "value"}')]
    result = render_prompt(facts)
    assert '{"key": "value"}' in result


# ---------------------------------------------------------------------------
# REACT_SYSTEM_PROMPT template sanity
# ---------------------------------------------------------------------------

def test_template_contains_placeholder():
    assert "{memory_section}" in REACT_SYSTEM_PROMPT


def test_template_contains_no_results_instruction():
    assert "[NO RESULTS]" in REACT_SYSTEM_PROMPT
    assert "[LOW QUALITY RESULT]" in REACT_SYSTEM_PROMPT
