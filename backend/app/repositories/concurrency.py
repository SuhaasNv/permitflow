"""Database concurrency errors translated for the services (US-073): a deadlock between two writers
becomes one domain-level error, so no service needs to know the driver."""

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg.errors import DeadlockDetected
from sqlalchemy.exc import OperationalError


class DeadlockError(Exception):
    """Two transactions waited on each other; PostgreSQL cancelled this one. Safe to retry."""


@contextmanager
def deadlock_as_error() -> Iterator[None]:
    try:
        yield
    except OperationalError as exc:
        if isinstance(exc.orig, DeadlockDetected):
            raise DeadlockError() from exc
        raise


__all__ = ["DeadlockError", "deadlock_as_error"]
