from __future__ import annotations

import asyncio
import base64
import httpx
import json
import re
import logging
import time
from typing import AsyncIterator, Optional, Tuple
from urllib.parse import unquote

from config import Config
from services.cache import _get_json_async, _set_json_async
from services.cf_solver import fetch_with_cf_solver

# 命中过的源 cache 10 分钟,复看秒回;不 cache no_result,免得上游后收录我们还死认空
_STREAM_CACHE_TTL = 600

# FlareSolverr 的同一浏览器 session 必须串行使用。给次要 CF 源一个很短的
# 启动错峰，确保最常命中的 jable 先拿到浏览器；仍会并发探测所有来源，
# 不改变来源、命中和画质逻辑。
_STREAM_SOURCE_START_DELAY_SECONDS = {
    "missav": 0.25,
    "kanav": 0.5,
}

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _proxy() -> Optional[str]:
    proxy = Config().stream_proxy.strip()
    return proxy or None


class M3U8Source:
    """m3u8 在线播放源 — 多站点聚合，参考 NASSAV"""

    name: str = "m3u8"

    async def search_m3u8(
        self, content_id: str
    ) -> Tuple[Optional[dict], list[dict]]:
        """搜索某番号的 m3u8 播放地址。

        按"速度+命中率"依次尝试多个站点,返回第一个成功的结果 + 全部尝试明细。
        rou.video 覆盖广且无 CF 几秒就出结果,放最优先;jable/missav 走 FlareSolverr
        解 CF 比较慢,作 fallback。memo 已移除:get_video_info.php 永久返回
        success:false/type:deleted,是上游撤掉了按番号入口,代码层无解。

        Returns:
            (result_dict | None, attempts_list)
            attempts 每条:
              {"source": str, "status": "ok|no_result|error", "elapsed_ms": int, "detail": str}
        """
        avid = content_id.upper().replace("_", "-")
        sites = self._sites()
        attempts: list[dict] = []
        for name, search_fn in sites:
            t0 = time.time()
            try:
                result = await search_fn(avid)
            except Exception as e:
                elapsed_ms = int((time.time() - t0) * 1000)
                attempts.append({
                    "source": name,
                    "status": "error",
                    "elapsed_ms": elapsed_ms,
                    "detail": f"{type(e).__name__}: {str(e)[:120]}",
                })
                logger.warning(f"m3u8 search failed on {name} for {avid}: {e}")
                continue
            elapsed_ms = int((time.time() - t0) * 1000)
            if result:
                result["source"] = name
                attempts.append({
                    "source": name,
                    "status": "ok",
                    "elapsed_ms": elapsed_ms,
                    "detail": "",
                })
                logger.info(f"m3u8 found for {avid} on {name}: {result['m3u8_url'][:80]}...")
                return result, attempts
            attempts.append({
                "source": name,
                "status": "no_result",
                "elapsed_ms": elapsed_ms,
                "detail": "未匹配到番号 / 上游未收录",
            })
        return None, attempts

    def _sites(self) -> list[tuple[str, "Callable"]]:
        # rou.video 移除:实测番号 → cuid 映射不可信,首条搜索结果常是题材近似的
        # 另一部片(搜 STARS-001 拿到 START-588 之类),内嵌 player 播出来跟用户
        # 搜的不是同一部。jable / missav / kanav / hohoj 都是按番号入口的硬命中,
        # 不存在这个错配问题。
        return [
            ("jable", self._search_jable),
            ("missav", self._search_missav),
            ("kanav", self._search_kanav),
            ("hohoj", self._search_hohoj),
        ]

    async def stream_sources(self, content_id: str) -> AsyncIterator[dict]:
        """并发跑所有源,谁先出结果谁先 yield。

        每条 yield 一个 dict:
          {"source", "status": "ok|no_result|error", "elapsed_ms",
           "m3u8_url"?, "page_url"?, "title"?, "detail"?}

        最后 yield 一条 {"source": "_done", "status": "done"} 标记结束,
        router 那层用来决定关闭 SSE 流。
        """
        avid = content_id.upper().replace("_", "-")

        async def runner(name: str, fn) -> dict:
            cache_key = f"stream:{avid}:{name}"
            cached = await _get_json_async(cache_key)
            if isinstance(cached, dict) and cached.get("m3u8_url"):
                return {
                    "source": name,
                    "status": "ok",
                    "elapsed_ms": 0,
                    "m3u8_url": cached["m3u8_url"],
                    "title": cached.get("title") or avid,
                    "page_url": cached.get("page_url"),
                    "cached": True,
                }
            start_delay = _STREAM_SOURCE_START_DELAY_SECONDS.get(name, 0)
            if start_delay:
                await asyncio.sleep(start_delay)
            t0 = time.time()
            try:
                result = await fn(avid)
            except Exception as e:
                return {
                    "source": name,
                    "status": "error",
                    "elapsed_ms": int((time.time() - t0) * 1000),
                    "detail": f"{type(e).__name__}: {str(e)[:160]}",
                }
            elapsed_ms = int((time.time() - t0) * 1000)
            if not result:
                return {
                    "source": name,
                    "status": "no_result",
                    "elapsed_ms": elapsed_ms,
                    "detail": "未匹配到番号 / 上游未收录",
                }
            # 只 cache 命中的(no_result 不 cache,免得上游补收录后我们死认空)
            await _set_json_async(cache_key, result, _STREAM_CACHE_TTL)
            return {
                "source": name,
                "status": "ok",
                "elapsed_ms": elapsed_ms,
                "m3u8_url": result.get("m3u8_url"),
                "title": result.get("title") or avid,
                "page_url": result.get("page_url"),
            }

        tasks = [asyncio.create_task(runner(name, fn)) for name, fn in self._sites()]
        try:
            pending: set = set(tasks)
            while pending:
                # 10s 没新事件就 yield 一条 keep-alive 哨兵,router 那层翻成
                # SSE 注释行(": keep-alive"),防 nginx 等反代按 idle 超时
                # 把流切了。FlareSolverr 解 CF 单源能 20~60s,没这条反代会断。
                done, pending = await asyncio.wait(
                    pending, timeout=10, return_when=asyncio.FIRST_COMPLETED,
                )
                if not done:
                    yield {"_keepalive": True}
                    continue
                for t in done:
                    yield await t
            yield {"source": "_done", "status": "done"}
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    # ── Jable (weight 1500) ──────────────────────────────────────

    async def _search_jable(self, avid: str) -> Optional[dict]:
        """jable.tv — Cloudflare 站,优先走 FlareSolverr 解 challenge,失败再 fallback httpx。"""
        url = f"https://jable.tv/videos/{avid.lower()}/"
        headers = {**HEADERS, "Referer": "https://jable.tv/"}

        html = await fetch_with_cf_solver(url, referer="https://jable.tv/")
        if html is None:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, proxy=_proxy()) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return None
                html = resp.text

        m = re.search(r"var hlsUrl\s*=\s*'(https?://[^']+)'", html)
        if not m:
            return None

        title_m = re.search(r"<title>(.*?)</title>", html)
        title = title_m.group(1).strip() if title_m else avid

        return {"m3u8_url": m.group(1), "title": title, "page_url": url}

    # ── MissAV (weight 1000) ─────────────────────────────────────

    async def _search_missav(self, avid: str) -> Optional[dict]:
        """missav.ai — Cloudflare 站,优先 FlareSolverr;失败再 fallback httpx。UUID → surrit master → 最高画质。"""
        urls = [
            f"https://missav.ai/cn/{avid.lower()}-chinese-subtitle",
            f"https://missav.ai/cn/{avid.lower()}-uncensored-leak",
            f"https://missav.ai/cn/{avid.lower()}",
            f"https://missav.ai/dm13/cn/{avid.lower()}",
        ]
        headers = {**HEADERS, "Referer": "https://missav.ai/"}

        html = None
        page_url: Optional[str] = None
        for url in urls:
            solved = await fetch_with_cf_solver(url, referer="https://missav.ai/")
            if solved and "m3u8" in solved:
                html = solved
                page_url = url
                break
        if html is None:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, proxy=_proxy()) as client:
                for url in urls:
                    try:
                        resp = await client.get(url, headers=headers)
                        if resp.status_code == 200 and "m3u8" in resp.text:
                            html = resp.text
                            page_url = url
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

        return {"m3u8_url": m3u8_url, "title": title, "page_url": page_url}

    async def _get_highest_quality_m3u8(self, master_url: str, headers: dict) -> Optional[str]:
        """解析 master playlist，返回最高画质的 stream URL"""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, proxy=_proxy()) as client:
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

    # ── rou.video (覆盖之王,实测 4/4) ──────────────────────────────

    async def _search_rou_video(self, avid: str) -> Optional[dict]:
        """rou.video — Next.js 站,搜索拿 cuid → 详情页 ev 字段 base64+char-shift 解出 videoUrl。

        参考 milon4999/test/scrapers/rouvideo/scraper.py。无 CF challenge,直接 httpx 即可。
        """
        next_data_re = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
        headers = {**HEADERS, "Referer": "https://rou.video/"}

        async with httpx.AsyncClient(timeout=20, follow_redirects=True, proxy=_proxy()) as client:
            r1 = await client.get(f"https://rou.video/search?q={avid.lower()}", headers=headers)
            if r1.status_code != 200:
                return None
            m1 = next_data_re.search(r1.text)
            if not m1:
                return None
            try:
                data1 = json.loads(m1.group(1))
            except Exception:
                return None
            page1 = data1.get("props", {}).get("pageProps", {})
            videos = page1.get("videos") or page1.get("results") or []
            cuid: Optional[str] = None
            title = avid
            if videos:
                first = videos[0]
                cuid = first.get("id")
                title = first.get("name") or first.get("nameZh") or avid
            else:
                # fallback: 从 JSON 文本里抓第一个 cuid 形态
                m_id = re.search(r'"id"\s*:\s*"(cm[a-z0-9]{20,})"', r1.text)
                if m_id:
                    cuid = m_id.group(1)
            if not cuid:
                return None

            r2 = await client.get(f"https://rou.video/v/{cuid}", headers=headers)
            if r2.status_code != 200:
                return None

        m2 = next_data_re.search(r2.text)
        if not m2:
            return None
        try:
            data2 = json.loads(m2.group(1))
        except Exception:
            return None
        ev = data2.get("props", {}).get("pageProps", {}).get("ev") or {}
        d, k = ev.get("d"), ev.get("k")
        if not d or k is None:
            return None
        try:
            raw = base64.b64decode(d)
            payload = json.loads("".join(chr(b - k) for b in raw))
        except Exception:
            return None
        video_url = payload.get("videoUrl")
        if not video_url:
            return None
        return {"m3u8_url": video_url, "title": title, "page_url": f"https://rou.video/v/{cuid}"}

    # ── KanAV (weight 490) ───────────────────────────────────────

    async def _search_kanav(self, avid: str) -> Optional[dict]:
        """kanav.info — Cloudflare 站,搜索页与播放页都走 FlareSolverr;失败再 fallback httpx。"""
        import base64

        search_url = f"https://kanav.info/index.php/vod/search.html?wd={avid.lower()}&by=time_add"
        headers = {**HEADERS, "Referer": "https://kanav.info/"}

        search_html = await fetch_with_cf_solver(search_url, referer="https://kanav.info/")
        play_html: Optional[str] = None
        if search_html is None:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, proxy=_proxy()) as client:
                resp = await client.get(search_url, headers=headers)
                if resp.status_code != 200:
                    return None
                search_html = resp.text

        m = re.search(r'href="(/index\.php/vod/play[^"]*\.html)"', search_html)
        if not m:
            return None

        play_url = f"https://kanav.info{m.group(1)}"
        play_html = await fetch_with_cf_solver(play_url, referer=search_url)
        if play_html is None:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, proxy=_proxy()) as client:
                resp2 = await client.get(play_url, headers=headers)
                if resp2.status_code != 200:
                    return None
                play_html = resp2.text
        html = play_html

        m2 = re.search(r'"url":"([A-Za-z0-9+/=]*)"', html)
        if not m2:
            return None

        try:
            decoded = base64.b64decode(m2.group(1)).decode("utf-8")
            m3u8_url = unquote(decoded)
        except Exception:
            return None

        return {"m3u8_url": m3u8_url, "title": avid, "page_url": play_url}

    # ── HohoJ (weight 400) ───────────────────────────────────────

    async def _search_hohoj(self, avid: str) -> Optional[dict]:
        """hohoj.tv — 搜索 → 嵌入页 → videoSrc。

        老实现取了"第一个 [?&]id=(\\d+)"作为视频 id,在 hohoj 没命中番号但返回擦边
        结果(比如搜 STARS-001 实际得到 020624-001 / IKUNA-001 卡片)时会错播。
        这里改成必须在 video-item 卡片的 <img alt="..."> 第一个 token 上严格
        匹配 avid (大小写不敏感、忽略短横线),没有严格命中就视为 NO_RESULT。
        """
        search_url = f"https://hohoj.tv/search?text={avid.lower()}"
        headers = {**HEADERS, "Referer": "https://hohoj.tv/"}

        async with httpx.AsyncClient(timeout=30, follow_redirects=True, proxy=_proxy()) as client:
            resp = await client.get(search_url, headers=headers)
            if resp.status_code != 200:
                return None
            search_html = resp.text

        avid_norm = avid.upper().replace("-", "").replace("_", "")
        # 每个卡片: href="/video?id={vid}"  ... <img ... alt="{番号} {标题}">
        card_re = re.compile(
            r'href="/video\?id=(\d+)"[^<]*<img[^>]+alt="([^"]+)"',
            re.IGNORECASE | re.DOTALL,
        )
        video_id: Optional[str] = None
        title = avid
        for m in card_re.finditer(search_html):
            alt = m.group(2).strip()
            first_token = alt.split()[0] if alt.split() else ""
            if first_token.upper().replace("-", "").replace("_", "") == avid_norm:
                video_id = m.group(1)
                title = alt
                break
        if not video_id:
            return None

        embed_url = f"https://hohoj.tv/embed?id={video_id}"
        embed_headers = {**headers, "Referer": f"https://hohoj.tv/video?id={video_id}"}
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, proxy=_proxy()) as client:
            resp2 = await client.get(embed_url, headers=embed_headers)
            if resp2.status_code != 200:
                return None
            html = resp2.text

        m2 = re.search(r'var videoSrc\s*=\s*"([^"]+)"', html)
        if not m2:
            return None

        return {"m3u8_url": m2.group(1), "title": title, "page_url": f"https://hohoj.tv/video?id={video_id}"}
