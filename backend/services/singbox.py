"""Managed sing-box core for VLESS/REALITY outbound connectivity."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


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
        cfg = build_config(uri, listen_port=port)
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
        uri = str(proxy.get("vless_uri") or "").strip()
        if not uri:
            raise SingBoxError("VLESS 分享链接为空")
        return await asyncio.to_thread(self.start, uri, int(proxy.get("singbox_port", 17890)))


manager = SingBoxManager()
