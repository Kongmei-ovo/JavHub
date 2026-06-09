"""Cloudflare challenge solver via FlareSolverr.

jable.tv / missav.ai 等站点挂在 Cloudflare 上,会返回 `cf-mitigated: challenge`
+ "Just a moment..." 页;纯 httpx 或 curl_cffi 的 TLS 指纹伪装已不足以绕过。
此模块把请求转交给本地/远端的 FlareSolverr 容器(`cf_solver_url`),由它跑无头
Chrome 解 challenge 后把 HTML 还回来。
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from config import Config

logger = logging.getLogger(__name__)


async def fetch_with_cf_solver(
    url: str,
    *,
    referer: str = "",
    timeout_ms: int = 60_000,
) -> Optional[str]:
    """通过 FlareSolverr 抓一个被 CF 保护的页面,返回 HTML;未配置或失败返回 None。"""
    solver_url = Config().stream_cf_solver_url.strip()
    if not solver_url:
        return None

    payload: dict = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": timeout_ms,
    }
    if referer:
        payload["headers"] = {"Referer": referer}

    # FlareSolverr 自己跑浏览器,这里给 httpx 留出足够时间等它解完 challenge。
    client_timeout = max((timeout_ms / 1000.0) + 10.0, 30.0)
    try:
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            resp = await client.post(solver_url, json=payload)
        if resp.status_code != 200:
            logger.warning("FlareSolverr %s returned HTTP %s", solver_url, resp.status_code)
            return None
        data = resp.json()
    except Exception as exc:
        logger.warning("FlareSolverr request failed for %s: %s", url, exc)
        return None

    if data.get("status") != "ok":
        logger.warning("FlareSolverr non-ok for %s: %s", url, data.get("message"))
        return None
    solution = data.get("solution") or {}
    if solution.get("status") != 200:
        logger.info("CF solver upstream %s -> %s", url, solution.get("status"))
        return None
    return solution.get("response")
