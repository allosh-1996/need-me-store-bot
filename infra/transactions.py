from __future__ import annotations
from contextlib import contextmanager
from typing import Generator
import threading
import logging

logger = logging.getLogger(__name__)

_local = threading.local()


@contextmanager
def transactional() -> Generator[None, None, None]:
    """
    Wraps the block in a real Turso interactive transaction (BEGIN/COMMIT/ROLLBACK).
    All execute() calls inside will use the transaction connection.
    Nested calls are no-ops — the outermost transaction covers everything.
    """
    if getattr(_local, "active", False):
        yield
        return

    from infra.db import get_client
    import infra.db as db_module

    txn = get_client().transaction()
    original_execute = db_module.execute

    def txn_execute(sql: str, params: tuple = ()):
        from infra.db import _Result
        args = list(params) if params else None
        rs = txn.execute(sql, args)
        return _Result(rs)

    _local.active = True
    db_module.execute = txn_execute

    try:
        yield
        txn.commit()
    except Exception:
        try:
            txn.rollback()
        except Exception:
            pass
        raise
    finally:
        db_module.execute = original_execute
        _local.active = False
        try:
            txn.close()
        except Exception:
            pass
