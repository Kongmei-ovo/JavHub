"""Cloudflare challenge solver via FlareSolverr,带 session 复用。

jable.tv / missav.ai 等站点挂在 Cloudflare 上,会返回 `cf-mitigated: challenge`
+ "Just a moment..." 页;纯 httpx 或 curl_cffi 的 TLS 指纹伪装已不足以绕过。
此模块把请求转交给本地/远端的 FlareSolverr 容器(`cf_solver_url`),由它跑无头
Chrome 解 challenge 后把 HTML 还回来。

session 复用:第一次创建一个 long-lived session,后续请求都附带 session id。
FlareSolverr 会复用同一个浏览器实例 + 已经解过的 cf_clearance cookie,把单次
20~30s 的"冷启 chrome + 解 JS challenge"压到秒级。session 过期/容器重启时
自动重建,无需运维介入。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from config import Config

logger = logging.getLogger(__name__)

_SESSION_ID = "javhub-default"
_session_created = False
_session_lock = asyncio.Lock()


async def _ensure_session(client: httpx.AsyncClient, solver_url: str) -> bool:
    """幂等地保证 FlareSolverr 上存在我们的 long-lived session。"""
    global _session_created
    if _session_created:
        return True
    async with _session_lock:
        if _session_created:
            return True
        try:
            resp = await client.post(
                solver_url,
                json={"cmd": "sessions.create", "session": _SESSION_ID},
            )
            data = resp.json() if resp.status_code == 200 else {}
        except Exception as exc:
            logger.warning("FlareSolverr session.create failed: %s", exc)
            return False
        if data.get("status") != "ok":
            logger.warning("FlareSolverr session.create non-ok: %s", data.get("message"))
            return False
        _session_created = True
        logger.info("FlareSolverr session %s ready", _SESSION_ID)
        return True


def _reset_session() -> None:
    global _session_created
    _session_created = False


async def fetch_with_cf_solver(
    url: str,
    *,
    referer: str = "",
    timeout_ms: int = 60_000,
) -> Optional[str]:
    """通过 FlareSolverr(带 session 复用)抓一个被 CF 保护的页面。未配置/失败返回 None。"""
    solver_url = Config().stream_cf_solver_url.strip()
    if not solver_url:
        return None

    base_payload: dict = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": timeout_ms,
    }
    if referer:
        base_payload["headers"] = {"Referer": referer}

    # FlareSolverr 跑浏览器需要时间,httpx 留余量等它解完 challenge。
    client_timeout = max((timeout_ms / 1000.0) + 10.0, 30.0)

    try:
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            # 两次尝试:第一次复用 session;如果 session 不存在(容器重启 / 过期),
            # 重置标志后第二次会自动创建新 session 再发请求。
            for attempt in (1, 2):
                if not await _ensure_session(client, solver_url):
                    return None
                payload = {**base_payload, "session": _SESSION_ID}
                resp = await client.post(solver_url, json=payload)
                if resp.status_code != 200:
                    logger.warning("FlareSolverr HTTP %s", resp.status_code)
                    return None
                data = resp.json()
                msg = (data.get("message") or "").lower()
                if data.get("status") != "ok":
                    # session 失效时 FlareSolverr 会返回 "session not found / Session"
                    if attempt == 1 and "session" in msg:
                        logger.info("FlareSolverr session lost, rebuilding")
                        _reset_session()
                        continue
                    logger.warning("FlareSolverr non-ok for %s: %s", url, data.get("message"))
                    return None
                solution = data.get("solution") or {}
                if solution.get("status") != 200:
                    logger.info("CF solver upstream %s -> %s", url, solution.get("status"))
                    return None
                return solution.get("response")
    except Exception as exc:
        logger.warning("FlareSolverr request failed for %s: %s", url, exc)
        return None
    return None
