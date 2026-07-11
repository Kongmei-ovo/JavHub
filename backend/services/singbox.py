"""Managed sing-box core for VLESS/REALITY outbound connectivity."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import httpx


class SingBoxError(ValueError):
    pass


def parse_vless_uri(uri: str) -> dict:
    uri = (uri or "").strip()
    parsed = urlparse(uri)
    if parsed.scheme.lower() != "vless" or not parsed.username or not parsed.hostname or not parsed.port:
        raise SingBoxError("请输入有效的 vless:// 分享链接")
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
    security = query.get("security", "none")
    if security == "reality" and (not query.get("pbk") or not query.get("sni")):
        raise SingBoxError("REALITY 节点缺少 pbk 或 sni 参数")
    return {
        "name": unquote(parsed.fragment) or parsed.hostname,
        "server": parsed.hostname,
        "server_port": parsed.port,
        "uuid": unquote(parsed.username),
        "flow": query.get("flow", ""),
        "network": query.get("type", "tcp"),
        "security": security,
        "server_name": query.get("sni", ""),
        "public_key": query.get("pbk", ""),
        "short_id": query.get("sid", ""),
        "fingerprint": query.get("fp", "chrome"),
    }


def parse_subscription(payload: str) -> list[str]:
    """Parse plain or base64-encoded VLESS subscription without exposing secrets."""
    text = (payload or "").strip()
    if not text:
        raise SingBoxError("订阅内容为空")
    if not text.lower().startswith("vless://"):
        try:
            padded = text + "=" * (-len(text) % 4)
            text = base64.b64decode(padded).decode("utf-8")
        except Exception as exc:
            raise SingBoxError("订阅不是有效的 Base64 或 VLESS 列表") from exc
    uris = [line.strip() for line in text.splitlines() if line.strip().lower().startswith("vless://")]
    if not uris:
        raise SingBoxError("订阅中没有 VLESS 节点")
    for uri in uris:
        parse_vless_uri(uri)
    return uris


def _vless_outbound(uri: str, tag: str) -> dict:
    node = parse_vless_uri(uri)
    outbound = {"type": "vless", "tag": tag, "server": node["server"], "server_port": node["server_port"], "uuid": node["uuid"]}
    if node["flow"]:
        outbound["flow"] = node["flow"]
    if node["security"] == "reality":
        outbound["tls"] = {"enabled": True, "server_name": node["server_name"], "utls": {"enabled": True, "fingerprint": node["fingerprint"]}, "reality": {"enabled": True, "public_key": node["public_key"], "short_id": node["short_id"]}}
    return outbound


def build_pool_config(uris: list[str], listen_port: int = 17890, api_port: int = 17891, listen_host: str = "127.0.0.1") -> tuple[dict, list[dict]]:
    nodes, outbounds = [], []
    used = set()
    for index, uri in enumerate(uris):
        parsed = parse_vless_uri(uri)
        name = parsed["name"]
        tag = name
        if tag in used:
            tag = f"{name} {index + 1}"
        used.add(tag)
        nodes.append({"tag": tag, "name": name})
        outbounds.append(_vless_outbound(uri, tag))
    tags = [node["tag"] for node in nodes]
    outbounds += [
        {"type": "urltest", "tag": "自动优选", "outbounds": tags, "url": "https://www.cloudflare.com/cdn-cgi/trace", "interval": "10m", "tolerance": 50},
        {"type": "selector", "tag": "proxy", "outbounds": ["自动优选", *tags], "default": "自动优选"},
        {"type": "direct", "tag": "direct"},
    ]
    return ({"log": {"level": "warn", "timestamp": True}, "inbounds": [{"type": "socks", "tag": "socks-in", "listen": listen_host, "listen_port": listen_port}], "outbounds": outbounds, "route": {"final": "proxy"}, "experimental": {"clash_api": {"external_controller": f"127.0.0.1:{api_port}"}}}, nodes)


def build_config(uri: str, listen_host: str = "127.0.0.1", listen_port: int = 17890) -> dict:
    node = parse_vless_uri(uri)
    outbound = {
        "type": "vless", "tag": "proxy", "server": node["server"],
        "server_port": node["server_port"], "uuid": node["uuid"],
    }
    if node["flow"]:
        outbound["flow"] = node["flow"]
    if node["security"] == "reality":
        outbound["tls"] = {
            "enabled": True, "server_name": node["server_name"],
            "utls": {"enabled": True, "fingerprint": node["fingerprint"]},
            "reality": {"enabled": True, "public_key": node["public_key"], "short_id": node["short_id"]},
        }
    return {
        "log": {"level": "warn", "timestamp": True},
        "inbounds": [{"type": "socks", "tag": "socks-in", "listen": listen_host, "listen_port": listen_port}],
        "outbounds": [outbound, {"type": "direct", "tag": "direct"}],
        "route": {"final": "proxy"},
    }


class SingBoxManager:
    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.runtime_dir = Path(os.getenv("JAVHUB_RUNTIME_DIR", Path(__file__).resolve().parents[2] / "data" / "runtime"))
        self.nodes: list[dict] = []
        self.api_port = 17891

    def binary(self) -> str | None:
        configured = os.getenv("SING_BOX_BIN", "").strip()
        bundled = Path(__file__).resolve().parents[2] / "bin" / "sing-box"
        return configured or (str(bundled) if bundled.is_file() else shutil.which("sing-box"))

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def start(self, uri: str, port: int = 17890):
        binary = self.binary()
        if not binary:
            raise SingBoxError("未找到 sing-box 核心；请安装 sing-box 或设置 SING_BOX_BIN")
        listen_host = os.getenv("JAVHUB_SINGBOX_LISTEN_HOST", "127.0.0.1").strip() or "127.0.0.1"
        cfg = build_config(uri, listen_host=listen_host, listen_port=port)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.runtime_dir / "sing-box.json"
        config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(config_path, 0o600)
        checked = subprocess.run([binary, "check", "-c", str(config_path)], capture_output=True, text=True, timeout=10)
        if checked.returncode:
            raise SingBoxError((checked.stderr or checked.stdout or "sing-box 配置检查失败").strip())
        self.stop()
        log_path = self.runtime_dir / "sing-box.log"
        log = open(log_path, "ab", buffering=0)
        self.process = subprocess.Popen([binary, "run", "-c", str(config_path)], stdout=log, stderr=subprocess.STDOUT)
        return self.status(port)

    def start_pool(self, uris: list[str], port: int = 17890):
        binary = self.binary()
        if not binary:
            raise SingBoxError("未找到 sing-box 核心")
        listen_host = os.getenv("JAVHUB_SINGBOX_LISTEN_HOST", "127.0.0.1").strip() or "127.0.0.1"
        cfg, self.nodes = build_pool_config(uris, port, self.api_port, listen_host=listen_host)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.runtime_dir / "sing-box.json"
        config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(config_path, 0o600)
        checked = subprocess.run([binary, "check", "-c", str(config_path)], capture_output=True, text=True, timeout=10)
        if checked.returncode:
            raise SingBoxError((checked.stderr or checked.stdout).strip())
        self.stop()
        log = open(self.runtime_dir / "sing-box.log", "ab", buffering=0)
        self.process = subprocess.Popen([binary, "run", "-c", str(config_path)], stdout=log, stderr=subprocess.STDOUT)
        return self.status(port)

    async def fetch_subscription(self, url: str) -> list[str]:
        if urlparse(url).scheme != "https":
            raise SingBoxError("订阅地址必须使用 HTTPS")
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        return parse_subscription(response.text)

    async def refresh(self, proxy: dict):
        uris = await self.fetch_subscription(str(proxy.get("subscription_url") or ""))
        status = await asyncio.to_thread(self.start_pool, uris, int(proxy.get("singbox_port", 17890)))
        return {**status, "nodes": await self.pool_status()}

    async def pool_status(self):
        if not self.nodes:
            return []
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                data = (await client.get(f"http://127.0.0.1:{self.api_port}/proxies")).json().get("proxies", {})
            selected = data.get("proxy", {}).get("now", "")
            return [{**node, "selected": node["tag"] == selected, "delay": (data.get(node["tag"], {}).get("history") or [{}])[-1].get("delay", 0)} for node in self.nodes]
        except Exception:
            return [{**node, "selected": False, "delay": 0} for node in self.nodes]

    async def select(self, tag: str):
        allowed = {"自动优选", *(node["tag"] for node in self.nodes)}
        if tag not in allowed:
            raise SingBoxError("节点不存在")
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.put(f"http://127.0.0.1:{self.api_port}/proxies/proxy", json={"name": tag})
            response.raise_for_status()
        return {"selected": tag, "nodes": await self.pool_status()}

    def status(self, port: int = 17890) -> dict:
        running = bool(self.process and self.process.poll() is None)
        if not running:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.15):
                    running = True
            except OSError:
                pass
        return {"installed": bool(self.binary()), "running": running, "socks_url": f"socks5://127.0.0.1:{port}" if running else ""}

    async def reconcile(self, proxy: dict):
        if not proxy.get("enabled") or proxy.get("mode") != "vless":
            self.stop()
            return self.status(int(proxy.get("singbox_port", 17890)))
        if proxy.get("subscription_url"):
            return await self.refresh(proxy)
        uri = str(proxy.get("vless_uri") or "").strip()
        if not uri:
            raise SingBoxError("VLESS 分享链接为空")
        return await asyncio.to_thread(self.start, uri, int(proxy.get("singbox_port", 17890)))


manager = SingBoxManager()
