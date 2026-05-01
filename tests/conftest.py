"""
Global test configuration.

IMPORTANT: environment variables and sys.modules stubs MUST be set before any
project module is imported, because config.py reads env vars at module level
and tools/*.py import from the three packages that are not installed.
"""
import os
import sys
import json
from contextlib import contextmanager
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Environment variables (read by config.py at import time)
# ---------------------------------------------------------------------------
_TEST_ENV = {
    "OPENAI_API_KEY": "sk-test-key",
    "OPENAI_MODEL": "gpt-4o",
    "TAVILY_API_KEY": "tvly-test-key",
    "MYSQL_HOST": "localhost",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "test_user",
    "MYSQL_PASSWORD": "test_pass",
    "MYSQL_DATABASE": "test_db",
    "MYSQL_POOL_SIZE": "2",
    "AGENT_MAX_TURNS": "10",
    "MAX_HISTORY_ITEMS": "20",
}
for k, v in _TEST_ENV.items():
    os.environ.setdefault(k, v)

# ---------------------------------------------------------------------------
# 2. Stub: mysql.connector (not installed)
# ---------------------------------------------------------------------------
_mysql_pkg = MagicMock()
_mysql_connector = MagicMock()
_mysql_pooling = MagicMock()
_mysql_pkg.connector = _mysql_connector
_mysql_connector.pooling = _mysql_pooling
sys.modules.setdefault("mysql", _mysql_pkg)
sys.modules.setdefault("mysql.connector", _mysql_connector)
sys.modules.setdefault("mysql.connector.pooling", _mysql_pooling)

# ---------------------------------------------------------------------------
# 3. Stub: tavily (not installed)
#    AsyncTavilyClient returns a shared AsyncMock instance so tests can
#    configure search.return_value per-test.
# ---------------------------------------------------------------------------
_tavily_instance = AsyncMock()
_tavily_pkg = MagicMock()
_tavily_pkg.AsyncTavilyClient = MagicMock(return_value=_tavily_instance)
sys.modules.setdefault("tavily", _tavily_pkg)

# ---------------------------------------------------------------------------
# 4. Stub: agents / agents.exceptions (openai-agents not installed)
#    @function_tool becomes a plain pass-through so decorated functions keep
#    their original callable signature — tests can call them directly.
# ---------------------------------------------------------------------------
def _passthrough_function_tool(fn=None, **kwargs):
    """Pass-through so @function_tool leaves the function unchanged."""
    if callable(fn):
        return fn
    return lambda f: f


class _MaxTurnsExceeded(Exception):
    pass


_agents_exceptions = MagicMock()
_agents_exceptions.MaxTurnsExceeded = _MaxTurnsExceeded

# Agent[T] uses __class_getitem__; MagicMock doesn't support that by default.
class _AgentStub:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, **kwargs):
        pass


_agents_pkg = MagicMock()
_agents_pkg.function_tool = _passthrough_function_tool
_agents_pkg.RunContextWrapper = MagicMock
_agents_pkg.Agent = _AgentStub
_agents_pkg.RunConfig = MagicMock
_agents_pkg.Runner = MagicMock()
_agents_pkg.Runner.run = AsyncMock()
_agents_pkg.exceptions = _agents_exceptions

sys.modules.setdefault("agents", _agents_pkg)
sys.modules.setdefault("agents.exceptions", _agents_exceptions)

# ---------------------------------------------------------------------------
# 5. Shared fixtures
# ---------------------------------------------------------------------------

def make_mock_cursor(rows=None, one_row=None):
    """Build a mock cursor that returns canned rows."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows if rows is not None else []
    cursor.fetchone.return_value = one_row
    return cursor


def make_mock_conn(cursor):
    """Build a mock MySQL connection using the given cursor."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


@contextmanager
def mock_get_conn_ctx(conn):
    """A context manager that yields *conn*, mimicking get_connection()."""
    yield conn


@pytest.fixture
def mock_wrapper():
    """RunContextWrapper mock with a pre-populated AppContext."""
    from agent.context import AppContext
    ctx = AppContext(user_id="u_test", session_id="s_test", memories=[])
    wrapper = MagicMock()
    wrapper.context = ctx
    return wrapper


@pytest.fixture
def tavily_instance():
    """Expose the shared Tavily AsyncMock so tests can configure it."""
    return _tavily_instance


@pytest.fixture
def agents_runner():
    """Expose the agents.Runner mock so tests can configure Runner.run."""
    return _agents_pkg.Runner
