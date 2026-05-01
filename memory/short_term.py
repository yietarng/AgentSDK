from __future__ import annotations
import json
from typing import Any
from database import get_connection

TResponseInputItem = dict[str, Any]


class MySQLSession:
    """
    Persistent conversation session backed by the MySQL conversations table.

    Implements the OpenAI Agents SDK Session protocol so the SDK can call
    get_items() / add_items() automatically each turn.

    Each TResponseInputItem is stored as a JSON blob; the 'role' column is
    extracted for human-readable querying but the JSON blob is the source of truth.
    """

    def __init__(self, session_id: str, user_id: str) -> None:
        self.session_id = session_id
        self.user_id = user_id

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        """Return stored items for this session in insertion order."""
        if limit is not None:
            # Fetch the last `limit` rows while preserving ascending order
            sql = """
                SELECT content FROM (
                    SELECT id, content
                    FROM conversations
                    WHERE session_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                ) sub
                ORDER BY id ASC
            """
            params = (self.session_id, int(limit))
        else:
            sql = """
                SELECT content
                FROM conversations
                WHERE session_id = %s
                ORDER BY id ASC
            """
            params = (self.session_id,)

        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()

        return [json.loads(row["content"]) for row in rows]

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        """Persist new items appended during this agent run."""
        if not items:
            return
        sql = """
            INSERT INTO conversations (session_id, user_id, role, content)
            VALUES (%s, %s, %s, %s)
        """
        records = []
        for item in items:
            role = item.get("role", item.get("type", "unknown"))
            records.append((
                self.session_id,
                self.user_id,
                str(role)[:32],
                json.dumps(item, ensure_ascii=False),
            ))

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, records)
            cursor.close()

    async def pop_item(self) -> TResponseInputItem | None:
        """Remove and return the most recently inserted item."""
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, content FROM conversations "
                "WHERE session_id = %s ORDER BY id DESC LIMIT 1",
                (self.session_id,),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.close()
                return None
            cursor.execute("DELETE FROM conversations WHERE id = %s", (row["id"],))
            cursor.close()
        return json.loads(row["content"])

    async def clear_session(self) -> None:
        """Delete all items for this session."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM conversations WHERE session_id = %s",
                (self.session_id,),
            )
            cursor.close()
