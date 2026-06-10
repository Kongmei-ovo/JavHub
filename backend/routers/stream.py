from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Any, AsyncIterator, Optional
from urllib.parse import urljoin, quote, urlparse
import ipaddress
import httpx
import json
import re
import logging
import socket

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])

# ── SSRF 防护 ─────────────────────────────────────────────────────
# 源站 + 它们对应的 m3u8 CDN。新加源时要么追加到这个集合(代码里),
# 要么走 config.stream.extra_allowed_domains(运维不动代码)。
ALLOWED_STREAM_DOMAINS = {
    # 源站本身
    "jable.tv", "missav.ai", "memojav.com", "kanav.info", "hohoj.tv", "rou.video",
    # m3u8 CDN
    "surrit.com",          # missav
    "mushroomtrack.com",   # jable
    "ggjav.com",           # hohoj
    "11yun.space",         # kanav
}

# rou.video 的 m3u8 CDN 是 rn{NNN}.xyz 的滚动域名(rn244 / rn245 / rn246 / rn247 …),
# 单独枚举挂不住,用正则覆盖整族。新发现的滚动域命名规律也加这里。
ALLOWED_STREAM_DOMAIN_PATTERNS = (
    re.compile(r"^(?:[\w-]+\.)?rn\d+\.xyz$"),  # rou.video 系列 CDN
)

STREAM_REFERER_BY_DOMAIN = {
    "surrit.com": "https://missav.ai/",
    "ggjav.com": "https://hohoj.tv/",
    "mushroomtrack.com": "https://jable.tv/",
    "11yun.space": "https://kanav.info/",
}

# rou.video 的 CDN 滚动域名,Referer 要带回 rou.video
STREAM_REFERER_BY_PATTERN = (
    (re.compile(r"^(?:[\w-]+\.)?rn\d+\.xyz$"), "https://rou.video/"),
)

PROXY_FAKE_IP_NETWORKS = (
    ipaddress.ip_network("198.18.0.0/15"),
)

MAX_REDIRECTS = 5


def _is_allowed_stream_domain(hostname: str) -> bool:
    # 1) 内置常量(含子域)
    for domain in ALLOWED_STREAM_DOMAINS:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return True
    # 2) 内置正则(覆盖 rn\d+.xyz 之类滚动 CDN)
    for pattern in ALLOWED_STREAM_DOMAIN_PATTERNS:
        if pattern.match(hostname):
            return True
    # 3) config.stream.extra_allowed_domains 追加(运维侧热加,不动代码)
    try:
        from config import Config
        for extra in Config().stream_extra_allowed_domains:
            if hostname == extra or hostname.endswith(f".{extra}"):
                return True
    except Exception:
        pass
    return False


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    )


def _is_proxy_fake_ip(ip: ipaddress._BaseAddress) -> bool:
    return any(ip in network for network in PROXY_FAKE_IP_NETWORKS)


def _resolve_host_ips(hostname: str) -> set[ipaddress._BaseAddress]:
    try:
        return {ipaddress.ip_address(hostname)}
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(400, "无法解析 URL 主机")

    addresses = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        try:
            addresses.add(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    if not addresses:
        raise HTTPException(400, "无法解析 URL 主机")
    return addresses


def _validate_proxy_url(url: str) -> str:
    """校验代理 URL，防止 SSRF。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "仅允许 http/https 协议")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HTTPException(400, "无效的 URL")
    hostname = hostname.rstrip(".")
    if not _is_allowed_stream_domain(hostname):
        raise HTTPException(403, "URL 域名不在允许列表")
    for ip in _resolve_host_ips(hostname):
        if _is_blocked_ip(ip) and not _is_proxy_fake_ip(ip):
            raise HTTPException(403, "不允许访问私有网络")
    return parsed.geturl()


def _referer_for_stream_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    for domain, referer in STREAM_REFERER_BY_DOMAIN.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            return referer
    for pattern, referer in STREAM_REFERER_BY_PATTERN:
        if pattern.match(hostname):
            return referer
    return "/".join(url.split("/")[:3]) + "/"


async def _fetch_validated_url(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> httpx.Response:
    current_url = _validate_proxy_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        resp = await client.get(current_url, headers=headers, follow_redirects=False)
        if resp.is_redirect:
            location = resp.headers.get("location")
            if not location:
                raise HTTPException(status_code=502, detail="上游重定向无效")
            current_url = _validate_proxy_url(urljoin(str(resp.url), location))
            continue
        return resp
    raise HTTPException(status_code=502, detail="上游重定向次数过多")


@router.get("/proxy")
async def proxy_stream(url: str = Query(..., description="要代理的 m3u8/ts URL")):
    """代理 m3u8 和 ts，m3u8 内容中的相对 URL 会被改写为代理地址"""
    url = _validate_proxy_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": _referer_for_stream_url(url),
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await _fetch_validated_url(client, url, headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="上游请求失败")

            content_type = resp.headers.get("content-type", "application/octet-stream")
            body = resp.content

            # m3u8 识别: 不能只看后缀(rou.video 把 m3u8 命名为 index.jpg 反盗链),
            # 也不能只信 content-type(rn{N}.xyz 跨站访问会返回 text/plain 甚至
            # image/jpeg)。直接看 body 是不是以 #EXTM3U 开头 — HLS spec 强制头。
            looks_like_m3u8 = (
                body.lstrip()[:7] == b"#EXTM3U"
                or url.endswith(".m3u8")
                or "mpegurl" in content_type.lower()
            )
            if looks_like_m3u8:
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


@router.get("/sources/{content_id}")
async def stream_sources(content_id: str) -> StreamingResponse:
    """SSE 流式返回所有源站的搜索结果,谁先出谁先发,前端边收边渲染。

    每条 event: data: {"source", "status", "elapsed_ms", "m3u8_url"?, "title"?, "page_url"?, "detail"?}
    结束 event: data: {"source": "_done", "status": "done"}
    """
    from sources.m3u8_source import M3U8Source

    async def event_stream() -> AsyncIterator[bytes]:
        source = M3U8Source()
        async for item in source.stream_sources(content_id):
            if item.get("_keepalive"):
                yield b": keep-alive\n\n"
                continue
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n".encode("utf-8")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 防 nginx 缓冲
        },
    )


@router.get("/{content_id}")
async def get_stream_url(content_id: str) -> dict[str, Any]:
    """获取影片的 m3u8 播放地址,返回时附带每个源站的尝试明细供前端展示(单源·向后兼容)。"""
    from sources.m3u8_source import M3U8Source
    source = M3U8Source()
    result, attempts = await source.search_m3u8(content_id)
    if not result:
        # FastAPI 序列化 dict 到 response.detail,前端可读 attempts 给精确提示
        raise HTTPException(
            status_code=404,
            detail={"message": "未找到播放地址", "attempts": attempts},
        )
    return {"data": result, "attempts": attempts}


class TransferRequest(BaseModel):
    m3u8_url: str
    content_id: str
    title: Optional[str] = ""


@router.post("/{content_id}/transfer")
async def transfer_to_cloud(content_id: str, req: TransferRequest) -> dict[str, Any]:
    """m3u8 转存到云盘（通过 AList 上传）"""
    # TODO: 实现 m3u8 下载并上传到 AList 的逻辑
    raise HTTPException(status_code=501, detail="转存功能尚未实现")
