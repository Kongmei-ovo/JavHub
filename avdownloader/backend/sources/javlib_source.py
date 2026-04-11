from __future__ import annotations

from sources.base import MagnetSource
from models.video import MagnetInfo, MovieDetail


class JavLibSource:
    """JavLib 下载源实现"""

    name: str = "javlib"

    def __init__(self, api_url: str = "https://www.javlib.com", headers: dict | None = None):
        self.api_url = api_url.rstrip("/")
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

    async def search(self, keyword: str) -> list[MagnetInfo]:
        """搜索磁力链接"""
        # TODO: 实现 JavLib API 调用
        return []

    async def get_detail(self, content_id: str) -> MovieDetail | None:
        """获取影片详情"""
        # TODO: 实现
        return None

    async def get_actress_videos(self, actress_name: str) -> list[MagnetInfo]:
        """获取演员作品"""
        # TODO: 实现
        return []
