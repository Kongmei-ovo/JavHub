"""Authentication primitives for the Emby compatibility surface."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

from config import config
from services.emby_mapper import SERVER_ID

TOKEN_VERSION = "jh1"
SESSION_TTL_SECONDS = 30 * 60
_TOKEN_RE = re.compile(r'(?:^|[\s,])Token\s*=\s*"?(?P<token>[^",\s]+)', re.IGNORECASE)


class EmbyHTTPException(HTTPException):
    """HTTP exception rendered with Emby's top-level Code/Message envelope."""

    def __init__(self, status_code: int, message: str, code: int | None = None):
        super().__init__(status_code=status_code, detail=message)
        self.emby_code = code if code is not None else status_code


@dataclass(frozen=True)
class _CompatSession:
    token: str
    expires_at: float


_sessions: dict[str, _CompatSession] = {}
_session_lock = threading.Lock()


def clear_compat_sessions() -> None:
    with _session_lock:
        _sessions.clear()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _signing_key(username: str, password: str) -> bytes:
    material = f"{SERVER_ID}\0{username.casefold()}\0{password}".encode("utf-8")
    return hashlib.sha256(material).digest()


def issue_token(username: str, password: str) -> str:
    payload = {
        "sub": "javhub-emby-user",
        "name": username,
        "iat": int(time.time()),
        "nonce": secrets.token_urlsafe(12),
    }
    encoded = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = _b64encode(
        hmac.new(_signing_key(username, password), encoded.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{TOKEN_VERSION}.{encoded}.{signature}"


def verify_token(token: str, username: str, password: str) -> dict[str, Any] | None:
    try:
        version, encoded, signature = token.split(".", 2)
        if version != TOKEN_VERSION:
            return None
        expected = _b64encode(
            hmac.new(
                _signing_key(username, password),
                encoded.encode("ascii"),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64decode(encoded))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if payload.get("sub") != "javhub-emby-user":
        return None
    if str(payload.get("name") or "").casefold() != username.casefold():
        return None
    return payload


def _header(request: Any, name: str) -> str:
    headers = getattr(request, "headers", {}) or {}
    value = headers.get(name)
    if value is None:
        value = headers.get(name.lower())
    return str(value or "").strip()


def extract_token(request: Any) -> str:
    for name in ("X-Emby-Token", "X-MediaBrowser-Token"):
        value = _header(request, name)
        if value:
            return value

    for name in ("Authorization", "X-Emby-Authorization", "X-MediaBrowser-Authorization"):
        value = _header(request, name)
        if not value:
            continue
        lowered = value.lower()
        for prefix in ("bearer ", "emby "):
            if lowered.startswith(prefix):
                return value[len(prefix):].strip()
        match = _TOKEN_RE.search(value)
        if match:
            return match.group("token")

    query = getattr(request, "query_params", {}) or {}
    for key in (
        "token",
        "api_key",
        "apiKey",
        "ApiKey",
        "X-Emby-Token",
        "X-MediaBrowser-Token",
    ):
        value = query.get(key)
        if value:
            return str(value).strip()
    return ""


def _session_keys(request: Any) -> list[str]:
    client = getattr(request, "client", None)
    ip = str(getattr(client, "host", "") or "")
    headers = getattr(request, "headers", {}) or {}
    device_id = (
        headers.get("X-Emby-Device-Id")
        or headers.get("X-Emby-DeviceId")
        or headers.get("X-MediaBrowser-Device-Id")
        or headers.get("X-MediaBrowser-DeviceId")
        or ""
    )
    user_agent = headers.get("User-Agent") or headers.get("user-agent") or ""
    prefix = ip or "unknown"
    result = []
    if device_id:
        result.append(f"{prefix}\0device\0{device_id}")
    if user_agent:
        result.append(f"{prefix}\0ua\0{user_agent}")
    return result


def remember_session(request: Any, token: str) -> None:
    keys = _session_keys(request)
    if not keys:
        return
    expires_at = time.time() + SESSION_TTL_SECONDS
    with _session_lock:
        now = time.time()
        if len(_sessions) > 1000:
            expired = [key for key, session in _sessions.items() if session.expires_at <= now]
            for key in expired:
                _sessions.pop(key, None)
        for key in keys:
            _sessions[key] = _CompatSession(token=token, expires_at=expires_at)


def _session_token(request: Any) -> str:
    now = time.time()
    with _session_lock:
        for key in _session_keys(request):
            session = _sessions.get(key)
            if session and session.expires_at > now:
                return session.token
    return ""


def require_auth(request: Request, username: str, password: str) -> str:
    token = extract_token(request) or _session_token(request)
    if not token or verify_token(token, username, password) is None:
        raise EmbyHTTPException(401, "Unauthorized", code=40101)
    remember_session(request, token)
    return token


def require_app_token(request: Request) -> str:
    """FastAPI dependency for first-party (non-Emby) endpoints. Same single-user
    credential as the Emby compat layer; accepts the token via header, query
    (?token=/api_key=, needed for browser-issued HLS sub-requests), or session."""
    return require_auth(request, config.emby_compat_username, config.emby_compat_password)
