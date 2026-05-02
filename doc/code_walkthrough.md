# Code Walkthrough — Main Steps of Every File

This document describes what each source file does and the key steps inside it,
in execution order. Files are grouped by module.

---

## `config.py`

**Purpose:** Load all configuration from environment variables once at startup
and expose a single immutable `settings` object used by every other module.

| Step | What happens |
|---|---|
| 1 | `load_dotenv()` reads `.env` into the process environment |
| 2 | `Settings` frozen dataclass is defined with typed fields for every config value |
| 3 | `settings` singleton is instantiated — required vars raise `KeyError` immediately if missing, optional vars fall back to safe defaults |

---

## `database/connection.py`

**Purpose:** Provide a thread-safe MySQL connection pool and a context manager
that handles commit/rollback automatically.

| Step | What happens |
|---|---|
| 1 | `get_pool()` lazily creates a `MySQLConnectionPool` on first call using `settings`; subsequent calls return the same pool |
| 2 | `get_connection()` borrows a connection from the pool via `get_pool().get_connection()` |
| 3 | Yields the connection to the caller (`with get_connection() as conn:`) |
| 4 | On success → `conn.commit()` |
| 5 | On any exception → `conn.rollback()`, then re-raises |
| 6 | In `finally` → `conn.close()` returns the connection back to the pool (does not close the TCP socket) |

---

## `database/schema.sql`

**Purpose:** Define the three MySQL tables and seed sample knowledge base articles.

| Step | What happens |
|---|---|
| 1 | Creates `knowledge_base` — support articles with a `FULLTEXT` index on `(title, content)` for Boolean Mode search |
| 2 | Creates `user_memory` — persistent key-value facts per user; `UNIQUE KEY (user_id, memory_key)` allows upsert without duplicates |
| 3 | Creates `conversations` — one row per `TResponseInputItem` (JSON blob), ordered by auto-increment `id` for strict chronological ordering |
| 4 | `INSERT IGNORE` seeds 5 sample articles (shipping, returns, billing, account security, payments) for immediate testing |

---

## `memory/long_term.py`

**Purpose:** Read and write persistent user memory facts to the `user_memory` table.

### `recall_memories(user_id)`

| Step | What happens |
|---|---|
| 1 | Opens a DB connection via `get_connection()` |
| 2 | Runs `SELECT memory_key, memory_value FROM user_memory WHERE user_id = %s ORDER BY updated_at DESC` |
| 3 | Maps each row to a `MemoryFact(memory_key, memory_value)` dataclass |
| 4 | Returns the list (empty list if no facts exist) |

### `save_memory(user_id, memory_key, memory_value)`

| Step | What happens |
|---|---|
| 1 | Opens a DB connection |
| 2 | Runs `INSERT ... ON DUPLICATE KEY UPDATE` — inserts the fact if the key is new, updates the value and `updated_at` if the key already exists |
| 3 | Connection context manager commits automatically on exit |

---

## `memory/short_term.py` — `MySQLSession`

**Purpose:** Implement the OpenAI Agents SDK `Session` protocol so the SDK can
automatically persist and restore conversation history from MySQL each turn.

### `get_items()`

| Step | What happens |
|---|---|
| 1 | Queries the last `MAX_HISTORY_ITEMS` rows for this `session_id` (descending by `id`) inside a subquery |
| 2 | Re-orders them ascending so the SDK sees history in chronological order |
| 3 | Deserialises each row's `content` column from JSON back to a `dict` |
| 4 | Returns the list of `TResponseInputItem` dicts |

### `add_items(items)`

| Step | What happens |
|---|---|
| 1 | Returns immediately if `items` is empty (no-op) |
| 2 | For each item, extracts `role` (falls back to `type`, then `"unknown"`) and truncates to 32 chars |
| 3 | Serialises the full item dict to JSON |
| 4 | Bulk-inserts all records via `executemany` |

### `pop_item()`

| Step | What happens |
|---|---|
| 1 | Fetches the most recently inserted row (`ORDER BY id DESC LIMIT 1`) |
| 2 | If none found, returns `None` |
| 3 | Deletes that row by its `id` |
| 4 | Deserialises and returns the item |

### `clear_session()`

| Step | What happens |
|---|---|
| 1 | Runs `DELETE FROM conversations WHERE session_id = %s` to wipe all history for this session |

---

## `agent/context.py`

**Purpose:** Define the shared state object that flows through every tool call.

| Step | What happens |
|---|---|
| 1 | `AppContext` dataclass is defined with `user_id`, `session_id`, and `memories` (list of `MemoryFact`) |
| 2 | One instance is created per `run_turn()` call and passed to `Runner.run()` via the `context=` argument |
| 3 | Every tool receives it via `wrapper.context`, giving tools access to `user_id` without global state |

---

## `agent/prompts.py`

**Purpose:** Define the ReAct system prompt and inject per-user memory into it
at runtime.

### `build_memory_section(memories)`

| Step | What happens |
|---|---|
| 1 | If `memories` is empty → returns `"Known User Facts: None on file."` |
| 2 | Otherwise builds a bulleted list: `- memory_key: memory_value` for each fact |

### `render_prompt(memories)`

| Step | What happens |
|---|---|
| 1 | Calls `build_memory_section(memories)` to produce the memory text |
| 2 | Replaces `{memory_section}` in `REACT_SYSTEM_PROMPT` using `str.replace()` — intentionally avoids `.format()` so curly braces inside memory values never trigger a `KeyError` |
| 3 | Returns the fully assembled system prompt string |

### `REACT_SYSTEM_PROMPT` template

Defines four reasoning stages the agent must follow every turn:

| Stage | Instruction |
|---|---|
| **THINK** | Decide which tool fits: KB first, then web search, then memory tools |
| **ACT** | Call the tool(s); always observe before answering |
| **OBSERVE** | If result starts with `[NO RESULTS]` or `[LOW QUALITY RESULT]` → retry with a rephrased query; after two failures, escalate |
| **RESPOND** | Give a grounded, cited, concise answer; never fabricate |

---

## `agent/react_agent.py`

**Purpose:** Assemble the agent, configure the runner, and expose `run_turn()`
as the single entry point for one conversation turn.

| Step | What happens |
|---|---|
| 1 | `_build_instructions(wrapper, agent)` is a callable that the SDK invokes at the start of every run; it calls `render_prompt(wrapper.context.memories)` to produce a fresh system prompt with the user's current memory facts |
| 2 | `support_agent` is instantiated as `Agent[AppContext]` with the four tools and `_build_instructions` as its dynamic instructions |
| 3 | `_run_config = RunConfig(...)` sets the workflow name and tracing flag |
| 4 | **`run_turn(user_message, user_id, session_id)`** is the public async function: |
|   | → Calls `recall_memories(user_id)` to load long-term facts |
|   | → Builds `AppContext` with those facts |
|   | → Creates `MySQLSession(session_id, user_id)` |
|   | → Calls `await Runner.run(support_agent, input=user_message, context=context, session=session, run_config=_run_config, max_turns=settings.agent_max_turns)` |
|   | → Returns `str(result.final_output)` |

---

## `tools/verifier.py`

**Purpose:** Assess the quality of every tool result before it is returned to
the agent, tagging poor results so the agent knows to retry.

| Step | What happens |
|---|---|
| 1 | Strips leading/trailing whitespace from the raw result |
| 2 | If stripped string is empty → returns `[NO RESULTS] ...` tag with the original query |
| 3 | If the string starts with a known error prefix (e.g. `"no results"`, `"error"`, `"not found"`) → returns `[LOW QUALITY RESULT] ...` tag |
| 4 | Otherwise → returns the content unchanged with `OutputQuality.OK` |

The `[NO RESULTS]` and `[LOW QUALITY RESULT]` tags are referenced directly
in the system prompt so the agent treats them as signals to retry.

---

## `tools/retrieval.py` — `search_knowledge_base`

**Purpose:** Search the internal MySQL knowledge base and return article excerpts.

| Step | What happens |
|---|---|
| 1 | Splits the query into words; keeps only words ≥ 3 characters (MySQL FULLTEXT minimum) |
| 2 | **FULLTEXT path** (words exist): builds a Boolean Mode query string (`+word*` for each word) and runs `MATCH(title, content) AGAINST(... IN BOOLEAN MODE)` ordered by relevance |
| 3 | **LIKE fallback** (all words < 3 chars): runs `WHERE title LIKE %query% OR content LIKE %query%` |
| 4 | If no rows returned → sets `raw = "No knowledge base articles found for '...'."` |
| 5 | If rows found → formats them as a numbered list; truncates each `content` to 600 characters |
| 6 | Passes `raw` through `verify_tool_output()` and returns the verified content |

---

## `tools/web_search.py` — `web_search`

**Purpose:** Search the live web via the Tavily API and return formatted results.

| Step | What happens |
|---|---|
| 1 | `_tavily_client` is a module-level `AsyncTavilyClient` singleton (created once at import, not per call) |
| 2 | Calls `await _tavily_client.search(query=query, max_results=max_results, search_depth="basic")` |
| 3 | Extracts `response.get("results", [])` — defaults to empty list if key is absent |
| 4 | If empty → sets `raw = "No web search results found for '...'."` |
| 5 | If results exist → formats as numbered list: title, URL, and first 400 characters of content per result |
| 6 | Passes `raw` through `verify_tool_output()` and returns the verified content |

---

## `tools/memory_tools.py`

**Purpose:** Expose long-term memory read/write as agent-callable tools.

### `save_user_memory(wrapper, memory_key, memory_value)`

| Step | What happens |
|---|---|
| 1 | Reads `user_id` from `wrapper.context.user_id` |
| 2 | Calls `save_memory(user_id, memory_key, memory_value)` (delegates to `long_term.py`) |
| 3 | Returns a confirmation string the agent sees as the tool result |

### `recall_user_memory(wrapper)`

| Step | What happens |
|---|---|
| 1 | Reads `user_id` from `wrapper.context.user_id` |
| 2 | Calls `recall_memories(user_id)` to fetch all stored facts |
| 3 | If none → returns `"No memory facts found for user '...'"` |
| 4 | Otherwise → formats as a bulleted list of `key: value` pairs and returns it |

---

## `main.py`

**Purpose:** Interactive CLI REPL — the entry point for running the agent from
the terminal.

### `parse_args()`

| Step | What happens |
|---|---|
| 1 | Defines `--user-id` and `--session-id` optional CLI arguments |
| 2 | Returns the parsed `Namespace` object |

### `main()`

| Step | What happens |
|---|---|
| 1 | Calls `parse_args()` to read CLI flags |
| 2 | If `--user-id` not supplied → prompts the user interactively; defaults to `"anonymous"` |
| 3 | If `--session-id` not supplied → generates a fresh `uuid.uuid4()` |
| 4 | Calls `asyncio.run(repl(...))` to start the event loop |

### `repl(user_id, session_id)`

| Step | What happens |
|---|---|
| 1 | Prints a session header showing `user_id` and `session_id` |
| 2 | Enters an infinite `while True` loop |
| 3 | Reads input with `input("You: ")` — strips whitespace; skips empty lines |
| 4 | Breaks on `"exit"` / `"quit"` or `EOF` / `KeyboardInterrupt` |
| 5 | Calls `await run_turn(user_message, user_id, session_id)` and prints the response |
| 6 | On `MaxTurnsExceeded` → prints a graceful fallback message to `stderr` |
| 7 | On any other exception → prints the error to `stderr` and continues the loop |
