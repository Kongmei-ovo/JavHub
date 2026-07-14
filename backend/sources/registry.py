from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import ClassVar

from sources.base import MagnetSource

# Import MagnetInfo for type hints
from models.video import MagnetInfo
from services.secret_redactor import redact_sensitive_text


class SourceRegistry:
    _sources: ClassVar[dict[str, MagnetSource]] = {}
    _priority: ClassVar[list[str]] = []
    _attempts: ClassVar[list[dict]] = []
    _max_attempts: ClassVar[int] = 200

    @classmethod
    def register(cls, source: MagnetSource) -> None:
        """注册下载源"""
        # Streaming providers (for example M3U8Source) are not magnet indexers.
        # Registering one without ``search`` turns a configuration problem into
        # a misleading successful search with zero results because _search_one
        # intentionally isolates provider exceptions.
        if not callable(getattr(source, "search", None)):
            return
        is_implemented = getattr(source, "is_implemented", None)
        if callable(is_implemented) and not is_implemented():
            return
        cls._sources[source.name] = source
        if source.name not in cls._priority:
            cls._priority.append(source.name)

    @classmethod
    def get(cls, name: str) -> MagnetSource | None:
        return cls._sources.get(name)

    @classmethod
    def all(cls) -> list[MagnetSource]:
        return list(cls._sources.values())

    @classmethod
    def priority(cls) -> list[str]:
        return cls._priority.copy()

    @classmethod
    def recent_attempts(cls, limit: int = 100) -> list[dict]:
        """返回最近的源搜索尝试记录。"""
        if limit <= 0:
            return []
        return [attempt.copy() for attempt in cls._attempts[-limit:]]

    @classmethod
    def clear_attempts(cls) -> None:
        """清空源搜索尝试记录，供测试和健康面板使用。"""
        cls._attempts.clear()

    @classmethod
    def _record_attempt(
        cls,
        *,
        source: str,
        keyword: str,
        started_at: float,
        result_count: int,
        ok: bool,
        error: str = "",
    ) -> dict:
        duration_ms = round((time.monotonic() - started_at) * 1000, 3)
        attempt = {
            "source": source,
            "keyword": keyword,
            "duration_ms": duration_ms,
            "result_count": result_count,
            "error": error,
            "ok": ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        cls._attempts.append(attempt)
        if len(cls._attempts) > cls._max_attempts:
            del cls._attempts[: len(cls._attempts) - cls._max_attempts]
        try:
            from database.source_attempt import record_source_attempt

            record_source_attempt(
                source=source,
                keyword=keyword,
                ok=ok,
                duration_ms=duration_ms,
                result_count=result_count,
                error=error,
            )
        except Exception:
            pass
        return attempt.copy()

    @classmethod
    async def _search_one(cls, name: str, keyword: str) -> tuple[list[dict], dict | None]:
        """Search a single source, recording the attempt and isolating errors."""
        source = cls._sources.get(name)
        if not source:
            return [], None
        started_at = time.monotonic()
        try:
            source_results = await source.search(keyword)
            rows = []
            for item in source_results:
                row = dict(item)
                row.setdefault("source", name)
                rows.append(row)
            attempt = cls._record_attempt(
                source=name,
                keyword=keyword,
                started_at=started_at,
                result_count=len(rows),
                ok=True,
            )
            return rows, attempt
        except Exception as exc:
            attempt = cls._record_attempt(
                source=name,
                keyword=keyword,
                started_at=started_at,
                result_count=0,
                ok=False,
                error=_sanitized_error(exc, source),
            )
            return [], attempt

    @classmethod
    async def search_selected(
        cls,
        keyword: str,
        names: list[str] | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Search the requested runtime sources and return call-local attempts."""
        requested = cls.priority() if names is None else list(names)
        selected = list(dict.fromkeys(name for name in requested if cls._sources.get(name)))
        if not selected:
            return [], []
        batches = await asyncio.gather(
            *(cls._search_one(name, keyword) for name in selected)
        )
        results = [row for rows, _attempt in batches for row in rows]
        attempts = [attempt for _rows, attempt in batches if attempt is not None]
        return results, attempts

    @classmethod
    async def search_all(cls, keyword: str) -> list[MagnetInfo]:
        """并发查询所有源，按优先级顺序聚合结果。"""
        results, _attempts = await cls.search_selected(keyword)
        return results


def _sanitized_error(exc: Exception, source: MagnetSource) -> str:
    text = f"{type(exc).__name__}: {exc}"
    secret = str(getattr(source, "api_key", "") or "")
    return redact_sensitive_text(text, secrets=(secret,))
