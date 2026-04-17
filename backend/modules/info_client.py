from __future__ import annotations
import httpx
from typing import Any
from services import cache

# DMM/FANZA 图片基础URL
DMM_IMAGE_BASE_URL = "https://pics.dmm.co.jp"
# DMM 预览视频基础URL
DMM_SAMPLE_BASE_URL = "https://cc3001.dmm.co.jp"


def _transform_jacket_url(jacket_path: str | None) -> str | None:
    """将相对路径转换为完整的DMM图片URL"""
    if not jacket_path:
        return None
    if jacket_path.startswith("http"):
        return jacket_path
    jacket_path = jacket_path.lstrip("/")
    return f"{DMM_IMAGE_BASE_URL}/{jacket_path}.jpg"


def _transform_sample_url(sample_path: str | None) -> str | None:
    """将相对路径转换为完整的DMM预览视频URL"""
    if not sample_path:
        return None
    if sample_path.startswith("http"):
        return sample_path
    sample_path = sample_path.lstrip("/")
    return f"{DMM_SAMPLE_BASE_URL}/{sample_path}"


def _transform_video_item(item: dict) -> dict:
    """转换视频项的图片URL和预览视频URL为完整路径，统一 content_id 命名"""
    if not item:
        return item
    item = dict(item)
    # JavInfoApi 返回 dvd_id，内部统一规范化为 content_id
    if "dvd_id" in item and "content_id" not in item:
        item["content_id"] = item.pop("dvd_id")
    if "jacket_thumb_url" in item:
        item["jacket_thumb_url"] = _transform_jacket_url(item.get("jacket_thumb_url"))
    if "jacket_full_url" in item:
        item["jacket_full_url"] = _transform_jacket_url(item.get("jacket_full_url"))
    if "sample_url" in item:
        item["sample_url"] = _transform_sample_url(item.get("sample_url"))
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
        year: int | None = None,
        service_code: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        random: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """搜索视频（结果缓存10分钟，有结果才缓存）"""
        # 多tag支持：空格分隔的 category_name 拆成重复参数实现 AND 过滤
        cat_names: str | list[str] | None = None
        if category_name:
            tags = category_name.split()
            cat_names = tags if len(tags) > 1 else tags[0]
        params: dict[str, Any] = {"q": q, "maker_id": maker_id, "maker_name": maker_name,
                  "series_id": series_id, "series_name": series_name, "actress_id": actress_id,
                  "actress_name": actress_name, "category_id": category_id, "category_name": cat_names,
                  "year": year, "service_code": service_code,
                  "page": page, "page_size": page_size}
        if random:
            params["random"] = random
            # 随机查询跳过缓存，每次直接请求 JavInfoApi 获取新的随机顺序
            result = await self._get("/api/v1/videos/search", {k: v for k, v in params.items() if v is not None})
            if "data" in result and isinstance(result["data"], list):
                result["data"] = [_transform_video_item(item) for item in result["data"]]
            return result
        elif sort_by:
            # JavInfoApi expects "field:dir" format; if already contains ":" (from frontend format), pass as-is
            params["sort_by"] = sort_by if ':' in sort_by else f"{sort_by}:{sort_order or 'asc'}"
        # content_id 映射到 JavInfoApi 的 dvd_id 字段（JavInfoApi 的 dvd_id = 小写 content_id）
        if content_id:
            params["dvd_id"] = content_id.lower()
        cached = cache.get_search({k: v for k, v in params.items() if v is not None}, page)
        if cached is not None:
            return cached
        result = await self._get("/api/v1/videos/search", {k: v for k, v in params.items() if v is not None})
        # 转换图片URL
        if "data" in result and isinstance(result["data"], list):
            result["data"] = [_transform_video_item(item) for item in result["data"]]
        # 只缓存有结果的搜索，空结果不缓存（避免"搜过=永远没有"）
        if result.get("total_count", 0) > 0:
            cache.set_search({k: v for k, v in params.items() if v is not None}, page, result)
        return result

    async def list_videos(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取视频列表"""
        result = await self._get("/api/v1/videos", params={"page": page, "page_size": page_size})
        # 转换图片URL
        if "data" in result and isinstance(result["data"], list):
            result["data"] = [_transform_video_item(item) for item in result["data"]]
        return result

    async def get_video(self, content_id: str, service_code: str | None = None) -> dict[str, Any]:
        """获取视频详情（缓存24小时）"""
        # JavInfoApi 的 content_id 保留原始格式（部分含下划线如 h_1330gtrp004r）
        normalized = content_id.replace("-", "").lower()
        cached = cache.get_video(normalized)
        if cached is not None:
            return cached
        params = {}
        if service_code:
            params["service_code"] = service_code
        result = await self._get(f"/api/v1/videos/{normalized}", params=params or None)
        # 转换图片URL
        data = _transform_video_item(result)
        # 用 metatube 补全 summary / director / score（取不到不影响主流程）
        try:
            from modules.metatube_client import get_movie as mt_get_movie
            mt_data = await mt_get_movie(content_id)
            if mt_data:
                if mt_data.get("summary"):
                    data["summary"] = mt_data["summary"]
                if mt_data.get("director"):
                    data["director"] = mt_data["director"]
                data["score"] = mt_data.get("score", 0)
                data["meta_provider"] = mt_data.get("provider", "")
        except Exception:
            pass
        cache.set_video(normalized, data)
        return data

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
        """获取所有厂商（缓存24小时）"""
        cached = cache.get_enum_list("makers")
        if cached is not None:
            return cached
        data = await self._get_list("/api/v1/makers")
        cache.set_enum_list("makers", data)
        return data

    async def list_series(self) -> list[dict]:
        """获取所有系列（缓存24小时）"""
        cached = cache.get_enum_list("series")
        if cached is not None:
            return cached
        data = await self._get_list("/api/v1/series")
        cache.set_enum_list("series", data)
        return data

    async def list_categories(self) -> list[dict]:
        """获取所有题材（缓存24小时）"""
        cached = cache.get_enum_list("categories")
        if cached is not None:
            return cached
        data = await self._get_list("/api/v1/categories")
        cache.set_enum_list("categories", data)
        return data

    async def list_labels(self) -> list[dict]:
        """获取所有品牌（缓存24小时）"""
        cached = cache.get_enum_list("labels")
        if cached is not None:
            return cached
        data = await self._get_list("/api/v1/labels")
        cache.set_enum_list("labels", data)
        return data

    # === 统计 ===

    async def get_stats(self) -> dict[str, Any]:
        """获取统计数据"""
        return await self._get("/api/v1/stats")


# 全局单例（复用 httpx client，只把 api_url 做成动态读配置）
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


def reset_info_client() -> None:
    """config 更新后调用，重置 client 的 api_url（下次请求生效）"""
    global _info_client
    if _info_client is not None:
        from config import config
        javinfo_config = getattr(config, "javinfo", {})
        _info_client.api_url = javinfo_config.get("api_url", "http://localhost:8080")
        _info_client.timeout = javinfo_config.get("timeout", 30)
