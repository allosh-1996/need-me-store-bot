from contextlib import contextmanager


@contextmanager
def transactional():
    """
    Logical grouping of DB operations.
    Turso HTTP auto-commits each statement — no manual transaction needed.
    """
    yield
