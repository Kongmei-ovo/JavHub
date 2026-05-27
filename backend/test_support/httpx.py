from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class FakeHTTPResponse:
    def __init__(
        self,
        payload: Any = None,
        *,
        status_code: int = 200,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP status {self.status_code}")

    def json(self) -> Any:
        return self._payload


class RecordingAsyncClient:
    calls: list[dict[str, Any]] = []
    _responses: dict[str, deque[Any]] = defaultdict(deque)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.__class__.calls.append({"method": "__init__", "args": args, "kwargs": kwargs})

    @classmethod
    def reset(cls) -> None:
        cls.calls = []
        cls._responses = defaultdict(deque)

    @classmethod
    def add_response(cls, method: str, response: Any) -> None:
        cls._responses[method.lower()].append(response)

    async def __aenter__(self) -> "RecordingAsyncClient":
        self.__class__.calls.append({"method": "__aenter__", "args": (), "kwargs": {}})
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.__class__.calls.append({"method": "__aexit__", "args": (exc_type, exc, tb), "kwargs": {}})
        return None

    async def get(self, url: str, **kwargs: Any) -> Any:
        return self._record_and_respond("get", url, kwargs)

    async def post(self, url: str, **kwargs: Any) -> Any:
        return self._record_and_respond("post", url, kwargs)

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        return self._record_and_respond(method.lower(), url, kwargs)

    def _record_and_respond(self, method: str, url: str, kwargs: dict[str, Any]) -> Any:
        normalized = method.lower()
        self.__class__.calls.append({"method": normalized, "url": url, "kwargs": kwargs})
        response = self._next_response(normalized)
        if callable(response):
            return response(method=normalized, url=url, kwargs=kwargs)
        return response

    def _next_response(self, method: str) -> Any:
        queue = self.__class__._responses[method]
        if not queue:
            return FakeHTTPResponse()
        return queue.popleft()
