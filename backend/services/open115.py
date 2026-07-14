"""115 Open API client.

Only durable 115 identifiers may leave this module. Access tokens, download
URLs, and signed transcode URLs are request-scoped values and must not be
logged, cached, or stored in the database.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import secrets
import tempfile
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterable

import httpx
import yaml

from config import config
from modules.loop_client_pool import LoopClientPool

logger = logging.getLogger(__name__)

PASSPORT_BASE = "https://passportapi.115.com"
API_BASE = "https://proapi.115.com"
QRCODE_STATUS_URL = "https://qrcodeapi.115.com/get/status/"
QRCODE_IMAGE_URL = "https://qrcodeapi.115.com/api/1.0/web/1.0/qrcode"

OPEN115_TIMEOUT = 30.0
MIN_REQUEST_INTERVAL = 0.3
FILES_PAGE_SIZE = 500
DEFAULT_ROOT_PATH = "/JavHub"
DEFAULT_UA = "JavHub/1.0"


def open115_binding_status(settings: dict[str, Any] | None) -> dict[str, bool]:
    settings = settings if isinstance(settings, dict) else {}
    bound = bool(os.getenv("OPEN115_REFRESH_TOKEN") or settings.get("refresh_token"))
    return {
        "bound": bound,
        "verified": bound and bool(settings.get("verified")),
    }


class Open115Error(RuntimeError):
    def __init__(self, code: int | str | None, message: str):
        self.code = code
        self.api_message = message
        super().__init__(f"115 Open API error ({code}): {message}")


class Open115AuthRequired(Open115Error):
    pass


def _is_token_expired(code: Any, status_code: int = 200) -> bool:
    if status_code == 401:
        return True
    text = str(code or "")
    return text == "99" or text.startswith("401")


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class PendingAuth:
    uid: str
    timestamp: str
    sign: str
    qrcode: str
    code_verifier: str
    created_at: float


@dataclass(frozen=True)
class TranscodeURL:
    url: str
    definition: int
    desc: str


@dataclass(frozen=True)
class Open115File:
    file_id: str
    parent_id: str
    name: str
    pick_code: str
    is_dir: bool
    size: int
    duration: int
    extension: str
    mtime: int = 0

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> "Open115File":
        name = str(item.get("fn") or item.get("file_name") or "")
        extension = str(item.get("ico") or "").lower().lstrip(".")
        if not extension and "." in name:
            extension = name.rsplit(".", 1)[-1].lower()
        category = str(item.get("fc") if item.get("fc") is not None else item.get("file_category") or "")
        return cls(
            file_id=str(item.get("fid") or item.get("file_id") or ""),
            parent_id=str(item.get("pid") or item.get("parent_id") or ""),
            name=name,
            pick_code=str(item.get("pc") or item.get("pick_code") or ""),
            is_dir=category == "0" or bool(item.get("is_dir")),
            size=_as_int(item.get("fs") or item.get("file_size")),
            duration=_as_int(item.get("play_long") or item.get("duration")),
            extension=extension,
            # 115 修改时间(epoch 秒):upt 优先,回退 uet/ute
            mtime=_as_int(item.get("upt") or item.get("uet") or item.get("ute")),
        )


class Open115Client:
    def __init__(
        self,
        *,
        config_obj: Any = config,
        http_client: Any | None = None,
        http_client_factory: Callable[[], httpx.AsyncClient] | None = None,
        min_request_interval: float = MIN_REQUEST_INTERVAL,
    ):
        if http_client is not None and http_client_factory is not None:
            raise ValueError("http_client and http_client_factory are mutually exclusive")
        self._config = config_obj
        self._http = http_client
        self._http_pool = None if http_client is not None else LoopClientPool(
            http_client_factory or self._new_http_client
        )
        self._min_request_interval = max(0.0, float(min_request_interval))
        self._throttle_lock = threading.Lock()
        self._refresh_state_lock = threading.Lock()
        self._refresh_inflight: Future[bool] | None = None
        self._persist_lock = threading.Lock()
        self._next_request_at = 0.0
        self._pending_auth: dict[str, PendingAuth] = {}
        self._folder_cache: dict[str, str] = {"/": "0"}

    @staticmethod
    def _new_http_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(OPEN115_TIMEOUT),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=False,
        )

    @property
    def settings(self) -> dict[str, Any]:
        value = self._config._config.get("open115", {})
        return value if isinstance(value, dict) else {}

    @property
    def app_id(self) -> str:
        return str(os.getenv("OPEN115_APP_ID") or self.settings.get("app_id") or "").strip()

    @property
    def access_token(self) -> str:
        return str(os.getenv("OPEN115_ACCESS_TOKEN") or self.settings.get("access_token") or "").strip()

    @property
    def refresh_token(self) -> str:
        return str(os.getenv("OPEN115_REFRESH_TOKEN") or self.settings.get("refresh_token") or "").strip()

    @property
    def root_path(self) -> str:
        value = str(self.settings.get("root_path") or DEFAULT_ROOT_PATH).strip()
        return "/" + value.strip("/")

    @property
    def default_ua(self) -> str:
        return str(self.settings.get("user_agent") or DEFAULT_UA).strip()

    def status(self) -> dict[str, Any]:
        binding = open115_binding_status(self.settings)
        return {
            "configured": bool(self.app_id),
            **binding,
            "access_token_configured": bool(self.access_token),
            "refresh_token_configured": binding["bound"],
            "token_expires_at": _as_int(self.settings.get("token_expires_at")),
            "root_path": self.root_path,
        }

    async def close(self) -> None:
        if self._http_pool is not None:
            await self._http_pool.close_all()

    async def _wait_for_request_slot(self) -> None:
        with self._throttle_lock:
            now = time.monotonic()
            slot = max(now, self._next_request_at)
            self._next_request_at = slot + self._min_request_interval
        delay = slot - now
        if delay > 0:
            await asyncio.sleep(delay)

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        await self._wait_for_request_slot()
        try:
            if self._http_pool is not None:
                async with self._http_pool.lease() as http_client:
                    return await http_client.request(method, url, **kwargs)
            return await self._http.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            raise Open115Error(None, "115 Open API 连接失败") from exc

    @staticmethod
    def _json_body(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise Open115Error(response.status_code, "115 Open API 返回了无效 JSON") from exc
        if not isinstance(body, dict):
            raise Open115Error(response.status_code, "115 Open API 返回格式无效")
        return body

    async def _passport_request(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._request(method, url, data=data, params=params)
        body = self._json_body(response)
        if response.status_code != 200:
            raise Open115Error(response.status_code, str(body.get("message") or "授权请求失败"))
        code = body.get("code")
        if code not in (None, 0, "0"):
            raise Open115Error(code, str(body.get("message") or body.get("error") or "授权请求失败"))
        if body.get("error"):
            raise Open115Error(body.get("errno"), str(body["error"]))
        payload = body.get("data")
        return payload if isinstance(payload, dict) else {}

    async def _auth_request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        user_agent: str | None = None,
        retried: bool = False,
        full: bool = False,
    ) -> Any:
        token = self.access_token
        if not token:
            refreshed = await self.refresh_access_token(expected_access_token="")
            if not refreshed:
                raise Open115AuthRequired(None, "115 尚未绑定")
            token = self.access_token

        headers = {"Authorization": f"Bearer {token}"}
        if user_agent is not None:
            headers["User-Agent"] = user_agent
        response = await self._request(
            method,
            f"{API_BASE}{path}",
            data=data,
            params=params,
            headers=headers,
        )
        body = self._json_body(response)
        state = body.get("state")
        failed = response.status_code != 200 or state in (False, 0, "0")
        code = body.get("code", response.status_code)
        if failed:
            if not retried and _is_token_expired(code, response.status_code):
                if await self.refresh_access_token(expected_access_token=token):
                    return await self._auth_request(
                        method,
                        path,
                        data=data,
                        params=params,
                        user_agent=user_agent,
                        retried=True,
                        full=full,
                    )
                raise Open115AuthRequired(code, "115 授权已失效，请重新绑定")
            raise Open115Error(code, str(body.get("message") or f"HTTP {response.status_code}"))
        return body if full else body.get("data")

    async def start_device_auth(self) -> dict[str, str]:
        if not self.app_id:
            raise Open115Error(None, "请先配置 115 Open AppID")
        code_verifier = secrets.token_urlsafe(48)[:64]
        challenge = base64.b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode()
        payload = await self._passport_request(
            "POST",
            f"{PASSPORT_BASE}/open/authDeviceCode",
            data={
                "client_id": self.app_id,
                "code_challenge": challenge,
                "code_challenge_method": "sha256",
            },
        )
        pending = PendingAuth(
            uid=str(payload.get("uid") or ""),
            timestamp=str(payload.get("time") or ""),
            sign=str(payload.get("sign") or ""),
            qrcode=str(payload.get("qrcode") or ""),
            code_verifier=code_verifier,
            created_at=time.monotonic(),
        )
        if not pending.uid:
            raise Open115Error(None, "115 授权接口未返回 uid")
        self._pending_auth[pending.uid] = pending
        while len(self._pending_auth) > 5:
            oldest = min(self._pending_auth.values(), key=lambda item: item.created_at)
            self._pending_auth.pop(oldest.uid, None)
        return {"uid": pending.uid, "qrcode": pending.qrcode}

    def qrcode_image_url(self, uid: str) -> str:
        return f"{QRCODE_IMAGE_URL}?uid={uid}"

    async def poll_device_auth(self, uid: str) -> dict[str, Any]:
        pending = self._pending_auth.get(uid)
        if pending is None:
            return {"status": "expired", "bound": bool(self.refresh_token)}
        response = await self._request(
            "GET",
            QRCODE_STATUS_URL,
            params={"uid": pending.uid, "time": pending.timestamp, "sign": pending.sign},
        )
        body = self._json_body(response)
        if response.status_code != 200:
            raise Open115Error(response.status_code, "查询扫码状态失败")
        payload = body.get("data") if isinstance(body.get("data"), dict) else body
        status_code = _as_int(payload.get("status"), -99)
        if status_code in (-2, -1):
            self._pending_auth.pop(uid, None)
            return {"status": "expired", "bound": bool(self.refresh_token)}
        if status_code == 1:
            return {"status": "scanned", "bound": False}
        if status_code != 2:
            return {"status": "waiting", "bound": False}

        tokens = await self._passport_request(
            "POST",
            f"{PASSPORT_BASE}/open/deviceCodeToToken",
            data={"uid": pending.uid, "code_verifier": pending.code_verifier},
        )
        self._persist_tokens(tokens, verified=False)
        self._pending_auth.pop(uid, None)
        return {"status": "confirmed", "bound": True}

    async def refresh_access_token(self, *, expected_access_token: str | None = None) -> bool:
        with self._refresh_state_lock:
            if (
                expected_access_token is not None
                and self.access_token
                and self.access_token != expected_access_token
            ):
                return True
            shared = self._refresh_inflight
            leader = shared is None
            if shared is None:
                shared = Future()
                self._refresh_inflight = shared

        if not leader:
            waiter = asyncio.wrap_future(shared)
            waiter.add_done_callback(self._consume_refresh_waiter)
            return await asyncio.shield(waiter)

        try:
            result = await self._refresh_access_token_once(expected_access_token)
        except asyncio.CancelledError:
            shared.cancel()
            raise
        except BaseException as exc:
            shared.set_exception(exc)
            raise
        else:
            shared.set_result(result)
            return result
        finally:
            with self._refresh_state_lock:
                if self._refresh_inflight is shared:
                    self._refresh_inflight = None

    async def _refresh_access_token_once(
        self,
        expected_access_token: str | None,
    ) -> bool:
        if (
            expected_access_token is not None
            and self.access_token
            and self.access_token != expected_access_token
        ):
            return True
        refresh_token = self.refresh_token
        if not refresh_token:
            return False
        try:
            tokens = await self._passport_request(
                "POST",
                f"{PASSPORT_BASE}/open/refreshToken",
                data={"refresh_token": refresh_token},
            )
            self._persist_tokens(tokens)
        except Open115Error:
            logger.warning("115 Open token refresh failed")
            return False
        return bool(self.access_token)

    @staticmethod
    def _consume_refresh_waiter(waiter: asyncio.Future[bool]) -> None:
        try:
            waiter.result()
        except BaseException:
            pass

    async def import_refresh_token(self, refresh_token: str) -> dict[str, bool]:
        normalized = str(refresh_token or "").strip()
        if not normalized:
            raise Open115Error(None, "refresh token 不能为空")
        self._persist_settings({
            "access_token": "",
            "refresh_token": normalized,
            "token_expires_at": 0,
            "verified": False,
        })
        if not await self.refresh_access_token(expected_access_token=""):
            raise Open115AuthRequired(None, "refresh token 无效")
        return {"bound": True}

    def unbind(self) -> None:
        if os.getenv("OPEN115_REFRESH_TOKEN"):
            raise Open115Error(None, "115 授权由环境变量管理，无法通过设置页解绑")
        self._persist_settings({
            "access_token": "",
            "refresh_token": "",
            "token_expires_at": 0,
            "verified": False,
        })
        self._pending_auth.clear()
        self._folder_cache = {"/": "0"}

    def _persist_tokens(self, token_data: dict[str, Any], *, verified: bool | None = None) -> None:
        access_token = str(token_data.get("access_token") or "").strip()
        refresh_token = str(token_data.get("refresh_token") or "").strip()
        if not access_token or not refresh_token:
            raise Open115Error(None, "115 授权响应缺少 token")
        expires_in = _as_int(token_data.get("expires_in"))
        updates = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": int(time.time()) + expires_in if expires_in > 0 else 0,
        }
        if verified is not None:
            updates["verified"] = verified
        self._persist_settings(updates)

    def _persist_settings(self, updates: dict[str, Any]) -> None:
        config_path = Path(self._config.config_path)
        with self._persist_lock:
            try:
                if config_path.exists():
                    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                else:
                    data = dict(self._config._config)
                section = data.setdefault("open115", {})
                if not isinstance(section, dict):
                    section = {}
                    data["open115"] = section
                section.update(updates)
                config_path.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary_path = tempfile.mkstemp(
                    prefix=f".{config_path.name}.",
                    suffix=".tmp",
                    dir=config_path.parent,
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as handle:
                        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary_path, config_path)
                finally:
                    if os.path.exists(temporary_path):
                        os.unlink(temporary_path)
                current = self._config._config.setdefault("open115", {})
                if not isinstance(current, dict):
                    current = {}
                    self._config._config["open115"] = current
                current.update(updates)
            except OSError as exc:
                raise Open115Error(None, "无法保存 115 授权配置") from exc

    async def test_connection(self) -> dict[str, Any]:
        try:
            user = await self.user_info()
        except Open115Error:
            self._persist_settings({"verified": False})
            raise
        self._persist_settings({"verified": True})
        return {
            "ok": True,
            "user_id": str(user.get("user_id") or ""),
            "user_name": str(user.get("user_name") or ""),
        }

    async def user_info(self) -> dict[str, Any]:
        payload = await self._auth_request("GET", "/open/user/info")
        return payload if isinstance(payload, dict) else {}

    async def get_folder_info(self, file_id: str) -> dict[str, Any]:
        payload = await self._auth_request(
            "GET",
            "/open/folder/get_info",
            params={"file_id": str(file_id)},
        )
        if isinstance(payload, list):
            return payload[0] if payload and isinstance(payload[0], dict) else {}
        return payload if isinstance(payload, dict) else {}

    async def mkdir(self, parent_id: str, name: str) -> str:
        payload = await self._auth_request(
            "POST",
            "/open/folder/add",
            data={"pid": str(parent_id), "file_name": name},
        )
        folder_id = str((payload or {}).get("file_id") or "") if isinstance(payload, dict) else ""
        if not folder_id:
            raise Open115Error(None, "115 创建目录未返回 file_id")
        return folder_id

    async def ensure_folder_path(self, path: str) -> str:
        normalized = "/" + str(path or "").strip("/")
        if normalized == "/":
            return "0"
        cached = self._folder_cache.get(normalized)
        if cached:
            return cached
        parent_id = "0"
        current_path = ""
        for name in [part for part in normalized.split("/") if part]:
            current_path += f"/{name}"
            cached = self._folder_cache.get(current_path)
            if cached:
                parent_id = cached
                continue
            existing_id = ""
            async for item in self.iter_files(parent_id):
                if item.is_dir and item.name == name:
                    existing_id = item.file_id
                    break
            parent_id = existing_id or await self.mkdir(parent_id, name)
            self._folder_cache[current_path] = parent_id
        return parent_id

    async def list_files(
        self,
        folder_id: str,
        *,
        offset: int = 0,
        limit: int = FILES_PAGE_SIZE,
    ) -> list[Open115File]:
        payload = await self._auth_request(
            "GET",
            "/open/ufile/files",
            params={
                "cid": str(folder_id),
                "offset": max(0, int(offset)),
                "limit": max(1, min(int(limit), FILES_PAGE_SIZE)),
                "show_dir": 1,
                "cur": 1,
            },
        )
        if isinstance(payload, dict):
            items = payload.get("data") or payload.get("files") or []
        else:
            items = payload or []
        return [
            Open115File.from_api(item)
            for item in items
            if isinstance(item, dict)
        ]

    async def list_folder(
        self,
        folder_id: str,
        *,
        offset: int = 0,
        limit: int = FILES_PAGE_SIZE,
        order: str | None = None,
        asc: int | None = None,
    ) -> dict[str, Any]:
        """List one page of a folder, including breadcrumb path and total count.

        ``order`` maps to 115's ``o`` sort field (``file_name`` / ``file_size`` /
        ``user_utime``; any other value collapses to ``user_utime``). ``asc`` is
        1 (ascending) or 0 (descending). When unset, 115's default ordering is
        used (modify time, descending)."""
        params: dict[str, Any] = {
            "cid": str(folder_id),
            "offset": max(0, int(offset)),
            "limit": max(1, min(int(limit), FILES_PAGE_SIZE)),
            "show_dir": 1,
            "cur": 1,
        }
        if order:
            params["o"] = order
        if asc is not None:
            params["asc"] = 1 if int(asc) else 0
        body = await self._auth_request(
            "GET",
            "/open/ufile/files",
            params=params,
            full=True,
        )
        body = body if isinstance(body, dict) else {}
        items = body.get("data")
        files = [Open115File.from_api(item) for item in (items or []) if isinstance(item, dict)]
        breadcrumb = [
            {
                "file_id": str(crumb.get("cid") or crumb.get("file_id") or ""),
                "name": str(crumb.get("name") or ""),
            }
            for crumb in (body.get("path") or [])
            if isinstance(crumb, dict)
        ]
        return {
            "files": files,
            "path": breadcrumb,
            "count": _as_int(body.get("count"), len(files)),
        }

    async def iter_files(self, folder_id: str) -> AsyncIterator[Open115File]:
        offset = 0
        while True:
            files = await self.list_files(folder_id, offset=offset, limit=FILES_PAGE_SIZE)
            for item in files:
                yield item
            if len(files) < FILES_PAGE_SIZE:
                return
            offset += FILES_PAGE_SIZE

    async def walk_files(self, file_or_folder_id: str) -> AsyncIterator[Open115File]:
        info = Open115File.from_api(await self.get_folder_info(file_or_folder_id))
        if info.file_id and not info.is_dir:
            yield info
            return
        async for item in self.iter_files(file_or_folder_id):
            if item.is_dir:
                async for child in self.walk_files(item.file_id):
                    yield child
            else:
                yield item

    async def add_offline_task(self, urls: Iterable[str], folder_id: str) -> list[str]:
        normalized = [str(url).strip() for url in urls if str(url).strip()]
        if not normalized:
            raise Open115Error(None, "离线下载链接不能为空")
        payload = await self._auth_request(
            "POST",
            "/open/offline/add_task_urls",
            data={"urls": "\n".join(normalized), "wp_path_id": str(folder_id)},
        )
        rows = payload if isinstance(payload, list) else []
        hashes = [
            str(item.get("info_hash") or "")
            for item in rows
            if isinstance(item, dict) and item.get("state") and item.get("info_hash")
        ]
        if not hashes:
            raise Open115Error(None, "115 未接受离线下载任务")
        return hashes

    async def list_offline_tasks(self, page: int = 1) -> dict[str, Any]:
        payload = await self._auth_request(
            "GET",
            "/open/offline/get_task_list",
            params={"page": max(1, int(page))},
        )
        return payload if isinstance(payload, dict) else {}

    async def offline_quota(self) -> dict[str, int]:
        """Monthly cloud-download quota. Normalized to total/used/remain; field
        names vary across 115 responses so we read several aliases and backfill
        ``remain`` when only total/used are present."""
        payload = await self._auth_request("GET", "/open/offline/get_quota_info")
        data = payload if isinstance(payload, dict) else {}
        total = _as_int(data.get("total") or data.get("count") or data.get("quota"))
        used = _as_int(data.get("used") or data.get("used_count"))
        remain_raw = data.get("remain")
        if remain_raw is None:
            remain_raw = data.get("surplus")
        remain = _as_int(remain_raw) if remain_raw is not None else max(0, total - used)
        return {"total": total, "used": used, "remain": remain}

    async def delete_offline_task(self, info_hash: str, *, del_source: bool = False) -> None:
        wanted = str(info_hash or "").strip()
        if not wanted:
            raise Open115Error(None, "删除离线任务需要 info_hash")
        await self._auth_request(
            "POST",
            "/open/offline/del_task",
            data={"info_hash": wanted, "del_source_file": 1 if del_source else 0},
        )

    async def clear_offline_tasks(self, flag: int = 0) -> None:
        """Clear cloud-download tasks. ``flag``: 0 已完成 / 1 全部 / 2 已失败 /
        3 进行中 / 4 已完成+删源 / 5 全部+删源。"""
        await self._auth_request(
            "POST",
            "/open/offline/clear_task",
            data={"flag": int(flag)},
        )

    async def delete_files(
        self,
        file_ids: Iterable[str],
        parent_id: str | None = None,
    ) -> None:
        normalized = [str(file_id).strip() for file_id in file_ids if str(file_id or "").strip()]
        if not normalized:
            return
        data = {"file_ids": ",".join(normalized)}
        normalized_parent_id = str(parent_id or "").strip()
        if normalized_parent_id:
            data["parent_id"] = normalized_parent_id
        await self._auth_request(
            "POST",
            "/open/ufile/delete",
            data=data,
        )

    async def rename_file(self, file_id: str, new_name: str) -> None:
        normalized_id = str(file_id or "").strip()
        name = str(new_name or "").strip()
        if not normalized_id or not name:
            raise Open115Error(None, "重命名需要 file_id 和新名称")
        await self._auth_request(
            "POST",
            "/open/ufile/update",
            data={"file_id": normalized_id, "file_name": name},
        )

    async def move_files(self, file_ids: Iterable[str], to_cid: str) -> int:
        normalized = [str(file_id).strip() for file_id in file_ids if str(file_id or "").strip()]
        if not normalized:
            return 0
        await self._auth_request(
            "POST",
            "/open/ufile/move",
            data={"file_ids": ",".join(normalized), "to_cid": str(to_cid)},
        )
        return len(normalized)

    async def copy_files(self, file_ids: Iterable[str], to_cid: str) -> int:
        normalized = [str(file_id).strip() for file_id in file_ids if str(file_id or "").strip()]
        if not normalized:
            return 0
        await self._auth_request(
            "POST",
            "/open/ufile/copy",
            data={"file_id": ",".join(normalized), "pid": str(to_cid)},
        )
        return len(normalized)

    async def search_files(
        self,
        keyword: str,
        *,
        cid: str = "0",
        offset: int = 0,
        limit: int = FILES_PAGE_SIZE,
    ) -> list[Open115File]:
        value = str(keyword or "").strip()
        if not value:
            return []
        payload = await self._auth_request(
            "GET",
            "/open/ufile/search",
            params={
                "search_value": value,
                "cid": str(cid),
                "offset": max(0, int(offset)),
                "limit": max(1, min(int(limit), FILES_PAGE_SIZE)),
            },
        )
        if isinstance(payload, dict):
            items = payload.get("data") or payload.get("files") or []
        else:
            items = payload or []
        return [Open115File.from_api(item) for item in items if isinstance(item, dict)]

    async def downurl(self, pick_code: str, user_agent: str) -> str:
        effective_ua = str(user_agent or "").strip() or self.default_ua
        payload = await self._auth_request(
            "POST",
            "/open/ufile/downurl",
            data={"pick_code": pick_code},
            user_agent=effective_ua,
        )
        if isinstance(payload, dict):
            for item in payload.values():
                if not isinstance(item, dict):
                    continue
                url_data = item.get("url")
                url = url_data.get("url") if isinstance(url_data, dict) else ""
                if url:
                    return str(url)
        raise Open115Error(None, "115 未返回原画地址")

    async def video_transcode_urls(self, pick_code: str) -> list[TranscodeURL]:
        payload = await self._auth_request(
            "GET",
            "/open/video/play",
            params={"pick_code": pick_code},
        )
        rows = payload.get("video_url") if isinstance(payload, dict) else []
        result = [
            TranscodeURL(
                url=str(item.get("url") or ""),
                definition=_as_int(item.get("definition")),
                desc=str(item.get("desc") or ""),
            )
            for item in (rows or [])
            if isinstance(item, dict) and item.get("url")
        ]
        return sorted(result, key=lambda item: item.definition, reverse=True)


open115_client = Open115Client()
