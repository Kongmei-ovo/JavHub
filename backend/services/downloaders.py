from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from config import config

logger = logging.getLogger(__name__)

DOWNLOADER_TIMEOUT = 30
SENSITIVE_FIELDS = {"password", "token", "secret", "api_key"}

DOWNLOADER_TYPES = [
    {"value": "open115", "label": "115 Open（原生）"},
    {"value": "qbittorrent", "label": "qBittorrent"},
    {"value": "transmission", "label": "Transmission"},
    {"value": "synology", "label": "Synology Download Station"},
    {"value": "aria2", "label": "Aria2"},
    {"value": "deluge", "label": "Deluge"},
    {"value": "flood", "label": "Flood"},
    {"value": "rutorrent", "label": "ruTorrent"},
    {"value": "utorrent", "label": "µTorrent / uTorrent"},
]

TYPE_ALIASES = {
    "openlist": "openlist",
    "alist": "openlist",
    "115": "open115",
    "open115": "open115",
    "qb": "qbittorrent",
    "qbt": "qbittorrent",
    "qbit": "qbittorrent",
    "qbittorrent": "qbittorrent",
    "transmission": "transmission",
    "tr": "transmission",
    "synology": "synology",
    "synologydownloadstation": "synology",
    "downloadstation": "synology",
    "群晖": "synology",
    "群晖下载器": "synology",
    "aria2": "aria2",
    "deluge": "deluge",
    "flood": "flood",
    "rutorrent": "rutorrent",
    "rtorrent": "rutorrent",
    "utorrent": "utorrent",
    "µtorrent": "utorrent",
    "μtorrent": "utorrent",
    "microtorrent": "utorrent",
    "mutorrent": "utorrent",
}


@dataclass
class DownloadActionResult:
    success: bool
    remote_task_id: str = ""
    message: str = ""


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _clean_type(value: Any) -> str:
    normalized = re.sub(r"[\s_\-.]", "", str(value or "").strip().lower())
    return TYPE_ALIASES.get(normalized, str(value or "").strip().lower())


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _extract_info_hash(magnet: str) -> str:
    match = re.search(r"btih:([a-fA-F0-9]{40}|[a-zA-Z0-9]{32})", magnet or "")
    return match.group(1).lower() if match else ""


def _first_csv_item(value: Any) -> str:
    return next((item.strip() for item in str(value or "").split(",") if item.strip()), "")


def _csv_items(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _basic_auth(client_config: dict[str, Any]) -> tuple[str, str] | None:
    username = client_config.get("username") or ""
    password = client_config.get("password") or ""
    return (username, password) if username or password else None


def _safe_client_id(value: Any, fallback: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raw = fallback
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").lower()
    return safe or fallback


def _normalize_client(raw: dict[str, Any] | None, index: int = 0) -> dict[str, Any]:
    raw = raw or {}
    client_type = _clean_type(raw.get("type") or raw.get("client_type"))
    fallback_id = f"{client_type}-{index + 1}"
    default_name = next((item["label"] for item in DOWNLOADER_TYPES if item["value"] == client_type), client_type)
    return {
        "id": _safe_client_id(raw.get("id"), fallback_id),
        "type": client_type,
        "name": str(raw.get("name") or default_name).strip(),
        "enabled": _as_bool(raw.get("enabled"), True),
        "address": str(raw.get("address") or raw.get("api_url") or "").strip(),
        "username": str(raw.get("username") or "").strip(),
        "password": str(raw.get("password") or ""),
        "token": str(raw.get("token") or raw.get("secret") or ""),
        "default_path": str(raw.get("default_path") or raw.get("path") or "").strip(),
        "category": str(raw.get("category") or "").strip(),
        "tags": str(raw.get("tags") or raw.get("label") or "").strip(),
        "paused": _as_bool(raw.get("paused"), False),
        "timeout": int(raw.get("timeout") or DOWNLOADER_TIMEOUT),
    }


def _native_open115_client() -> dict[str, Any]:
    from services.open115 import open115_binding_status

    settings = config._config.get("open115", {}) if isinstance(config._config, dict) else {}
    if not isinstance(settings, dict):
        settings = {}
    binding = open115_binding_status(settings)
    return _normalize_client({
        "id": "open115",
        "type": "open115",
        "name": "115 Open（原生）",
        "enabled": binding["verified"],
        "default_path": settings.get("root_path") or "/JavHub",
    })


def _public_client(client: dict[str, Any]) -> dict[str, Any]:
    result = dict(client)
    for key in SENSITIVE_FIELDS:
        configured = bool(result.get(key))
        result[f"{key}_configured"] = configured
        result[key] = ""
    return result


def get_downloaders_config(include_sensitive: bool = False) -> dict[str, Any]:
    raw = config._config.get("downloaders", {}) if isinstance(config._config, dict) else {}
    clients = raw.get("clients") if isinstance(raw, dict) else None
    if not isinstance(clients, list):
        clients = []
    normalized = [
        _normalize_client(item, index)
        for index, item in enumerate(clients)
        if isinstance(item, dict) and _clean_type(item.get("type")) not in {"openlist", "open115"}
    ]
    normalized.insert(0, _native_open115_client())

    default_id = str(raw.get("default_id") or "").strip() if isinstance(raw, dict) else ""
    if default_id == "openlist":
        default_id = "open115"
    selected = next((item for item in normalized if item["id"] == default_id), None)
    if not selected or not selected.get("enabled"):
        default = next((item for item in normalized if item.get("enabled")), None)
        default_id = default["id"] if default else ""

    public_clients = normalized if include_sensitive else [_public_client(item) for item in normalized]
    return {
        "default_id": default_id,
        "clients": public_clients,
        "types": DOWNLOADER_TYPES,
    }


def merge_downloaders_payload(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_downloaders_config(include_sensitive=True)
    current_by_id = {item["id"]: item for item in current["clients"]}
    incoming_clients = payload.get("clients") or payload.get("downloaders") or []
    if not isinstance(incoming_clients, list):
        incoming_clients = []

    merged_clients = []
    for index, item in enumerate(incoming_clients):
        if not isinstance(item, dict):
            continue
        client = _normalize_client(item, index)
        if client["type"] in {"openlist", "open115"}:
            continue
        old = current_by_id.get(client["id"], {})
        for key in SENSITIVE_FIELDS:
            if not client.get(key) and old.get(key):
                client[key] = old[key]
        merged_clients.append(client)

    default_id = str(payload.get("default_id") or "").strip()
    if default_id == "openlist":
        default_id = "open115"
    native_enabled = _native_open115_client()["enabled"]
    valid_default_ids = {item["id"] for item in merged_clients}
    if native_enabled:
        valid_default_ids.add("open115")
    if not default_id or default_id not in valid_default_ids:
        if native_enabled:
            return {"default_id": "open115", "clients": merged_clients}
        default = next((item for item in merged_clients if item.get("enabled")), merged_clients[0] if merged_clients else None)
        default_id = default["id"] if default else ""

    return {"default_id": default_id, "clients": merged_clients}


def save_downloaders_config(payload: dict[str, Any]) -> dict[str, Any]:
    merged = merge_downloaders_payload(payload)
    config.update({"downloaders": merged})
    return get_downloaders_config(include_sensitive=False)


def get_downloader_config(downloader_id: str | None = None) -> Optional[dict[str, Any]]:
    cfg = get_downloaders_config(include_sensitive=True)
    clients = cfg["clients"]
    selected_id = downloader_id or cfg.get("default_id")
    selected = next((item for item in clients if item["id"] == selected_id), None)
    if selected and selected.get("enabled"):
        return selected
    return next((item for item in clients if item.get("enabled")), None)


class BaseDownloaderClient:
    def __init__(self, client_config: dict[str, Any]):
        self.config = client_config
        self.address = str(client_config.get("address") or "").rstrip("/")
        self.timeout = int(client_config.get("timeout") or DOWNLOADER_TIMEOUT)

    async def test(self) -> DownloadActionResult:
        raise NotImplementedError

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        raise NotImplementedError

    async def list_tasks(self) -> list[dict[str, Any]]:
        return []


class NativeOpen115DownloaderClient(BaseDownloaderClient):
    async def test(self) -> DownloadActionResult:
        from services.open115 import Open115Error, open115_client

        try:
            await open115_client.test_connection()
            return DownloadActionResult(True, message="连接正常")
        except Open115Error as exc:
            return DownloadActionResult(False, message=exc.api_message)

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        return DownloadActionResult(False, message="115 离线任务必须绑定稳定 movie_id")


class QBittorrentDownloaderClient(BaseDownloaderClient):
    async def _client(self) -> httpx.AsyncClient:
        client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        username = self.config.get("username") or ""
        password = self.config.get("password") or ""
        if username or password:
            resp = await client.post(
                _join_url(self.address, "/api/v2/auth/login"),
                data={"username": username, "password": password},
            )
            if resp.status_code != 200 or resp.text.strip() != "Ok.":
                await client.aclose()
                raise RuntimeError("qBittorrent 登录失败")
        return client

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="qBittorrent 地址为空")
        try:
            client = await self._client()
            async with client:
                resp = await client.get(_join_url(self.address, "/api/v2/app/version"))
            return DownloadActionResult(resp.status_code == 200, message=resp.text.strip())
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        try:
            client = await self._client()
            data: dict[str, Any] = {"urls": magnet}
            save_path = path or self.config.get("default_path") or ""
            if save_path:
                if save_path.startswith("category:"):
                    data["autoTMM"] = "true"
                    data["category"] = save_path.replace("category:", "", 1)
                else:
                    data["savepath"] = save_path
            if self.config.get("category"):
                data["category"] = self.config["category"]
            if self.config.get("tags"):
                data["tags"] = self.config["tags"]
            if self.config.get("paused"):
                data["paused"] = "true"
                data["stopped"] = "true"
            async with client:
                resp = await client.post(_join_url(self.address, "/api/v2/torrents/add"), data=data)
            if resp.status_code == 200 and resp.text.strip() != "Fails.":
                return DownloadActionResult(True, remote_task_id=_extract_info_hash(magnet), message="success")
            return DownloadActionResult(False, message=resp.text.strip() or f"HTTP {resp.status_code}")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        try:
            client = await self._client()
            async with client:
                resp = await client.get(_join_url(self.address, "/api/v2/torrents/info"))
            if resp.status_code != 200:
                return []
            return [
                {
                    "id": item.get("hash", ""),
                    "hash": str(item.get("hash") or "").lower(),
                    "status": self._status_from_state(item.get("state")),
                    "raw": item,
                }
                for item in resp.json()
            ]
        except Exception as exc:
            logger.warning("qBittorrent task list failed: %s", exc)
            return []

    def _status_from_state(self, state: str) -> str:
        if state in {"error", "missingFiles"}:
            return "failed"
        if state in {"uploading", "stalledUP", "pausedUP", "queuedUP", "checkingUP", "forcedUP"}:
            return "completed"
        if state in {"pausedDL", "queuedDL", "checkingDL", "allocating", "checkingResumeData"}:
            return "pending"
        if state:
            return "downloading"
        return "unknown"


class TransmissionDownloaderClient(BaseDownloaderClient):
    def _rpc_url(self) -> str:
        if self.address.endswith("/rpc"):
            return self.address
        return _join_url(self.address, "/transmission/rpc")

    async def _request(self, method: str, args: dict[str, Any] | None = None, session_id: str = "") -> dict[str, Any]:
        auth = None
        username = self.config.get("username") or ""
        password = self.config.get("password") or ""
        if username or password:
            auth = (username, password)
        headers = {"X-Transmission-Session-Id": session_id} if session_id else {}
        async with httpx.AsyncClient(timeout=self.timeout, auth=auth) as client:
            resp = await client.post(self._rpc_url(), json={"method": method, "arguments": args or {}}, headers=headers)
        if resp.status_code == 409:
            sid = resp.headers.get("X-Transmission-Session-Id") or resp.headers.get("x-transmission-session-id") or ""
            return await self._request(method, args, sid)
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") != "success":
            raise RuntimeError(data.get("result") or "Transmission RPC failed")
        return data

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="Transmission 地址为空")
        try:
            data = await self._request("session-get")
            version = data.get("arguments", {}).get("version") or "connected"
            return DownloadActionResult(True, message=str(version))
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        args: dict[str, Any] = {"filename": magnet, "paused": bool(self.config.get("paused"))}
        save_path = path or self.config.get("default_path") or ""
        if save_path:
            args["download-dir"] = save_path
        tags = self.config.get("tags") or ""
        if tags:
            args["labels"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
        try:
            try:
                data = await self._request("torrent-add", args)
            except Exception:
                if "labels" not in args:
                    raise
                args.pop("labels", None)
                data = await self._request("torrent-add", args)
            added = data.get("arguments", {}).get("torrent-added") or data.get("arguments", {}).get("torrent-duplicate") or {}
            remote_id = str(added.get("hashString") or added.get("id") or _extract_info_hash(magnet))
            return DownloadActionResult(True, remote_task_id=remote_id, message=added.get("name") or "success")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        try:
            data = await self._request(
                "torrent-get",
                {
                    "fields": [
                        "id",
                        "hashString",
                        "name",
                        "status",
                        "leftUntilDone",
                        "percentDone",
                        "error",
                        "errorString",
                    ]
                },
            )
            return [
                {
                    "id": str(item.get("hashString") or item.get("id") or ""),
                    "hash": str(item.get("hashString") or "").lower(),
                    "status": self._status_from_state(item),
                    "raw": item,
                }
                for item in data.get("arguments", {}).get("torrents", [])
            ]
        except Exception as exc:
            logger.warning("Transmission task list failed: %s", exc)
            return []

    def _status_from_state(self, item: dict[str, Any]) -> str:
        if item.get("error"):
            return "failed"
        if int(item.get("leftUntilDone") or 0) <= 0 and float(item.get("percentDone") or 0) >= 1:
            return "completed"
        if item.get("status") in {3, 4, 5}:
            return "downloading"
        if item.get("status") == 0:
            return "pending"
        return "unknown"


class SynologyDownloaderClient(BaseDownloaderClient):
    async def _api_info(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                _join_url(self.address, "/webapi/query.cgi"),
                params={"api": "SYNO.API.Info", "version": 1, "method": "query", "query": "all"},
            )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(str(data.get("error") or "Synology API query failed"))
        return data.get("data") or {}

    async def _login(self, api_info: dict[str, Any] | None = None) -> str:
        api_info = api_info or await self._api_info()
        auth_info = api_info.get("SYNO.API.Auth") or {}
        max_version = int(auth_info.get("maxVersion") or 6)
        version = 3 if max_version >= 7 else min(max_version, 6)
        path = auth_info.get("path") or "auth.cgi"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                _join_url(self.address, f"/webapi/{path}"),
                params={
                    "api": "SYNO.API.Auth",
                    "version": version,
                    "method": "login",
                    "account": self.config.get("username") or "",
                    "passwd": self.config.get("password") or "",
                    "session": "DownloadStation",
                    "format": "sid",
                },
            )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(str(data.get("error") or "Synology 登录失败"))
        return data.get("data", {}).get("sid") or ""

    def _task_path(self, api_info: dict[str, Any]) -> tuple[str, int]:
        task_info = api_info.get("SYNO.DownloadStation.Task") or {}
        path = task_info.get("path") or "DownloadStation/task.cgi"
        version = min(int(task_info.get("maxVersion") or 3), 3)
        return path, version

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="Synology 地址为空")
        try:
            api_info = await self._api_info()
            sid = await self._login(api_info)
            if sid:
                return DownloadActionResult(True, message="连接正常")
            return DownloadActionResult(False, message="Synology 未返回会话")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        try:
            api_info = await self._api_info()
            sid = await self._login(api_info)
            task_path, version = self._task_path(api_info)
            data = {
                "api": "SYNO.DownloadStation.Task",
                "version": version,
                "method": "create",
                "uri": magnet,
                "_sid": sid,
            }
            save_path = path or self.config.get("default_path") or ""
            if save_path:
                data["destination"] = save_path
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(_join_url(self.address, f"/webapi/{task_path}"), data=data)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("success"):
                return DownloadActionResult(True, remote_task_id=_extract_info_hash(magnet), message="success")
            return DownloadActionResult(False, message=str(payload.get("error") or payload))
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        try:
            api_info = await self._api_info()
            sid = await self._login(api_info)
            task_path, version = self._task_path(api_info)
            data = {
                "api": "SYNO.DownloadStation.Task",
                "version": version,
                "method": "list",
                "additional": "detail,transfer",
                "_sid": sid,
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(_join_url(self.address, f"/webapi/{task_path}"), data=data)
            payload = resp.json()
            if not payload.get("success"):
                return []
            return [
                {
                    "id": str(item.get("id") or item.get("hash") or ""),
                    "hash": str(item.get("additional", {}).get("detail", {}).get("hash") or item.get("hash") or "").lower(),
                    "status": self._status_from_state(item.get("status")),
                    "raw": item,
                }
                for item in payload.get("data", {}).get("tasks", [])
            ]
        except Exception as exc:
            logger.warning("Synology task list failed: %s", exc)
            return []

    def _status_from_state(self, status: str) -> str:
        if status in {"finished", "seeding"}:
            return "completed"
        if status in {"error", "broken"}:
            return "failed"
        if status in {"waiting", "paused"}:
            return "pending"
        if status:
            return "downloading"
        return "unknown"


class Aria2DownloaderClient(BaseDownloaderClient):
    def _rpc_url(self) -> str:
        if self.address.endswith("/jsonrpc"):
            return self.address
        return _join_url(self.address, "/jsonrpc")

    async def _call(self, method: str, params: list[Any] | None = None) -> Any:
        params = params or []
        token = self.config.get("token") or ""
        if token:
            params = [f"token:{token}", *params]
        payload = {"jsonrpc": "2.0", "id": "javhub", "method": method, "params": params}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self._rpc_url(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(data["error"].get("message") or str(data["error"]))
        return data.get("result")

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="Aria2 地址为空")
        try:
            result = await self._call("aria2.getVersion")
            return DownloadActionResult(True, message=result.get("version", "connected"))
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        options: dict[str, Any] = {}
        save_path = path or self.config.get("default_path") or ""
        if save_path:
            options["dir"] = save_path
        if self.config.get("paused"):
            options["pause"] = "true"
        try:
            gid = await self._call("aria2.addUri", [[magnet], options])
            return DownloadActionResult(True, remote_task_id=str(gid or ""), message="success")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for method in ("aria2.tellActive", "aria2.tellWaiting", "aria2.tellStopped"):
            try:
                if method == "aria2.tellWaiting":
                    result = await self._call(method, [0, 1000])
                elif method == "aria2.tellStopped":
                    result = await self._call(method, [0, 1000])
                else:
                    result = await self._call(method)
                tasks.extend(result or [])
            except Exception as exc:
                logger.warning("Aria2 %s failed: %s", method, exc)
        return [
            {
                "id": str(item.get("gid") or ""),
                "hash": str(item.get("infoHash") or "").lower(),
                "status": self._status_from_state(item.get("status")),
                "raw": item,
            }
            for item in tasks
        ]

    def _status_from_state(self, status: str) -> str:
        if status == "complete":
            return "completed"
        if status == "error":
            return "failed"
        if status in {"paused", "waiting"}:
            return "pending"
        if status == "active":
            return "downloading"
        return "unknown"


class DelugeDownloaderClient(BaseDownloaderClient):
    def __init__(self, client_config: dict[str, Any]):
        super().__init__(client_config)
        self._msg_id = 0
        self._logged_in = False
        self._cookies = httpx.Cookies()

    def _json_url(self) -> str:
        if self.address.rstrip("/").endswith("/json"):
            return self.address
        return _join_url(self.address, "/json")

    async def _request(self, method: str, params: list[Any] | None = None, ensure_login: bool = True) -> Any:
        if ensure_login and not self._logged_in:
            await self._login()
        payload = {"id": self._msg_id, "method": method, "params": params or []}
        self._msg_id += 1
        async with httpx.AsyncClient(timeout=self.timeout, cookies=self._cookies) as client:
            resp = await client.post(self._json_url(), json=payload)
            self._cookies = client.cookies
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(str(data["error"]))
        return data.get("result")

    async def _login(self) -> bool:
        password = self.config.get("password") or ""
        result = await self._request("auth.login", [password], ensure_login=False)
        self._logged_in = bool(result)
        if not self._logged_in:
            raise RuntimeError("Deluge 登录失败")
        return True

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="Deluge 地址为空")
        try:
            await self._login()
            version = await self._request("daemon.info")
            return DownloadActionResult(True, message=str(version or "connected"))
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        options: dict[str, Any] = {"add_paused": bool(self.config.get("paused"))}
        save_path = path or self.config.get("default_path") or ""
        if save_path:
            options["download_location"] = save_path
        try:
            result = await self._request("core.add_torrent_url", [magnet, options])
            if result is None:
                return DownloadActionResult(False, message="Deluge 未返回任务 ID")
            remote_id = ""
            if isinstance(result, str):
                remote_id = result
            elif isinstance(result, list) and result:
                remote_id = str(result[0][1] if isinstance(result[0], (list, tuple)) and len(result[0]) > 1 else result[0])
            remote_id = remote_id or _extract_info_hash(magnet)
            label = self.config.get("tags") or self.config.get("category") or ""
            if remote_id and label:
                try:
                    await self._request("label.set_torrent", [remote_id, _first_csv_item(label)])
                except Exception as exc:
                    logger.info("Deluge label.set_torrent ignored: %s", exc)
            return DownloadActionResult(True, remote_task_id=remote_id, message="success")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        try:
            fields = ["hash", "name", "progress", "state", "is_finished", "message"]
            result = await self._request("core.get_torrents_status", [{}, fields])
            return [
                {
                    "id": str(item.get("hash") or info_hash or "").lower(),
                    "hash": str(item.get("hash") or info_hash or "").lower(),
                    "status": self._status_from_state(item),
                    "raw": item,
                }
                for info_hash, item in (result or {}).items()
                if isinstance(item, dict)
            ]
        except Exception as exc:
            logger.warning("Deluge task list failed: %s", exc)
            return []

    def _status_from_state(self, item: dict[str, Any]) -> str:
        state = str(item.get("state") or "").lower()
        if state in {"seeding"} or item.get("is_finished") or float(item.get("progress") or 0) >= 100:
            return "completed"
        if state == "error":
            return "failed"
        if state in {"paused", "queued", "checking"}:
            return "pending"
        if state:
            return "downloading"
        return "unknown"


class FloodDownloaderClient(BaseDownloaderClient):
    ENDPOINTS = {
        "jesec": {
            "verify": "/api/auth/verify",
            "authenticate": "/api/auth/authenticate",
            "connection": "/api/client/connection-test",
            "add_urls": "/api/torrents/add-urls",
            "torrents": "/api/torrents",
        },
        "legacy": {
            "verify": "/auth/verify",
            "authenticate": "/auth/authenticate",
            "connection": "/api/client/connection-test",
            "add_urls": "/api/client/add",
            "torrents": "",
        },
    }

    def __init__(self, client_config: dict[str, Any]):
        super().__init__(client_config)
        self._api_type = _clean_type(client_config.get("api_type") or client_config.get("version") or "")
        if self._api_type not in {"legacy", "jesec"}:
            self._api_type = ""

    async def _detect_api_type(self, client: httpx.AsyncClient) -> str:
        if self._api_type:
            return self._api_type
        try:
            resp = await client.get(_join_url(self.address, self.ENDPOINTS["legacy"]["verify"]))
            self._api_type = "legacy" if resp.status_code < 400 else "jesec"
        except Exception:
            self._api_type = "jesec"
        return self._api_type

    async def _login(self, client: httpx.AsyncClient) -> bool:
        api_type = await self._detect_api_type(client)
        resp = await client.post(
            _join_url(self.address, self.ENDPOINTS[api_type]["authenticate"]),
            json={"username": self.config.get("username") or "", "password": self.config.get("password") or ""},
        )
        if resp.status_code >= 400:
            return False
        try:
            data = resp.json()
        except Exception:
            return 200 <= resp.status_code < 300
        return bool(data.get("success", True))

    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        json: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            api_type = await self._detect_api_type(client)
            url = _join_url(self.address, self.ENDPOINTS[api_type][endpoint])
            resp = await client.request(method, url, json=json)
            if resp.status_code == 401 and retry_auth and await self._login(client):
                resp = await client.request(method, url, json=json)
            return resp

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="Flood 地址为空")
        try:
            resp = await self._request("connection")
            if resp.status_code >= 400:
                return DownloadActionResult(False, message=f"Flood 返回 {resp.status_code}")
            data = resp.json()
            if data.get("isConnect", True) is False:
                return DownloadActionResult(False, message=str(data))
            return DownloadActionResult(True, message="连接正常")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        payload: dict[str, Any] = {
            "urls": [magnet],
            "destination": path or self.config.get("default_path") or "",
            "tags": _csv_items(self.config.get("tags") or self.config.get("category")),
        }
        if self.config.get("paused"):
            payload["start"] = False
        try:
            resp = await self._request("add_urls", method="POST", json=payload)
            if resp.status_code < 400:
                return DownloadActionResult(True, remote_task_id=_extract_info_hash(magnet), message="success")
            return DownloadActionResult(False, message=resp.text or f"HTTP {resp.status_code}")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        try:
            resp = await self._request("torrents")
            if resp.status_code >= 400:
                return []
            data = resp.json()
            raw_torrents = data.get("torrents", data) if isinstance(data, dict) else {}
            if isinstance(raw_torrents, list):
                pairs = [(item.get("hash", item.get("id", "")), item) for item in raw_torrents if isinstance(item, dict)]
            elif isinstance(raw_torrents, dict):
                pairs = list(raw_torrents.items())
            else:
                pairs = []
            return [
                {
                    "id": str(info_hash or item.get("hash") or "").lower(),
                    "hash": str(info_hash or item.get("hash") or "").lower(),
                    "status": self._status_from_state(item),
                    "raw": item,
                }
                for info_hash, item in pairs
                if isinstance(item, dict)
            ]
        except Exception as exc:
            logger.warning("Flood task list failed: %s", exc)
            return []

    def _status_from_state(self, item: dict[str, Any]) -> str:
        statuses = item.get("status") or []
        if isinstance(statuses, str):
            statuses = [statuses]
        statuses = {str(status).lower() for status in statuses}
        if statuses & {"error", "e"}:
            return "failed"
        if item.get("isComplete") or statuses & {"seeding", "complete", "sd", "au"}:
            return "completed"
        if statuses & {"stopped", "checking", "p", "s", "ch"}:
            return "pending"
        if statuses:
            return "downloading"
        return "unknown"


class RuTorrentDownloaderClient(BaseDownloaderClient):
    async def _request(self, path: str, method: str = "GET", **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout, auth=_basic_auth(self.config), follow_redirects=True) as client:
            resp = await client.request(method, _join_url(self.address, path), **kwargs)
        resp.raise_for_status()
        return resp

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="ruTorrent 地址为空")
        try:
            resp = await self._request("/php/getsettings.php")
            return DownloadActionResult(True, message="连接正常" if resp.status_code == 200 else f"HTTP {resp.status_code}")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        data: dict[str, Any] = {"url": magnet, "json": "1"}
        save_path = path or self.config.get("default_path") or ""
        if save_path:
            data["dir_edit"] = save_path
        if self.config.get("paused"):
            data["torrents_start_stopped"] = "1"
        label = _first_csv_item(self.config.get("tags") or self.config.get("category"))
        if label:
            data["label"] = label
        try:
            resp = await self._request("/php/addtorrent.php", method="POST", data=data)
            payload = resp.json()
            if payload.get("result") == "Success":
                return DownloadActionResult(True, remote_task_id=_extract_info_hash(magnet), message="success")
            return DownloadActionResult(False, message=str(payload))
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        try:
            resp = await self._request("/plugins/httprpc/action.php", method="POST", data={"mode": "list"})
            data = resp.json()
            torrents = data.get("t") or {}
            return [
                {
                    "id": str(info_hash or "").lower(),
                    "hash": str(info_hash or "").lower(),
                    "status": self._status_from_state(item),
                    "raw": item,
                }
                for info_hash, item in torrents.items()
                if isinstance(item, list)
            ]
        except Exception as exc:
            logger.warning("ruTorrent task list failed: %s", exc)
            return []

    def _status_from_state(self, item: list[Any]) -> str:
        try:
            is_open = int(item[0] or 0)
            is_hash_checking = int(item[1] or 0)
            get_state = int(item[3] or 0)
            completed = int(item[6] or 0) >= int(item[7] or 1)
            get_hashing = int(item[23] or 0)
            is_active = int(item[28] or 0)
            message = str(item[30] or "")
        except Exception:
            return "unknown"
        if is_open:
            if get_state == 0 or is_active == 0:
                return "pending"
            return "completed" if completed else "downloading"
        if get_hashing or is_hash_checking:
            return "pending"
        if message and message != "Tracker: [Tried all trackers.]":
            return "failed"
        return "unknown"


class UTorrentDownloaderClient(BaseDownloaderClient):
    STATE_STARTED = 1
    STATE_CHECKING = 2
    STATE_ERROR = 16
    STATE_PAUSED = 32
    STATE_QUEUED = 64

    def _gui_url(self) -> str:
        if re.search(r"/gui/?$", self.address):
            return self.address.rstrip("/") + "/"
        return _join_url(self.address, "/gui/")

    async def _token(self) -> str:
        async with httpx.AsyncClient(timeout=self.timeout, auth=_basic_auth(self.config), follow_redirects=True) as client:
            resp = await client.get(_join_url(self._gui_url(), "/token.html"), params={"t": "1"})
        resp.raise_for_status()
        match = re.search(r">([^<]+)<", resp.text or "")
        if not match:
            raise RuntimeError("µTorrent 未返回 token")
        return match.group(1)

    async def _request(self, params: dict[str, Any], method: str = "GET") -> httpx.Response:
        token = await self._token()
        ordered_params = {"token": token, **params}
        async with httpx.AsyncClient(timeout=self.timeout, auth=_basic_auth(self.config), follow_redirects=True) as client:
            resp = await client.request(method, self._gui_url(), params=ordered_params)
        resp.raise_for_status()
        return resp

    async def test(self) -> DownloadActionResult:
        if not self.address:
            return DownloadActionResult(False, message="µTorrent 地址为空")
        try:
            await self._token()
            return DownloadActionResult(True, message="连接正常")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def add_magnet(self, magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        save_path = path or self.config.get("default_path") or ""
        try:
            resp = await self._request(
                {"action": "add-url", "download_dir": 0, "path": save_path, "s": magnet},
                method="POST",
            )
            if resp.status_code >= 400:
                return DownloadActionResult(False, message=resp.text or f"HTTP {resp.status_code}")
            info_hash = _extract_info_hash(magnet)
            if info_hash and self.config.get("paused"):
                await self._request({"action": "pause", "hash": info_hash})
            label = _first_csv_item(self.config.get("tags") or self.config.get("category"))
            if info_hash and label:
                await self._request({"action": "setprops", "hash": info_hash, "s": "label", "v": label})
            return DownloadActionResult(True, remote_task_id=info_hash, message="success")
        except Exception as exc:
            return DownloadActionResult(False, message=str(exc))

    async def list_tasks(self) -> list[dict[str, Any]]:
        try:
            resp = await self._request({"list": 1})
            torrents = resp.json().get("torrents") or []
            return [
                {
                    "id": str(item[0] or "").lower(),
                    "hash": str(item[0] or "").lower(),
                    "status": self._status_from_state(item),
                    "raw": item,
                }
                for item in torrents
                if isinstance(item, list) and item
            ]
        except Exception as exc:
            logger.warning("µTorrent task list failed: %s", exc)
            return []

    def _status_from_state(self, item: list[Any]) -> str:
        try:
            state = int(item[1] or 0)
            done = float(item[4] or 0) >= 1000
        except Exception:
            return "unknown"
        if state & self.STATE_ERROR:
            return "failed"
        if state & self.STATE_PAUSED or state & self.STATE_CHECKING or state & self.STATE_QUEUED:
            return "pending"
        if done:
            return "completed"
        if state & self.STATE_STARTED:
            return "downloading"
        return "pending" if done else "unknown"


def create_downloader_client(client_config: dict[str, Any]) -> BaseDownloaderClient:
    client_type = _clean_type(client_config.get("type"))
    if client_type == "openlist":
        raise ValueError("OpenList 下载器已下线，请绑定 115 Open")
    if client_type == "open115":
        return NativeOpen115DownloaderClient(client_config)
    if client_type == "qbittorrent":
        client = QBittorrentDownloaderClient(client_config)
    elif client_type == "transmission":
        client = TransmissionDownloaderClient(client_config)
    elif client_type == "synology":
        client = SynologyDownloaderClient(client_config)
    elif client_type == "aria2":
        client = Aria2DownloaderClient(client_config)
    elif client_type == "deluge":
        client = DelugeDownloaderClient(client_config)
    elif client_type == "flood":
        client = FloodDownloaderClient(client_config)
    elif client_type == "rutorrent":
        client = RuTorrentDownloaderClient(client_config)
    elif client_type == "utorrent":
        client = UTorrentDownloaderClient(client_config)
    else:
        raise ValueError(f"不支持的下载器类型: {client_type or 'empty'}")
    return _with_duplicate_preflight(client)


def _with_duplicate_preflight(client: BaseDownloaderClient) -> BaseDownloaderClient:
    add_magnet = client.add_magnet

    async def add_magnet_with_duplicate_check(magnet: str, path: str = "", title: str = "") -> DownloadActionResult:
        if _extract_info_hash(magnet):
            try:
                duplicate = check_duplicate_download(await client.list_tasks(), magnet)
                if not duplicate.success:
                    return duplicate
            except Exception as exc:
                logger.warning("Downloader duplicate preflight failed: %s", exc)
        return await add_magnet(magnet, path, title)

    client.add_magnet = add_magnet_with_duplicate_check  # type: ignore[method-assign]
    return client


async def test_downloader_config(client_config: dict[str, Any]) -> DownloadActionResult:
    normalized = _normalize_client(client_config, 0)
    return await create_downloader_client(normalized).test()


def match_remote_task(tasks: list[dict[str, Any]], magnet: str, remote_task_id: str = "") -> Optional[dict[str, Any]]:
    info_hash = _extract_info_hash(magnet)
    if remote_task_id:
        matched = next((task for task in tasks if str(task.get("id") or "").lower() == remote_task_id.lower()), None)
        if matched:
            return matched
    if info_hash:
        return next((task for task in tasks if str(task.get("hash") or "").lower() == info_hash), None)
    return None


def check_duplicate_download(
    tasks: list[dict[str, Any]],
    magnet: str,
    remote_task_id: str = "",
) -> DownloadActionResult:
    matched = match_remote_task(tasks, magnet, remote_task_id)
    if not matched:
        return DownloadActionResult(True, message="not duplicate")
    duplicate_id = str(matched.get("id") or matched.get("hash") or remote_task_id or _extract_info_hash(magnet))
    status = str(matched.get("status") or "remote").strip()
    return DownloadActionResult(False, remote_task_id=duplicate_id, message=f"duplicate download: {duplicate_id} ({status})")
