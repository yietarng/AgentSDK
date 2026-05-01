"""
Customer Support ReAct Agent — CLI entry point.

Usage:
    python main.py
    python main.py --user-id alice --session-id sess_001
"""
from __future__ import annotations
import asyncio
import argparse
import sys
import uuid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Customer Support ReAct Agent")
    parser.add_argument(
        "--user-id",
        default=None,
        help="Stable user identifier (default: prompted on start)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Session identifier; a new UUID is generated if omitted",
    )
    return parser.parse_args()


async def repl(user_id: str, session_id: str) -> None:
    from agent import run_turn
    from agents.exceptions import MaxTurnsExceeded

    print("\n[Customer Support Agent]")
    print(f"User ID : {user_id}")
    print(f"Session : {session_id}")
    print("Type 'exit' or 'quit' to end the session.\n")

    while True:
        try:
            raw = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Session ended]")
            break

        if not raw:
            continue
        if raw.lower() in {"exit", "quit"}:
            print("[Session ended]")
            break

        try:
            response = await run_turn(
                user_message=raw,
                user_id=user_id,
                session_id=session_id,
            )
            print(f"\nAgent: {response}\n")
        except MaxTurnsExceeded:
            print(
                "\n[Agent] I wasn't able to fully resolve your question in the "
                "allowed number of steps. Please try rephrasing, or a support "
                "specialist will be happy to help.\n",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"\n[Error] {exc}\n", file=sys.stderr)


def main() -> None:
    args = parse_args()

    user_id = args.user_id
    if not user_id:
        user_id = input("Enter your user ID (or press Enter for 'anonymous'): ").strip()
        if not user_id:
            user_id = "anonymous"

    session_id = args.session_id or str(uuid.uuid4())

    asyncio.run(repl(user_id=user_id, session_id=session_id))


if __name__ == "__main__":
    main()
