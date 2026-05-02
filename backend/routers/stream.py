from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any, Optional
from urllib.parse import urljoin, quote, urlparse
import ipaddress
import httpx
import re
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])

# ── SSRF 防护 ─────────────────────────────────────────────────────

ALLOWED_STREAM_DOMAINS = {
    "jable.tv", "missav.ai", "surrit.com", "memojav.com",
    "kanav.info", "hohoj.tv",
}

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"}


def _validate_proxy_url(url: str):
    """校验代理 URL，防止 SSRF（仅拦截私有/环路/链路本地 IP）"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "仅允许 http/https 协议")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HTTPException(400, "无效的 URL")
    if hostname in BLOCKED_HOSTS:
        raise HTTPException(403, "不允许访问内部地址")
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(403, "不允许访问私有网络")
    except ValueError:
        pass  # 域名而非 IP


@router.get("/proxy")
async def proxy_stream(url: str = Query(..., description="要代理的 m3u8/ts URL")):
    """代理 m3u8 和 ts，m3u8 内容中的相对 URL 会被改写为代理地址"""
    _validate_proxy_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": "/".join(url.split("/")[:3]) + "/",
    }
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="上游请求失败")

            content_type = resp.headers.get("content-type", "application/octet-stream")
            body = resp.content

            # m3u8: 重写相对路径为代理绝对路径
            if url.endswith(".m3u8") or "mpegurl" in content_type.lower():
                content_type = "application/vnd.apple.mpegurl"
                text = body.decode("utf-8", errors="replace")
                base_url = url.rsplit("/", 1)[0] + "/"

                proxy_prefix = "/api/v1/stream/proxy?url="

                def rewrite_uri(m):
                    raw = m.group(1)
                    abs_url = urljoin(base_url, raw)
                    return f'URI="{proxy_prefix}{quote(abs_url, safe="")}"'

                def rewrite_line(line):
                    stripped = line.strip()
                    # 改写 #EXT-X-KEY 等标签中的 URI="..."
                    if 'URI="' in stripped:
                        stripped = re.sub(r'URI="([^"]+)"', rewrite_uri, stripped)
                    if not stripped or stripped.startswith("#"):
                        return stripped
                    abs_url = urljoin(base_url, stripped)
                    return f"{proxy_prefix}{quote(abs_url, safe='')}"

                lines = text.strip().split("\n")
                rewritten = "\n".join(rewrite_line(l) for l in lines)
                body = rewritten.encode("utf-8")
            elif url.endswith(".ts"):
                content_type = "video/mp2t"

            return Response(
                content=body,
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache",
                },
            )
    except httpx.RequestError as e:
        logger.error(f"Proxy request failed for {urlparse(url).hostname}: {e}")
        raise HTTPException(status_code=502, detail="代理请求失败")


@router.get("/{content_id}")
async def get_stream_url(content_id: str) -> dict[str, Any]:
    """获取影片的 m3u8 播放地址"""
    from sources.m3u8_source import M3U8Source
    source = M3U8Source()
    result = await source.search_m3u8(content_id)
    if not result:
        raise HTTPException(status_code=404, detail="未找到播放地址")
    return {"data": result}


class TransferRequest(BaseModel):
    m3u8_url: str
    content_id: str
    title: Optional[str] = ""


@router.post("/{content_id}/transfer")
async def transfer_to_cloud(content_id: str, req: TransferRequest) -> dict[str, Any]:
    """m3u8 转存到云盘（通过 AList 上传）"""
    # TODO: 实现 m3u8 下载并上传到 AList 的逻辑
    raise HTTPException(status_code=501, detail="转存功能尚未实现")
