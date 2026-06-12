"""Playback policy and ephemeral HLS proxy sessions."""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Literal

PlaybackMode = Literal["auto", "original", "hls"]
Caller = Literal["web", "emby", "infuse", "vidhub", "iina", "external"]

WEB_ORIGINAL_EXTENSIONS = {"mp4", "webm"}
WEB_HLS_EXTENSIONS = {"mkv", "avi", "wmv", "m2ts", "ts", "iso", "mov", "m4v"}
VALID_MODES = {"auto", "original", "hls"}


def _caller_from_user_agent(user_agent: str, hint: str = "") -> Caller:
    normalized_hint = str(hint or "").strip().lower()
    if normalized_hint in {"web", "emby", "infuse", "vidhub", "iina", "external"}:
        return normalized_hint  # type: ignore[return-value]
    ua = str(user_agent or "").lower()
    if "infuse" in ua:
        return "infuse"
    if "vidhub" in ua:
        return "vidhub"
    if "iina" in ua:
        return "iina"
    if "emby" in ua or "mediabrowser" in ua:
        return "emby"
    if "mozilla/" in ua or "chrome/" in ua or "safari/" in ua:
        return "web"
    return "external"


@dataclass(frozen=True)
class PlaybackContext:
    user_agent: str
    caller: Caller
    requested_mode: PlaybackMode
    preferred_mode: Literal["original", "hls"]
    extension: str
    accepts_hls: bool

    @classmethod
    def build(
        cls,
        *,
        user_agent: str,
        accept: str,
        mode: str,
        extension: str,
        caller_hint: str = "",
    ) -> "PlaybackContext":
        normalized_mode = str(mode or "auto").lower()
        if normalized_mode not in VALID_MODES:
            raise ValueError("mode must be auto, original, or hls")
        normalized_extension = str(extension or "").lower().lstrip(".")
        caller = _caller_from_user_agent(user_agent, caller_hint)
        accepts_hls = (
            caller == "web"
            or "mpegurl" in str(accept or "").lower()
            or caller in {"emby", "infuse", "vidhub", "iina", "external"}
        )
        if normalized_mode in {"original", "hls"}:
            preferred = normalized_mode
        elif caller != "web":
            preferred = "original"
        elif normalized_extension in WEB_ORIGINAL_EXTENSIONS:
            preferred = "original"
        else:
            preferred = "hls"
        return cls(
            user_agent=str(user_agent or ""),
            caller=caller,
            requested_mode=normalized_mode,  # type: ignore[arg-type]
            preferred_mode=preferred,  # type: ignore[arg-type]
            extension=normalized_extension,
            accepts_hls=accepts_hls,
        )


@dataclass
class HLSPlaybackSession:
    session_id: str
    resource_id: int
    user_agent: str
    expires_at: float
    targets: dict[str, str] = field(default_factory=dict)
    target_tokens: dict[str, str] = field(default_factory=dict)


class HLSPlaybackSessionStore:
    def __init__(self, *, ttl_seconds: int = 900, max_sessions: int = 256):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, HLSPlaybackSession] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)
        while len(self._sessions) >= self.max_sessions:
            oldest = min(self._sessions.values(), key=lambda item: item.expires_at)
            self._sessions.pop(oldest.session_id, None)

    def create(self, *, resource_id: int, root_url: str, user_agent: str) -> str:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            session_id = secrets.token_urlsafe(18)
            self._sessions[session_id] = HLSPlaybackSession(
                session_id=session_id,
                resource_id=int(resource_id),
                user_agent=str(user_agent or ""),
                expires_at=now + self.ttl_seconds,
                targets={"root": str(root_url)},
                target_tokens={str(root_url): "root"},
            )
            return session_id

    def get(self, session_id: str, resource_id: int) -> HLSPlaybackSession | None:
        now = time.monotonic()
        with self._lock:
            session = self._sessions.get(str(session_id))
            if session is None or session.resource_id != int(resource_id) or session.expires_at <= now:
                self._sessions.pop(str(session_id), None)
                return None
            return session

    def register_target(self, session: HLSPlaybackSession, url: str) -> str:
        with self._lock:
            existing = session.target_tokens.get(str(url))
            if existing:
                return existing
            token = secrets.token_urlsafe(12)
            session.targets[token] = str(url)
            session.target_tokens[str(url)] = token
            return token


hls_sessions = HLSPlaybackSessionStore()
