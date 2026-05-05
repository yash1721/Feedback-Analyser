from contextvars import ContextVar
from uuid import uuid4


_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(correlation_id: str):
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token) -> None:
    _correlation_id.reset(token)


def new_correlation_id() -> str:
    return str(uuid4())
