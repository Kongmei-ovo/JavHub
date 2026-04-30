from __future__ import annotations

import httpx
import re
import logging
from typing import Optional
from sources.base import MagnetSource
from models.video import MagnetInfo, MovieDetail

logger = logging.getLogger(__name__)


class JavBusSource:
    """JavBus 下载源实现"""

    name: str = "javbus"

    def __init__(self, api_url: str = "https://www.javbus.com", headers: dict | None = None):
        self.api_url = api_url.rstrip("/")
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.javbus.com/",
        }

    async def search(self, keyword: str) -> list[MagnetInfo]:
        """搜索磁力链接"""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(
                    f"{self.api_url}/search/{keyword}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                return self._parse_search_results(resp.text)
            except Exception as e:
                logger.error(f"JavBus search failed for '{keyword}': {e}")
                return []

    async def get_detail(self, content_id: str) -> MovieDetail | None:
        """获取影片详情（含磁力列表）"""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(
                    f"{self.api_url}/{content_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                return self._parse_detail_page(resp.text, content_id)
            except Exception as e:
                logger.error(f"JavBus get_detail failed for '{content_id}': {e}")
                return None

    async def get_actress_videos(self, actress_name: str) -> list[MagnetInfo]:
        """获取某演员的最新作品（用于订阅检查）"""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(
                    f"{self.api_url}/search/{actress_name}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                return self._parse_search_results(resp.text)
            except Exception as e:
                logger.error(f"JavBus get_actress_videos failed for '{actress_name}': {e}")
                return []

    def _parse_search_results(self, html: str) -> list[MagnetInfo]:
        """解析搜索结果页面"""
        results = []
        # 匹配影片卡片中的番号
        pattern = r'<a class="movie-box" href="/([\w]+)">.*?<span class="id">([\w-]+)</span>.*?<span class="date">([\d-]+)</span>'
        for match in re.finditer(pattern, html, re.DOTALL):
            path, code, date = match.groups()
            results.append(MagnetInfo(
                title=code,
                magnet="",
                size="",
                resolution="",
                hd=False,
                subtitle=False,
            ))
        return results

    def _parse_detail_page(self, html: str, content_id: str) -> MovieDetail | None:
        """解析详情页面"""
        title_match = re.search(r'<h3>(.*?)</h3>', html)
        title = title_match.group(1).strip() if title_match else content_id

        magnets = []
        # 匹配磁力链接
        magnet_pattern = r'magnet:\?xt=urn:btih:([a-fA-F0-9]{40,})[^"\']*'
        for match in re.finditer(magnet_pattern, html):
            magnet_hash = match.group(1)
            magnet_uri = f"magnet:?xt=urn:btih:{magnet_hash}"
            magnets.append(MagnetInfo(
                title=title,
                magnet=magnet_uri,
                size="",
                resolution="",
                hd=False,
                subtitle=False,
            ))

        if not magnets:
            return None

        return MovieDetail(
            content_id=content_id,
            title=title,
            magnets=magnets,
        )
