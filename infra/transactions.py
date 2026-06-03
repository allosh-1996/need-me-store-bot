from contextlib import contextmanager


@contextmanager
def transactional():
    """
    Context manager for logical grouping of DB operations.

    Note: libsql_client (Turso HTTP) auto-commits each statement.
    True multi-statement atomicity requires batch() — handled per-service
    when needed. This wrapper preserves the service interface unchanged
    and re-raises any exception from the block.
    """
    try:
        yield
    except Exception:
        raise
