from __future__ import annotations
import asyncio
import logging
import httpx
from typing import Any
from services import cache

logger = logging.getLogger(__name__)

# DMM/FANZA 图片基础URL
DMM_IMAGE_BASE_URL = "https://pics.dmm.co.jp"
# DMM 预览视频基础URL
DMM_SAMPLE_BASE_URL = "https://cc3001.dmm.co.jp"
PENDING_METADATA_VIDEO_TTL = 300


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


def _has_result_items(result: Any) -> bool:
    return isinstance(result, dict) and bool(result.get("data") or result.get("total_count"))


def _strip_metadata_fields(item: dict) -> dict:
    data = dict(item)
    for field in ("director",):
        data.pop(field, None)
    return data


def _has_enhancement_fields(item: dict | None) -> bool:
    if not isinstance(item, dict):
        return False
    summary = item.get("summary")
    if isinstance(summary, str) and summary.strip():
        return True
    return "score" in item and item.get("score") is not None


def _has_complete_enhancement_fields(item: dict | None) -> bool:
    if not isinstance(item, dict):
        return False
    summary = item.get("summary")
    return isinstance(summary, str) and bool(summary.strip()) and item.get("score") is not None


def _has_partial_enhancement_fields(item: dict | None) -> bool:
    return _has_enhancement_fields(item) and not _has_complete_enhancement_fields(item)


def _source_movie_id_for_enrichment(content_id: str, item: dict) -> str:
    for value in (
        item.get("dvd_id"),
        item.get("canonical_number"),
        item.get("content_id"),
        content_id,
    ):
        value = str(value or "").strip()
        if value:
            return value
    return ""


def _is_random_limit_error(exc: httpx.HTTPStatusError) -> bool:
    if exc.response.status_code != 400:
        return False
    try:
        payload = exc.response.json()
    except Exception:
        payload = {}
    message = str(payload.get("error") or payload.get("detail") or exc.response.text or "")
    return "random=1" in message


class InfoClient:
    """JavInfoApi HTTP 客户端"""

    def __init__(self, api_url: str = "http://localhost:18080", timeout: int = 30):
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
        """获取列表数据（单页），自动处理分页格式返回纯 list"""
        client = await self._get_client()
        response = await client.get(f"{self.api_url}{path}", params=params)
        response.raise_for_status()
        data = response.json()
        # 兼容分页格式 {data: [...], ...} 和纯数组格式 [...]
        if isinstance(data, dict):
            return data.get("data", [])
        return data if isinstance(data, list) else []

    async def _get_all_pages(self, path: str, page_size: int = 100) -> list[dict]:
        """获取所有分页数据，自动翻页合并"""
        all_items = []
        page = 1
        while True:
            params = {"page": page, "page_size": page_size}
            client = await self._get_client()
            response = await client.get(f"{self.api_url}{path}", params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            all_items.extend(items)
            # 检查是否还有下一页
            total_pages = data.get("total_pages", 1) if isinstance(data, dict) else 1
            if page >= total_pages or not items:
                break
            page += 1
        return all_items

    async def get_total_count(self, path: str) -> int:
        """Fetch total_count from a paginated JavInfoApi list endpoint."""
        data = await self._get(path, params={"page": 1, "page_size": 1})
        if isinstance(data, dict):
            if data.get("total_count") is not None:
                return int(data.get("total_count") or 0)
            items = data.get("data", [])
            return len(items) if isinstance(items, list) else 0
        return len(data) if isinstance(data, list) else 0

    def _auth_headers(self) -> dict[str, str]:
        """返回补全管理接口认证头（如果 token 已配置）"""
        from config import config
        token = config.supplement_admin_token
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def proxy_get(self, path: str, params: dict | None = None) -> dict:
        """代理 GET 请求，注入补全 token，不做图片转换和缓存"""
        client = await self._get_client()
        response = await client.get(
            f"{self.api_url}{path}",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def proxy_post(self, path: str, json_body: dict | None = None, params: dict | None = None) -> dict:
        """代理 POST 请求，注入补全 token，不做图片转换和缓存"""
        client = await self._get_client()
        response = await client.post(
            f"{self.api_url}{path}",
            json=json_body,
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def proxy_patch(self, path: str, json_body: dict | None = None) -> dict:
        """代理 PATCH 请求"""
        client = await self._get_client()
        response = await client.patch(
            f"{self.api_url}{path}",
            json=json_body,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def push_proxy_config(self, proxy_url: str) -> dict:
        """推送代理配置到 JavInfoApi"""
        return await self.proxy_patch("/api/v1/config", {"proxy_url": proxy_url})

    # === 视频相关 ===

    async def search_videos(
        self,
        q: str | None = None,
        content_id: str | None = None,
        dvd_id: str | None = None,
        maker_id: int | None = None,
        maker_name: str | None = None,
        series_id: int | None = None,
        series_name: str | None = None,
        actress_id: int | None = None,
        actress_name: str | None = None,
        category_id: int | None = None,
        category_name: str | None = None,
        label_id: int | None = None,
        label_name: str | None = None,
        site_id: int | None = None,
        year: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        runtime_min: int | None = None,
        runtime_max: int | None = None,
        release_date_from: str | None = None,
        release_date_to: str | None = None,
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
                  "label_id": label_id, "label_name": label_name, "site_id": site_id,
                  "year": year, "year_from": year_from, "year_to": year_to,
                  "runtime_min": runtime_min, "runtime_max": runtime_max,
                  "release_date_from": release_date_from, "release_date_to": release_date_to,
                  "service_code": service_code,
                  "page": page, "page_size": page_size}
        # content_id 映射到 JavInfoApi 的 dvd_id 字段
        # JavInfoApi 会同时匹配带横杠和不带横杠的版本
        # 例如输入 XRW-429 会匹配 XRW-429 和 XRW429
        if content_id:
            params["dvd_id"] = content_id
        elif dvd_id:
            params["dvd_id"] = dvd_id
        if random:
            params["random"] = random
            # 随机查询跳过缓存，每次直接请求 JavInfoApi 获取新的随机顺序
            try:
                result = await self._get("/api/v1/videos/search", {k: v for k, v in params.items() if v is not None})
            except httpx.HTTPStatusError as exc:
                if not _is_random_limit_error(exc):
                    raise
                fallback_params = {k: v for k, v in params.items() if v is not None and k != "random"}
                cached = cache.get_search(fallback_params, page)
                if cached is not None:
                    return cached
                result = await self._get("/api/v1/videos/search", fallback_params)
                if "data" in result and isinstance(result["data"], list):
                    result["data"] = [_transform_video_item(item) for item in result["data"]]
                if result.get("total_count", 0) > 0:
                    cache.set_search(fallback_params, page, result)
                return result
            if "data" in result and isinstance(result["data"], list):
                result["data"] = [_transform_video_item(item) for item in result["data"]]
            return result
        elif sort_by:
            # JavInfoApi expects "field:dir" format; if already contains ":" (from frontend format), pass as-is
            params["sort_by"] = sort_by if ':' in sort_by else f"{sort_by}:{sort_order or 'asc'}"
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
        cache_key = f"{normalized}:service:{service_code}" if service_code else normalized
        cached = cache.get_video(cache_key)
        if cached is not None:
            data = _strip_metadata_fields(cached)
            if _has_complete_enhancement_fields(data):
                return data
            if not _has_partial_enhancement_fields(data):
                cache.set_video(cache_key, data, ttl=PENDING_METADATA_VIDEO_TTL)
                self.queue_video_detail_enrichment(content_id, data)
                return data

            try:
                return await self._fetch_video_detail(content_id, normalized, cache_key, service_code)
            except Exception:
                cache.set_video(cache_key, data, ttl=PENDING_METADATA_VIDEO_TTL)
                self.queue_video_detail_enrichment(content_id, data)
                return data

        return await self._fetch_video_detail(content_id, normalized, cache_key, service_code)

    async def _fetch_video_detail(
        self,
        content_id: str,
        normalized: str,
        cache_key: str,
        service_code: str | None = None,
    ) -> dict[str, Any]:
        params = {}
        if service_code:
            params["service_code"] = service_code
        result = await self._get(f"/api/v1/videos/{normalized}", params=params or None)
        # 转换图片URL
        data = _strip_metadata_fields(_transform_video_item(result))
        cache_ttl = PENDING_METADATA_VIDEO_TTL if not _has_complete_enhancement_fields(data) else cache.DEFAULT_VIDEO_TTL
        cache.set_video(cache_key, data, ttl=cache_ttl)
        self.queue_video_detail_enrichment(content_id, data)
        return data

    def queue_video_detail_enrichment(self, content_id: str, data: dict[str, Any]) -> bool:
        """后台触发 JavInfoApi source=all 补全，当前详情响应不等待。"""
        if _has_complete_enhancement_fields(data):
            return False
        source_movie_id = _source_movie_id_for_enrichment(content_id, data)
        if not source_movie_id:
            return False

        async def run() -> None:
            try:
                await self.proxy_post(
                    "/api/v1/supplement/movies/detail/jobs",
                    params={"source": "all", "source_movie_id": source_movie_id},
                )
            except Exception as exc:
                logger.warning("Failed to queue JavInfoApi detail enrichment for %s: %s", source_movie_id, exc)

        asyncio.create_task(run())
        return True

    # === 演员相关 ===

    async def list_actresses(
        self,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
        has_valid_avatar: str | int | bool | None = None,
    ) -> dict[str, Any]:
        """获取演员列表（支持 q 关键词搜索）"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        if has_valid_avatar is not None:
            params["has_valid_avatar"] = has_valid_avatar
        return await self._get("/api/v1/actresses", params=params)

    async def get_actress(self, actress_id: int) -> dict[str, Any]:
        """获取演员详情"""
        return await self._get(f"/api/v1/actresses/{actress_id}")

    async def get_actress_videos(
        self,
        actress_id: int,
        page: int = 1,
        page_size: int = 20,
        include_supplement: str | None = None,
        service_code: str | None = None,
        year: int | None = None,
        sort_by: str | None = None,
    ) -> dict[str, Any]:
        """获取演员作品列表（支持补全层查询）"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if include_supplement:
            params["include_supplement"] = include_supplement
        if service_code:
            params["service_code"] = service_code
        if year:
            params["year"] = year
        if sort_by:
            params["sort_by"] = sort_by
        result = await self._get(
            f"/api/v1/actresses/{actress_id}/videos",
            params=params,
        )
        if include_supplement and not _has_result_items(result):
            fallback_params = dict(params)
            fallback_params.pop("include_supplement", None)
            result = await self._get(
                f"/api/v1/actresses/{actress_id}/videos",
                params=fallback_params,
            )
        # 转换图片URL
        if "data" in result and isinstance(result["data"], list):
            result["data"] = [_transform_video_item(item) for item in result["data"]]
        return result

    # === 枚举数据 ===

    async def list_makers(self, q: str | None = None) -> list[dict]:
        """获取所有厂商（缓存24小时，支持 q 搜索）"""
        if q:
            # 搜索不走缓存
            result = await self._get("/api/v1/makers", params={"q": q, "page_size": 100})
            return result.get("data", []) if isinstance(result, dict) else result
        cached = cache.get_enum_list("makers")
        if cached is not None:
            return cached
        data = await self._get_all_pages("/api/v1/makers")
        cache.set_enum_list("makers", data)
        return data

    async def list_series(self, q: str | None = None) -> list[dict]:
        """获取所有系列（缓存24小时，支持 q 搜索）"""
        if q:
            result = await self._get("/api/v1/series", params={"q": q, "page_size": 100})
            return result.get("data", []) if isinstance(result, dict) else result
        cached = cache.get_enum_list("series")
        if cached is not None:
            return cached
        data = await self._get_all_pages("/api/v1/series")
        cache.set_enum_list("series", data)
        return data

    async def list_series_page(self, q: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取系列分页列表，避免为推荐页拉取完整系列枚举。"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        result = await self._get("/api/v1/series", params=params)
        if isinstance(result, dict):
            return result
        items = result if isinstance(result, list) else []
        return {
            "data": items,
            "page": page,
            "page_size": page_size,
            "total_count": len(items),
            "total_pages": 1,
        }

    async def list_categories(self, q: str | None = None) -> list[dict]:
        """获取所有题材（缓存24小时，支持 q 搜索）"""
        if q:
            result = await self._get("/api/v1/categories", params={"q": q, "page_size": 100})
            return result.get("data", []) if isinstance(result, dict) else result
        cached = cache.get_enum_list("categories")
        if cached is not None:
            return cached
        data = await self._get_all_pages("/api/v1/categories")
        cache.set_enum_list("categories", data)
        return data

    async def list_labels(self, q: str | None = None) -> list[dict]:
        """获取所有品牌（缓存24小时，支持 q 搜索）"""
        if q:
            result = await self._get("/api/v1/labels", params={"q": q, "page_size": 100})
            return result.get("data", []) if isinstance(result, dict) else result
        cached = cache.get_enum_list("labels")
        if cached is not None:
            return cached
        data = await self._get_all_pages("/api/v1/labels")
        cache.set_enum_list("labels", data)
        return data

    # === 批量接口 ===

    async def batch_get_videos(self, ids: list[str]) -> list[dict]:
        """批量获取视频详情（最多100个 content_id）"""
        if not ids:
            return []
        # 分批，每批最多100
        results = []
        for i in range(0, len(ids), 100):
            batch = ids[i:i + 100]
            client = await self._get_client()
            resp = await client.post(f"{self.api_url}/api/v1/videos/batch", json={"ids": batch})
            resp.raise_for_status()
            items = resp.json()
            if isinstance(items, list):
                results.extend([_transform_video_item(item) for item in items])
        return results

    async def batch_lookup_by_dvd_id(self, dvd_ids: list[str]) -> dict[str, dict]:
        """批量番号查找（最多100个 dvd_id），返回 {dvd_id: video} 映射"""
        if not dvd_ids:
            return {}
        results = {}
        for i in range(0, len(dvd_ids), 100):
            batch = dvd_ids[i:i + 100]
            client = await self._get_client()
            resp = await client.post(f"{self.api_url}/api/v1/videos/lookup", json={"dvd_ids": batch})
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                for k, v in data.items():
                    results[k] = _transform_video_item(v)
        return results

    async def batch_get_actress_videos(
        self, actress_ids: list[int], page: int = 1, page_size: int = 20
    ) -> dict[str, dict]:
        """批量获取演员作品（最多20个演员），返回 {actress_id: {total_count, videos}}"""
        if not actress_ids:
            return {}
        results = {}
        for i in range(0, len(actress_ids), 20):
            batch = actress_ids[i:i + 20]
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_url}/api/v1/actresses/batch_videos",
                json={"ids": batch, "page": page, "page_size": page_size},
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                for aid, info in data.items():
                    if isinstance(info, dict) and "videos" in info:
                        info["videos"] = [_transform_video_item(v) for v in info["videos"]]
                    results[aid] = info
        return results

    # === 辅助数据 (v1.2.0) ===

    async def list_directors(self, q: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取导演列表（支持 q 搜索）"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        return await self._get("/api/v1/directors", params=params)

    async def list_actors(self, q: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取男演员列表（支持 q 搜索）"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        return await self._get("/api/v1/actors", params=params)

    async def list_authors(self, q: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """获取作者列表（支持 q 搜索）"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        return await self._get("/api/v1/authors", params=params)

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
        _info_client = InfoClient(
            api_url=config.javinfo_api_url,
            timeout=config.javinfo_timeout,
        )
    return _info_client


def reset_info_client() -> None:
    """config 更新后调用，重置 client 的 api_url（下次请求生效）"""
    global _info_client
    if _info_client is not None:
        from config import config
        _info_client.api_url = config.javinfo_api_url.rstrip("/")
        _info_client.timeout = config.javinfo_timeout
