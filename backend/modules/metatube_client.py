from __future__ import annotations
import httpx
from typing import Any, Optional

# metatube SDK client

_cache: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _cache
    if _cache is None:
        _cache = httpx.AsyncClient(timeout=30, trust_env=False)
    return _cache


def _base_url() -> str:
    from config import config
    mt = getattr(config, "metatube", {})
    host = mt.get("host", "localhost")
    port = mt.get("port", 8081)
    return f"http://{host}:{port}"


def _token() -> str | None:
    from config import config
    mt = getattr(config, "metatube", {})
    return mt.get("token") or None


async def _get(path: str, params: dict | None = None) -> dict[str, Any]:
    client = _get_client()
    url = f"{_base_url()}{path}"
    headers = {}
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


async def close():
    global _cache
    if _cache is not None:
        await _cache.aclose()
        _cache = None


async def get_movie(content_id: str, provider: str = "fanza") -> Optional[dict[str, Any]]:
    """
    获取影片详情，返回 { summary, director, score, provider, review_count }。
    取不到返回 None。
    """
    # 先尝试用 content_id 裸码查找
    for pid in [_normalize_content_id(content_id), content_id]:
        try:
            data = await _get(f"/v1/movies/{provider}/{pid}")
            if "data" in data and data["data"]:
                m = data["data"]
                return {
                    "summary": m.get("summary") or "",
                    "director": m.get("director") or "",
                    "score": m.get("score") or 0,
                    "provider": m.get("provider") or provider,
                }
        except Exception:
            pass
        # fallback 搜索获取 provider
        try:
            search = await _get("/v1/movies/search", {"q": pid})
            if "data" in search and search["data"]:
                for item in search["data"]:
                    if item.get("id", "").replace("-", "").lower() == pid.replace("-", "").lower():
                        prov = item.get("provider", "").lower()
                        # 用对应 provider 拿详情
                        movie_data = await _get(f"/v1/movies/{prov}/{item['id']}")
                        if "data" in movie_data and movie_data["data"]:
                            m = movie_data["data"]
                            return {
                                "summary": m.get("summary") or "",
                                "director": m.get("director") or "",
                                "score": m.get("score") or 0,
                                "provider": m.get("provider") or prov,
                            }
        except Exception:
            pass
    return None


def _normalize_content_id(content_id: str) -> str:
    """将 content_id 补零到5位数字格式，如 miaa784 → miaa00784，MIAA-784 → miaa00784"""
    import re
    # 先去掉横杠等分隔符
    stripped = content_id.replace("-", "").replace("_", "")
    m = re.match(r'^([a-z]+)(\d+)$', stripped, re.IGNORECASE)
    if not m:
        return content_id
    prefix, num = m.group(1).lower(), m.group(2)
    # 只有字母部分 < 5 位才补零（TK 系列不补）
    if len(prefix) < 5:
        return f"{prefix}{int(num):05d}"
    return stripped
