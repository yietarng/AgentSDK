from __future__ import annotations
from agents import Agent, Runner, RunConfig
from agents import RunContextWrapper
from agent.context import AppContext
from agent.prompts import render_prompt
from memory.long_term import recall_memories
from memory.short_term import MySQLSession
from tools import web_search, search_knowledge_base, save_user_memory, recall_user_memory
from config import settings


def _build_instructions(
    wrapper: RunContextWrapper[AppContext],
    agent: "Agent[AppContext]",
) -> str:
    """Dynamic instructions callable — injects the user's long-term memories each run."""
    return render_prompt(wrapper.context.memories)


support_agent = Agent[AppContext](
    name="CustomerSupportAgent",
    instructions=_build_instructions,
    model=settings.openai_model,
    tools=[
        search_knowledge_base,
        web_search,
        save_user_memory,
        recall_user_memory,
    ],
)

# max_turns belongs on Runner.run(), not RunConfig — passing it here causes TypeError
_run_config = RunConfig(
    workflow_name="CustomerSupport",
    tracing_disabled=False,
)


async def run_turn(
    user_message: str,
    user_id: str,
    session_id: str,
) -> str:
    """
    Execute one user turn and return the agent's final text response.

    Long-term memories are loaded before the run and injected into the system
    prompt via the dynamic instructions callable. Short-term history is handled
    automatically by MySQLSession (get_items / add_items).

    Raises MaxTurnsExceeded if the agent loops beyond settings.agent_max_turns.
    """
    memories = recall_memories(user_id)

    context = AppContext(
        user_id=user_id,
        session_id=session_id,
        memories=memories,
    )

    session = MySQLSession(session_id=session_id, user_id=user_id)

    result = await Runner.run(
        support_agent,
        input=user_message,
        context=context,
        session=session,
        run_config=_run_config,
        max_turns=settings.agent_max_turns,
    )

    return str(result.final_output)
