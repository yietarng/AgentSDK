from __future__ import annotations
from typing import Annotated
from agents import function_tool, RunContextWrapper
from tavily import AsyncTavilyClient
from agent.context import AppContext
from config import settings
from tools.verifier import verify_tool_output

# Module-level singleton — avoids creating a new client on every tool call.
_tavily_client = AsyncTavilyClient(api_key=settings.tavily_api_key)


@function_tool
async def web_search(
    wrapper: RunContextWrapper[AppContext],
    query: Annotated[str, "The search query to look up current information on the web."],
    max_results: Annotated[int, "Maximum number of results to return (1-10)."] = 5,
) -> str:
    """
    Search the web for current information using Tavily.

    Use this tool when the user asks about recent events, product updates,
    pricing, availability, or any information that may have changed recently
    and is unlikely to be in the internal knowledge base.

    Returns a formatted list of results with titles, URLs, and content snippets.
    If the result starts with [NO RESULTS] or [LOW QUALITY RESULT], rephrase
    the query and try again.
    """
    response = await _tavily_client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
    )
    results = response.get("results", [])

    if not results:
        raw = f"No web search results found for '{query}'."
    else:
        lines = [f"Web search results for: '{query}'\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r.get('title', 'No title')}]({r.get('url', '')})")
            lines.append(f"   {r.get('content', '')[:400]}")
        raw = "\n".join(lines)

    verified = verify_tool_output(raw, query=query)
    return verified.content
