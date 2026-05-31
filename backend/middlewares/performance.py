"""Request timing middleware for lightweight API performance visibility."""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, slow_request_ms: float = 500.0):
        super().__init__(app)
        self.slow_request_ms = float(slow_request_ms)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        if elapsed_ms >= self.slow_request_ms:
            logger.warning(
                "Slow request %.2fms %s %s status=%s",
                elapsed_ms,
                request.method,
                request.url.path,
                response.status_code,
            )
        return response
