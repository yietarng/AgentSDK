from __future__ import annotations
from dataclasses import dataclass, field
from memory.long_term import MemoryFact


@dataclass
class AppContext:
    user_id: str
    session_id: str
    memories: list[MemoryFact] = field(default_factory=list)
