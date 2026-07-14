from __future__ import annotations

import asyncio
import re
from typing import Any

from database.avdb import search_avdb_records
from models.video import MagnetInfo
from modules.code_matcher import normalize_code


class AvdbSource:
    """Local PostgreSQL index built from the AVdb-Only public release feed."""

    def __init__(
        self,
        *,
        name: str = "avdb",
        enabled: bool = False,
        result_limit: int = 50,
        **_settings: Any,
    ) -> None:
        self.name = str(name or "avdb").strip() or "avdb"
        self.enabled = bool(enabled)
        self.result_limit = max(1, min(int(result_limit), 200))

    def is_implemented(self) -> bool:
        return self.enabled

    async def search(self, keyword: str) -> list[MagnetInfo]:
        normalized = normalize_code(keyword)
        if not self.is_implemented() or not normalized:
            return []
        rows = await asyncio.to_thread(
            search_avdb_records,
            normalized,
            limit=self.result_limit,
        )
        seen: set[str] = set()
        results: list[MagnetInfo] = []
        for row in rows:
            info_hash = str(row.get("info_hash") or "").lower()
            if not info_hash or info_hash in seen:
                continue
            seen.add(info_hash)
            title = str(row.get("title") or "")
            resolution, quality, hd = _quality_flags(title)
            result = {
                "magnet": str(row.get("magnet") or ""),
                "title": title,
                "size": _display_size(row.get("size_text")),
                "quality": quality,
                "resolution": resolution,
                "hd": hd,
                "subtitle": _has_subtitle(title),
                "source": self.name,
                "info_hash": info_hash,
            }
            results.append(result)
        return results

    async def get_detail(self, content_id: str) -> dict | None:
        return None

    async def get_actress_videos(self, actress_name: str) -> list:
        return []


def _display_size(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    # Upstream's numeric size column is expressed in MB (for example 3930 for
    # a roughly 3.8 GB release). Reject sentinel/corrupt values rather than
    # letting them distort candidate ranking.
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        return text
    size_mb = float(text)
    if size_mb <= 0 or size_mb > 128 * 1024:
        return ""
    if size_mb >= 1024:
        return f"{_compact_number(size_mb / 1024)} GB"
    return f"{_compact_number(size_mb)} MB"


def _compact_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _quality_flags(title: str) -> tuple[str | None, str | None, bool]:
    lowered = title.lower()
    resolution = None
    if "2160" in lowered or "4k" in lowered:
        resolution = "2160p"
    elif "1080" in lowered:
        resolution = "1080p"
    elif "720" in lowered:
        resolution = "720p"
    hd = bool(resolution) or any(
        token in lowered for token in (" hd", ".hd", "_hd", "fhd", "uhd", "bluray", "web-dl")
    )
    return resolution, "4K" if resolution == "2160p" else "HD" if hd else None, hd


def _has_subtitle(title: str) -> bool:
    lowered = title.lower()
    return any(
        token in lowered
        for token in ("字幕", "subtitle", "subtitles", " sub", ".sub", "_sub", "chs", "cht", "zh")
    )
