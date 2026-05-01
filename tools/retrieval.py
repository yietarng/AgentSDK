from __future__ import annotations
from typing import Annotated
from agents import function_tool, RunContextWrapper
from agent.context import AppContext
from database import get_connection
from tools.verifier import verify_tool_output


@function_tool
async def search_knowledge_base(
    wrapper: RunContextWrapper[AppContext],
    query: Annotated[str, "Keywords or phrase to search in the internal support knowledge base."],
    max_results: Annotated[int, "Maximum number of articles to return (1-5)."] = 3,
) -> str:
    """
    Search the internal support knowledge base for relevant articles.

    Use this tool FIRST before web search when the user has a product-specific
    question, troubleshooting request, or asks about policies, procedures, or
    features. The knowledge base contains curated, authoritative support content.

    Returns matching article titles and content excerpts.
    If the result starts with [NO RESULTS] or [LOW QUALITY RESULT], rephrase
    the query and try again before falling back to web_search.
    """
    words = [w.strip() for w in query.split() if len(w.strip()) >= 3]

    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        if words:
            boolean_query = " ".join(f"+{w}*" for w in words)
            sql = """
                SELECT title, content, category,
                       MATCH(title, content) AGAINST(%s IN BOOLEAN MODE) AS relevance
                FROM knowledge_base
                WHERE MATCH(title, content) AGAINST(%s IN BOOLEAN MODE)
                ORDER BY relevance DESC
                LIMIT %s
            """
            cursor.execute(sql, (boolean_query, boolean_query, max_results))
        else:
            like_pattern = f"%{query}%"
            sql = """
                SELECT title, content, category
                FROM knowledge_base
                WHERE title LIKE %s OR content LIKE %s
                LIMIT %s
            """
            cursor.execute(sql, (like_pattern, like_pattern, max_results))

        rows = cursor.fetchall()
        cursor.close()

    if not rows:
        raw = f"No knowledge base articles found for '{query}'."
    else:
        lines = [f"Knowledge base results for: '{query}'\n"]
        for i, row in enumerate(rows, 1):
            excerpt = row["content"][:600].replace("\n", " ")
            lines.append(f"{i}. [{row['title']}] (category: {row['category']})")
            lines.append(f"   {excerpt}...")
        raw = "\n".join(lines)

    verified = verify_tool_output(raw, query=query)
    return verified.content
