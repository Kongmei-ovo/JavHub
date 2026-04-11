from __future__ import annotations
import httpx
from typing import Any

# DMM/FANZA 图片基础URL
DMM_IMAGE_BASE_URL = "https://pics.dmm.co.jp"


def _transform_jacket_url(jacket_path: str | None) -> str | None:
    """将相对路径转换为完整的DMM图片URL"""
    if not jacket_path:
        return None
    if jacket_path.startswith("http"):
        return jacket_path
    # 移除开头的斜杠（如果有）
    jacket_path = jacket_path.lstrip("/")
    return f"{DMM_IMAGE_BASE_URL}/{jacket_path}.jpg"


def _transform_video_item(item: dict) -> dict:
    """转换视频项的图片URL为完整路径"""
    if not item:
        return item
    item = dict(item)
    if "jacket_thumb_url" in item:
        item["jacket_thumb_url"] = _transform_jacket_url(item.get("jacket_thumb_url"))
    if "jacket_full_url" in item:
        item["jacket_full_url"] = _transform_jacket_url(item.get("jacket_full_url"))
    return item


class InfoClient:
    """JavInfoApi HTTP 客户端"""

    def __init__(self, api_url: str = "http://localhost:8080", timeout: int = 30):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False  # 禁用系统代理，避免代理导致连接问题
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"{self.api_url}{path}", params=params)
        response.raise_for_status()
        return response.json()

    async def _get_list(self, path: str, params: dict | None = None) -> list[dict]:
        client = await self._get_client()
        response = await client.get(f"{self.api_url}{path}", params=params)
        response.raise_for_status()
        return response.json()

    # === 视频相关 ===

    async def search_videos(
        self,
        q: str | None = None,
        content_id: str | None = None,
        maker_id: int | None = None,
        maker_name: str | None = None,
        series_id: int | None = None,
        series_name: str | None = None,
        actress_id: int | None = None,
        actress_name: str | None = None,
        category_id: int | None = None,
        category_name: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """搜索视频"""
        params = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        if content_id:
            # JavInfoApi 用 dvd_id 来匹配番号
            params["dvd_id"] = content_id
        if maker_id:
            params["maker_id"] = maker_id
        if maker_name:
            params["maker_name"] = maker_name
        if series_id:
            params["series_id"] = series_id
        if series_name:
            params["series_name"] = series_name
        if actress_id:
            params["actress_id"] = actress_id
        if actress_name:
            params["actress_name"] = actress_name
        if category_id:
            params["category_id"] = category_id
        if category_name:
            params["category_name"] = category_name
        result = await self._get("/api/v1/videos/search", params)
        # 转换图片URL
        if "data" in result and isinstance(result["data"], list):
            result["data"] = [_transform_video_item(item) for item in result["data"]]
        return result

    async def list_videos(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取视频列表"""
        result = await self._get("/api/v1/videos", params={"page": page, "page_size": page_size})
        # 转换图片URL
        if "data" in result and isinstance(result["data"], list):
            result["data"] = [_transform_video_item(item) for item in result["data"]]
        return result

    async def get_video(self, content_id: str, service_code: str | None = None) -> dict[str, Any]:
        """获取视频详情"""
        params = {}
        if service_code:
            params["service_code"] = service_code
        result = await self._get(f"/api/v1/videos/{content_id}", params=params or None)
        # 转换图片URL
        return _transform_video_item(result)

    # === 演员相关 ===

    async def list_actresses(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取演员列表"""
        return await self._get("/api/v1/actresses", params={"page": page, "page_size": page_size})

    async def get_actress(self, actress_id: int) -> dict[str, Any]:
        """获取演员详情"""
        return await self._get(f"/api/v1/actresses/{actress_id}")

    async def get_actress_videos(self, actress_id: int, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取演员作品列表"""
        result = await self._get(
            f"/api/v1/actresses/{actress_id}/videos",
            params={"page": page, "page_size": page_size}
        )
        # 转换图片URL
        if "data" in result and isinstance(result["data"], list):
            result["data"] = [_transform_video_item(item) for item in result["data"]]
        return result

    # === 枚举数据 ===

    async def list_makers(self) -> list[dict]:
        """获取所有厂商"""
        return await self._get_list("/api/v1/makers")

    async def list_series(self) -> list[dict]:
        """获取所有系列"""
        return await self._get_list("/api/v1/series")

    async def list_categories(self) -> list[dict]:
        """获取所有题材"""
        return await self._get_list("/api/v1/categories")

    async def list_labels(self) -> list[dict]:
        """获取所有品牌"""
        return await self._get_list("/api/v1/labels")

    # === 统计 ===

    async def get_stats(self) -> dict[str, Any]:
        """获取统计数据"""
        return await self._get("/api/v1/stats")


# 全局单例
_info_client: InfoClient | None = None


def get_info_client() -> InfoClient:
    global _info_client
    if _info_client is None:
        from config import config
        javinfo_config = getattr(config, "javinfo", {})
        _info_client = InfoClient(
            api_url=javinfo_config.get("api_url", "http://localhost:8080"),
            timeout=javinfo_config.get("timeout", 30),
        )
    return _info_client
