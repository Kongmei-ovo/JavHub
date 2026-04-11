from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MagnetSource(Protocol):
    """下载源协议 - 所有下载源必须实现此接口"""

    name: str

    async def search(self, keyword: str) -> list:
        """搜索磁力链接"""
        ...

    async def get_detail(self, content_id: str) -> dict | None:
        """获取影片详情（含磁力列表）"""
        ...

    async def get_actress_videos(self, actress_name: str) -> list:
        """获取某演员的最新作品（用于订阅检查）"""
        ...
