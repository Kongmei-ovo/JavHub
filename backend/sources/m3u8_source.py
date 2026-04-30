from __future__ import annotations

import httpx
import re
import logging
from typing import Optional
from urllib.parse import unquote

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class M3U8Source:
    """m3u8 在线播放源 — 多站点聚合，参考 NASSAV"""

    name: str = "m3u8"

    async def search_m3u8(self, content_id: str) -> Optional[dict]:
        """搜索某番号的 m3u8 播放地址

        按权重依次尝试多个站点，返回第一个成功的结果。

        Returns:
            {"m3u8_url": "...", "title": "...", "source": "..."} or None
        """
        avid = content_id.upper().replace("_", "-")
        # 按权重排序的站点列表
        sites = [
            ("jable", self._search_jable),
            ("missav", self._search_missav),
            ("memo", self._search_memo),
            ("kanav", self._search_kanav),
            ("hohoj", self._search_hohoj),
        ]
        for name, search_fn in sites:
            try:
                result = await search_fn(avid)
                if result:
                    result["source"] = name
                    logger.info(f"m3u8 found for {avid} on {name}: {result['m3u8_url'][:80]}...")
                    return result
            except Exception as e:
                logger.warning(f"m3u8 search failed on {name} for {avid}: {e}")
                continue
        return None

    # ── Jable (weight 1500) ──────────────────────────────────────

    async def _search_jable(self, avid: str) -> Optional[dict]:
        """jable.tv — 直接从页面 JS 提取 hlsUrl"""
        url = f"https://jable.tv/videos/{avid.lower()}/"
        headers = {**HEADERS, "Referer": "https://jable.tv/"}

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            html = resp.text

        m = re.search(r"var hlsUrl\s*=\s*'(https?://[^']+)'", html)
        if not m:
            return None

        title_m = re.search(r"<title>(.*?)</title>", html)
        title = title_m.group(1).strip() if title_m else avid

        return {"m3u8_url": m.group(1), "title": title}

    # ── MissAV (weight 1000) ─────────────────────────────────────

    async def _search_missav(self, avid: str) -> Optional[dict]:
        """missav.ai — UUID 提取 → surrit.com master playlist → 最高画质"""
        urls = [
            f"https://missav.ai/cn/{avid.lower()}-chinese-subtitle",
            f"https://missav.ai/cn/{avid.lower()}-uncensored-leak",
            f"https://missav.ai/cn/{avid.lower()}",
            f"https://missav.ai/dm13/cn/{avid.lower()}",
        ]
        headers = {**HEADERS, "Referer": "https://missav.ai/"}

        html = None
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200 and "m3u8" in resp.text:
                        html = resp.text
                        break
                except Exception:
                    continue

        if not html:
            return None

        # 从混淆 JS 中提取 UUID
        m = re.search(r"m3u8\|([a-f0-9\|]+)\|com\|surrit\|https\|video", html)
        if not m:
            return None

        parts = m.group(1).split("|")
        uuid = "-".join(reversed(parts))
        master_url = f"https://surrit.com/{uuid}/playlist.m3u8"

        # 获取 master playlist，选最高画质
        m3u8_url = await self._get_highest_quality_m3u8(master_url, headers)
        if not m3u8_url:
            return None

        title_m = re.search(r"<title>(.*?)</title>", html)
        title = title_m.group(1).strip() if title_m else avid

        return {"m3u8_url": m3u8_url, "title": title}

    async def _get_highest_quality_m3u8(self, master_url: str, headers: dict) -> Optional[str]:
        """解析 master playlist，返回最高画质的 stream URL"""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(master_url, headers=headers)
            if resp.status_code != 200:
                return None
            content = resp.text

        best_bw = 0
        best_url = None
        lines = content.strip().split("\n")
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF:"):
                bw_m = re.search(r"BANDWIDTH=(\d+)", line)
                if bw_m:
                    bw = int(bw_m.group(1))
                    if bw > best_bw and i + 1 < len(lines):
                        best_bw = bw
                        stream_path = lines[i + 1].strip()
                        if stream_path.startswith("http"):
                            best_url = stream_path
                        else:
                            # 相对路径
                            base = master_url.rsplit("/", 1)[0]
                            best_url = f"{base}/{stream_path}"

        return best_url

    # ── Memo (weight 600) ────────────────────────────────────────

    async def _search_memo(self, avid: str) -> Optional[dict]:
        """memojav.com — API 调用，返回 URL-encoded m3u8"""
        url = f"https://memojav.com/hls/get_video_info.php?id={avid.lower()}&sig=NTg1NTczNg&sts=7264825"
        headers = {**HEADERS, "Referer": "https://memojav.com/"}

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            text = resp.text

        m = re.search(r'"url":"(https?%3A%2F%2F[^"]+)"', text)
        if not m:
            return None

        m3u8_url = unquote(m.group(1))
        return {"m3u8_url": m3u8_url, "title": avid}

    # ── KanAV (weight 490) ───────────────────────────────────────

    async def _search_kanav(self, avid: str) -> Optional[dict]:
        """kanav.info — 搜索 → 播放页 → base64+URL 解码 m3u8"""
        import base64

        search_url = f"https://kanav.info/index.php/vod/search.html?wd={avid.lower()}&by=time_add"
        headers = {**HEADERS, "Referer": "https://kanav.info/"}

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # 搜索
            resp = await client.get(search_url, headers=headers)
            if resp.status_code != 200:
                return None

            m = re.search(r'href="(/index\.php/vod/play[^"]*\.html)"', resp.text)
            if not m:
                return None

            # 播放页
            play_url = f"https://kanav.info{m.group(1)}"
            resp2 = await client.get(play_url, headers=headers)
            if resp2.status_code != 200:
                return None
            html = resp2.text

        m2 = re.search(r'"url":"([A-Za-z0-9+/=]*)"', html)
        if not m2:
            return None

        try:
            decoded = base64.b64decode(m2.group(1)).decode("utf-8")
            m3u8_url = unquote(decoded)
        except Exception:
            return None

        return {"m3u8_url": m3u8_url, "title": avid}

    # ── HohoJ (weight 400) ───────────────────────────────────────

    async def _search_hohoj(self, avid: str) -> Optional[dict]:
        """hohoj.tv — 搜索 → 嵌入页 → videoSrc"""
        search_url = f"https://hohoj.tv/search?text={avid.lower()}"
        headers = {**HEADERS, "Referer": "https://hohoj.tv/"}

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # 搜索
            resp = await client.get(search_url, headers=headers)
            if resp.status_code != 200:
                return None

            m = re.search(r'[?&]id=(\d+)', resp.text)
            if not m:
                return None

            video_id = m.group(1)

            # 嵌入页
            embed_url = f"https://hohoj.tv/embed?id={video_id}"
            embed_headers = {
                **headers,
                "Referer": f"https://hohoj.tv/video?id={video_id}",
            }
            resp2 = await client.get(embed_url, headers=embed_headers)
            if resp2.status_code != 200:
                return None
            html = resp2.text

        m2 = re.search(r'var videoSrc\s*=\s*"([^"]+)"', html)
        if not m2:
            return None

        return {"m3u8_url": m2.group(1), "title": avid}
