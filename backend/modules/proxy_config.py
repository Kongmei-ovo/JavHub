from __future__ import annotations

from collections.abc import Mapping
from typing import Any


DEFAULT_VLESS_PORT = 17890


def _vless_port(value: Any) -> int:
    if isinstance(value, bool):
        return DEFAULT_VLESS_PORT
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError):
        return DEFAULT_VLESS_PORT
    return port if 1 <= port <= 65535 else DEFAULT_VLESS_PORT


def effective_proxy_url(proxy: Mapping[str, Any] | None, *, advertise_host: str | None = None) -> str:
    proxy_config: Mapping[str, Any] = proxy if isinstance(proxy, Mapping) else {}
    if not proxy_config.get("enabled"):
        return ""
    if proxy_config.get("mode") == "vless":
        host = str(advertise_host or "").strip() or "127.0.0.1"
        port = _vless_port(proxy_config.get("singbox_port"))
        return f"socks5://{host}:{port}"
    http_url = str(proxy_config.get("http_url") or "").strip()
    https_url = str(proxy_config.get("https_url") or "").strip()
    return http_url or https_url
