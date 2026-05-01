from __future__ import annotations
from typing import Annotated
from agents import function_tool, RunContextWrapper
from agent.context import AppContext
from memory.long_term import save_memory, recall_memories


@function_tool
async def save_user_memory(
    wrapper: RunContextWrapper[AppContext],
    memory_key: Annotated[
        str,
        "A short descriptive key for this fact, e.g. 'preferred_language', "
        "'account_type', 'last_reported_issue'. Use snake_case.",
    ],
    memory_value: Annotated[str, "The value to store for this fact, as a concise string."],
) -> str:
    """
    Save an important fact about the user to persistent long-term memory.

    Use this tool when the user reveals information that will be useful in
    future sessions: their name, account tier, preferred contact method,
    a recurring problem, or a stated preference.

    Do NOT save trivial or session-specific information. Only save durable facts.
    """
    user_id = wrapper.context.user_id
    save_memory(user_id, memory_key, memory_value)
    return f"Memory saved: '{memory_key}' = '{memory_value}' for user {user_id}."


@function_tool
async def recall_user_memory(
    wrapper: RunContextWrapper[AppContext],
) -> str:
    """
    Retrieve all previously saved memory facts for the current user.

    Use this tool mid-session only if you need to re-check or refresh facts
    beyond what was already injected into your system prompt at session start.

    Returns a formatted list of key-value memory facts.
    """
    user_id = wrapper.context.user_id
    facts = recall_memories(user_id)
    if not facts:
        return f"No memory facts found for user '{user_id}'."
    lines = [f"Memory facts for user '{user_id}':"]
    for fact in facts:
        lines.append(f"  - {fact.memory_key}: {fact.memory_value}")
    return "\n".join(lines)
