from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

_local = threading.local()


@contextmanager
def transactional() -> Generator[None, None, None]:
    """
    Wraps the block in a real transaction via the libsql connection.
    Thread-safe: each thread has its own connection via threading.local.
    Nested calls are no-ops — the outermost transaction covers everything.
    """
    if getattr(_local, "active", False):
        yield
        return

    from infra.db import get_connection, _Result

    conn = get_connection()

    def txn_execute(sql: str, params: tuple = ()) -> _Result:
        cur = conn.cursor()
        cur.execute(sql, params)
        return _Result(cur)

    _local.active = True
    _local.txn_execute = txn_execute

    try:
        yield
        conn.commit()
        logger.debug("Transaction committed on thread %s", threading.current_thread().name)
    except Exception:
        try:
            conn.rollback()
            logger.debug("Transaction rolled back on thread %s", threading.current_thread().name)
        except Exception:
            pass
        raise
    finally:
        _local.active = False
        _local.txn_execute = None
