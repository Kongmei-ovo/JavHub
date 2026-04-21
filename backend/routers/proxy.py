from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from config import config

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

# 允许代理的图片域名白名单（防 SSRF）
ALLOWED_IMAGE_DOMAINS = {
    "pics.dmm.co.jp",
    "javbus.com",
    "javcdn.com",
    "javlink.com",
    "dmm.co.jp",
    "amazonaws.com",
}


def _get_allowed_domains() -> set:
    """获取允许的图片域名白名单（包含动态添加的 Emby 域名）"""
    domains = set(ALLOWED_IMAGE_DOMAINS)
    # 动态添加 Emby 域名
    emby_cfg = getattr(config, "emby", {})
    emby_url = emby_cfg.get("api_url", "")
    if emby_url:
        from urllib.parse import urlparse
        parsed = urlparse(emby_url)
        if parsed.netloc:
            domains.add(parsed.netloc.lower())
    return domains


def _is_url_allowed(url: str) -> bool:
    """验证 URL 域名是否在白名单内"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        allowed = _get_allowed_domains()
        return any(domain.endswith(allowed_domain) or domain == allowed_domain for allowed_domain in allowed)
    except Exception:
        return False


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
    if not _is_url_allowed(url):
        raise HTTPException(status_code=403, detail="URL not allowed")
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
