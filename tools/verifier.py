from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class OutputQuality(Enum):
    OK = "ok"
    EMPTY = "empty"


@dataclass
class VerifiedOutput:
    quality: OutputQuality
    content: str


_ERROR_PREFIXES = (
    "error",
    "no results",
    "no knowledge base",
    "no web search",
    "no memory",
    "0 results",
    "not found",
)


def verify_tool_output(raw: str, query: str = "") -> VerifiedOutput:
    """
    Assess the quality of a tool result string.

    Returns a VerifiedOutput whose content is prefixed with a [NO RESULTS] or
    [LOW QUALITY RESULT] tag when the result is empty or unhelpful, so the
    agent's system prompt can instruct it to retry with a rephrased query.
    """
    stripped = raw.strip()

    if not stripped:
        return VerifiedOutput(
            OutputQuality.EMPTY,
            f"[NO RESULTS] The tool returned no data for query: '{query}'. "
            "Try rephrasing your search or use a different tool.",
        )

    if stripped.lower().startswith(_ERROR_PREFIXES):
        return VerifiedOutput(
            OutputQuality.EMPTY,
            f"[LOW QUALITY RESULT] {stripped}\n"
            "Consider rephrasing the query or trying another tool.",
        )

    return VerifiedOutput(OutputQuality.OK, stripped)
