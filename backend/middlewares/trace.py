"""Trace-id context propagation for requests and background jobs."""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def new_trace_id() -> str:
    return uuid.uuid4().hex[:8]


def get_trace_id() -> str | None:
    return trace_id_var.get()


def set_trace_id(value: str | None) -> Token[str | None]:
    return trace_id_var.set(value)


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = new_trace_id()
        token = set_trace_id(trace_id)
        try:
            response = await call_next(request)
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            trace_id_var.reset(token)
