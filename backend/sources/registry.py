from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import ClassVar

from sources.base import MagnetSource

# Import MagnetInfo for type hints
from models.video import MagnetInfo


class SourceRegistry:
    _sources: ClassVar[dict[str, MagnetSource]] = {}
    _priority: ClassVar[list[str]] = []
    _attempts: ClassVar[list[dict]] = []
    _max_attempts: ClassVar[int] = 200

    @classmethod
    def register(cls, source: MagnetSource) -> None:
        """注册下载源"""
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
    ) -> None:
        cls._attempts.append(
            {
                "source": source,
                "keyword": keyword,
                "duration_ms": round((time.monotonic() - started_at) * 1000, 3),
                "result_count": result_count,
                "error": error,
                "ok": ok,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(cls._attempts) > cls._max_attempts:
            del cls._attempts[: len(cls._attempts) - cls._max_attempts]

    @classmethod
    async def search_all(cls, keyword: str) -> list[MagnetInfo]:
        """按优先级遍历所有源搜索，返回聚合结果"""
        results = []
        for name in cls._priority:
            source = cls._sources.get(name)
            if source:
                started_at = time.monotonic()
                try:
                    source_results = await source.search(keyword)
                    result_count = 0
                    for item in source_results:
                        row = dict(item)
                        row.setdefault("source", name)
                        results.append(row)
                        result_count += 1
                    cls._record_attempt(
                        source=name,
                        keyword=keyword,
                        started_at=started_at,
                        result_count=result_count,
                        ok=True,
                    )
                except Exception as exc:
                    cls._record_attempt(
                        source=name,
                        keyword=keyword,
                        started_at=started_at,
                        result_count=0,
                        ok=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    continue
        return results
