from __future__ import annotations
from dataclasses import dataclass
from database import get_connection


@dataclass
class MemoryFact:
    memory_key: str
    memory_value: str


def recall_memories(user_id: str) -> list[MemoryFact]:
    """Load all key-value memory facts for a user from MySQL."""
    sql = """
        SELECT memory_key, memory_value
        FROM user_memory
        WHERE user_id = %s
        ORDER BY updated_at DESC
    """
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
    return [MemoryFact(r["memory_key"], r["memory_value"]) for r in rows]


def save_memory(user_id: str, memory_key: str, memory_value: str) -> None:
    """Upsert a key-value fact for a user. Updates value if key exists."""
    sql = """
        INSERT INTO user_memory (user_id, memory_key, memory_value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            memory_value = VALUES(memory_value),
            updated_at   = NOW()
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, memory_key, memory_value))
        cursor.close()
