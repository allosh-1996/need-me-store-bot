from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Generator

import libsql_client

logger = logging.getLogger(__name__)

_local = threading.local()


def _get_txn() -> libsql_client.Transaction | None:
    return getattr(_local, "txn", None)


@contextmanager
def transactional() -> Generator[None, None, None]:
    """
    Wraps the block in a real Turso interactive transaction.

    - Thread-safe: each thread has its own transaction via threading.local.
    - No monkey-patching: infra.db.execute() checks _local.txn_execute directly.
    - Nested calls are no-ops — the outermost transaction covers everything.
    """
    if getattr(_local, "active", False):
        # Already inside a transaction on this thread — nested call, just yield
        yield
        return

    from infra.db import get_client, _Result

    client = get_client()
    txn = client.transaction()

    def txn_execute(sql: str, params: tuple = ()) -> _Result:
        args = list(params) if params else None
        rs = txn.execute(sql, args)
        return _Result(rs)

    _local.active = True
    _local.txn = txn
    _local.txn_execute = txn_execute

    try:
        yield
        txn.commit()
        logger.debug("Transaction committed on thread %s", threading.current_thread().name)
    except Exception:
        try:
            txn.rollback()
            logger.debug("Transaction rolled back on thread %s", threading.current_thread().name)
        except Exception:
            pass
        raise
    finally:
        _local.active = False
        _local.txn = None
        _local.txn_execute = None
        try:
            txn.close()
        except Exception:
            pass
