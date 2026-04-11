from __future__ import annotations

from typing import ClassVar

from sources.base import MagnetSource

# Import MagnetInfo for type hints
from models.video import MagnetInfo


class SourceRegistry:
    _sources: ClassVar[dict[str, MagnetSource]] = {}
    _priority: ClassVar[list[str]] = []

    @classmethod
    def register(cls, source: MagnetSource) -> None:
        """注册下载源"""
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
    async def search_all(cls, keyword: str) -> list[MagnetInfo]:
        """按优先级遍历所有源搜索，返回聚合结果"""
        results = []
        for name in cls._priority:
            source = cls._sources.get(name)
            if source:
                try:
                    results.extend(await source.search(keyword))
                except Exception:
                    continue
        return results
