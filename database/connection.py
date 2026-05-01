from mysql.connector import pooling
from contextlib import contextmanager
from config import settings

_pool: pooling.MySQLConnectionPool | None = None


def get_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="support_pool",
            pool_size=settings.mysql_pool_size,
            pool_reset_session=True,
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
        )
    return _pool


@contextmanager
def get_connection():
    """Yield a pooled connection; commit on success, rollback on error."""
    conn = get_pool().get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()  # returns to pool, does not close the TCP socket
