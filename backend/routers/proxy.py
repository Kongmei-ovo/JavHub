from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import httpx
from config import config

router = APIRouter(prefix="/api/proxy", tags=["proxy"])


def _get_httpx_proxies() -> Optional[dict]:
    """根据配置返回 httpx proxies dict"""
    if not config.proxy_enabled:
        return None
    proxies = {}
    http_url = config.proxy_http_url
    https_url = config.proxy_https_url
    if http_url:
        proxies["http://"] = http_url
    if https_url:
        proxies["https://"] = https_url
    return proxies if proxies else None


@router.get("/image")
async def proxy_image(url: str = Query(...)):
    """代理图片请求，避免CORS问题"""
    proxies = _get_httpx_proxies()
    try:
        async with httpx.AsyncClient(timeout=30, proxies=proxies) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                resp.aiter_bytes(),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                }
            )
    except Exception as e:
        return StreamingResponse(
            iter([b""]),
            media_type="image/png",
            status_code=500
        )
