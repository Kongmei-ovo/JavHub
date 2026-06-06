"""Subscription/inventory pipeline that produces download candidates."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from database import (
    candidate_content_id,
    download_candidate_content_keys,
    is_video_exempt,
    upsert_candidate_from_video,
)


def normalize_code(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def video_code(video: dict) -> str:
    return str(video.get("dvd_id") or video.get("content_id") or video.get("canonical_number") or "").strip()


def video_in_snapshot(video: dict, snapshot_items: Iterable[dict] | None) -> bool:
    """Match a JavInfo video against Emby snapshot titles/filenames."""
    code = video_code(video)
    normalized = normalize_code(code)
    if not normalized:
        return False
    for item in snapshot_items or []:
        haystack = " ".join([
            str(item.get("filename") or ""),
            str(item.get("title") or ""),
            str(item.get("Name") or ""),
            str(item.get("FileName") or ""),
        ])
        if normalized and normalized in normalize_code(haystack):
            return True
    return False


@dataclass
class PipelineStats:
    checked: int = 0
    created: int = 0
    existing: int = 0
    skipped: int = 0
    in_library: int = 0
    candidates: list[dict] = field(default_factory=list)
    skipped_exempt: int = 0

    def as_dict(self) -> dict:
        return {
            "checked": self.checked,
            "created": self.created,
            "existing": self.existing,
            "skipped": self.skipped,
            "skipped_exempt": self.skipped_exempt,
            "in_library": self.in_library,
            "candidate_count": len(self.candidates),
            "candidates": self.candidates,
            # Backward-compatible subscription naming.
            "new_movies_count": len(self.candidates),
            "new_movies": [
                {
                    "code": c.get("dvd_id") or c.get("content_id"),
                    "content_id": c.get("content_id"),
                    "dvd_id": c.get("dvd_id"),
                    "title": c.get("title"),
                    "release_date": c.get("release_date"),
                    "actress_name": c.get("actress_name"),
                    "candidate_id": c.get("id"),
                }
                for c in self.candidates
            ],
        }


class WatchlistPipeline:
    def __init__(self, info_client=None, emby_client=None):
        self.info_client = info_client
        self.emby_client = emby_client

    async def _info(self):
        if self.info_client is None:
            from modules.info_client import get_info_client
            self.info_client = get_info_client()
        return self.info_client

    async def _emby(self):
        if self.emby_client is None:
            from modules.emby_client import get_emby_client
            self.emby_client = get_emby_client()
        return self.emby_client

    async def fetch_actress_videos(self, actress_id: int, page_size: int = 100) -> list[dict]:
        info = await self._info()
        safe_page_size = max(1, min(int(page_size or 100), 100))
        page = 1
        videos: list[dict] = []

        while True:
            result = await info.get_actress_videos(
                actress_id,
                page=page,
                page_size=safe_page_size,
                include_supplement="1",
            )
            rows = result.get("data", []) if isinstance(result, dict) else result
            rows = rows if isinstance(rows, list) else []
            videos.extend(rows)

            total_pages = result.get("total_pages") if isinstance(result, dict) else None
            if isinstance(total_pages, int):
                if page >= total_pages:
                    break
            elif len(rows) < safe_page_size:
                break
            page += 1

        return videos

    async def generate_candidates_for_actress(
        self,
        actress_id: int,
        actress_name: str = "",
        trigger_source: str = "subscription",
        reason: str = "",
        emby_snapshot: list[dict] | None = None,
        page_size: int = 100,
    ) -> dict:
        """Fetch complete filmography and upsert candidates for missing movies."""
        stats = PipelineStats()
        videos = await self.fetch_actress_videos(actress_id, page_size=page_size)
        existing_candidates = download_candidate_content_keys(actress_id=actress_id, source=trigger_source)
        emby = None if emby_snapshot is not None else await self._emby()

        for video in videos:
            content_id = candidate_content_id(video)
            code = video_code(video)
            if not content_id or not code:
                stats.skipped += 1
                continue
            stats.checked += 1

            if is_video_exempt(content_id) or is_video_exempt(code):
                stats.skipped += 1
                stats.skipped_exempt += 1
                continue

            if emby_snapshot is not None:
                exists = video_in_snapshot(video, emby_snapshot)
            else:
                exists = await emby.check_exists(code)

            if exists:
                stats.in_library += 1
                continue

            existed = (content_id, trigger_source) in existing_candidates
            candidate = upsert_candidate_from_video(
                video=video,
                actress_id=actress_id,
                actress_name=actress_name,
                source=trigger_source,
                reason=reason or trigger_source,
            )
            stats.candidates.append(candidate)
            if existed:
                stats.existing += 1
            else:
                stats.created += 1
                existing_candidates.add((content_id, trigger_source))

        return stats.as_dict()
