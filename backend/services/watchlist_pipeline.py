"""Subscription/inventory pipeline that produces download candidates."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Iterable

from database import (
    candidate_content_id,
    download_candidate_content_keys,
    is_video_exempt,
    upsert_candidate_from_video,
)
from modules.code_matcher import (
    code_matches_text as _code_matches_haystack,
    normalize_code,
    video_code,
)


__all__ = [
    "WatchlistPipeline",
    "normalize_code",
    "video_code",
    "video_in_snapshot",
    "video_in_snapshot_match",
    "video_in_existing_codes",
]


def video_in_snapshot_match(video: dict, snapshot_items: Iterable[dict] | None) -> dict | None:
    """Return the matching Emby snapshot row for a JavInfo video, if any."""
    code = video_code(video)
    if not normalize_code(code):
        return None
    for item in snapshot_items or []:
        haystack = " ".join([
            str(item.get("filename") or ""),
            str(item.get("title") or ""),
            str(item.get("Name") or ""),
            str(item.get("FileName") or ""),
        ])
        if _code_matches_haystack(code, haystack):
            return item
    return None


def video_in_snapshot(video: dict, snapshot_items: Iterable[dict] | None) -> bool:
    """Match a JavInfo video against Emby snapshot titles/filenames."""
    return video_in_snapshot_match(video, snapshot_items) is not None


def video_in_existing_codes(video: dict, existing_codes: set[str] | None) -> bool:
    normalized = normalize_code(video_code(video))
    return bool(normalized and existing_codes is not None and normalized in existing_codes)


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

    async def fetch_actress_videos(
        self,
        actress_id: int,
        page_size: int = 100,
        info_semaphore: asyncio.Semaphore | None = None,
    ) -> list[dict]:
        info = await self._info()
        return await self._fetch_scope_videos(
            lambda page, safe_page_size: info.get_actress_videos(
                actress_id,
                page=page,
                page_size=safe_page_size,
                include_supplement="1",
            ),
            page_size=page_size,
            info_semaphore=info_semaphore,
        )

    async def fetch_maker_videos(
        self,
        maker_id: int,
        page_size: int = 100,
        info_semaphore: asyncio.Semaphore | None = None,
    ) -> list[dict]:
        info = await self._info()
        return await self._fetch_scope_videos(
            lambda page, safe_page_size: info.get_maker_videos(maker_id, page=page, page_size=safe_page_size),
            page_size=page_size,
            info_semaphore=info_semaphore,
        )

    async def fetch_series_videos(
        self,
        series_id: int,
        page_size: int = 100,
        info_semaphore: asyncio.Semaphore | None = None,
    ) -> list[dict]:
        info = await self._info()
        return await self._fetch_scope_videos(
            lambda page, safe_page_size: info.get_series_videos(series_id, page=page, page_size=safe_page_size),
            page_size=page_size,
            info_semaphore=info_semaphore,
        )

    async def fetch_label_videos(
        self,
        label_id: int,
        page_size: int = 100,
        info_semaphore: asyncio.Semaphore | None = None,
    ) -> list[dict]:
        info = await self._info()
        return await self._fetch_scope_videos(
            lambda page, safe_page_size: info.get_label_videos(label_id, page=page, page_size=safe_page_size),
            page_size=page_size,
            info_semaphore=info_semaphore,
        )

    async def _fetch_scope_videos(
        self,
        fetch_page,
        page_size: int = 100,
        info_semaphore: asyncio.Semaphore | None = None,
    ) -> list[dict]:
        safe_page_size = max(1, min(int(page_size or 100), 100))
        page = 1
        videos: list[dict] = []

        while True:
            if info_semaphore is None:
                result = await fetch_page(page, safe_page_size)
            else:
                async with info_semaphore:
                    result = await fetch_page(page, safe_page_size)
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

    async def _generate_candidates_for_videos(
        self,
        videos: list[dict],
        *,
        actress_id: int | None,
        actress_name: str,
        trigger_source: str,
        reason: str,
        emby_snapshot: list[dict] | None,
        existing_codes: set[str] | None = None,
    ) -> dict:
        from modules.emby_client import EmbyUnavailableError

        stats = PipelineStats()
        existing_candidates = download_candidate_content_keys(actress_id=actress_id, source=trigger_source)
        emby = None if emby_snapshot is not None or existing_codes is not None else await self._emby()
        # When we have to query Emby live, bail out the moment it starts erroring —
        # the alternative is mass-flagging the actor as "all missing" and queueing
        # thousands of false candidates.
        emby_failure_streak = 0
        emby_aborted = False

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

            if existing_codes is not None:
                exists = video_in_existing_codes(video, existing_codes)
            elif emby_snapshot is not None:
                exists = video_in_snapshot_match(video, emby_snapshot) is not None
            else:
                try:
                    exists = await emby.check_exists(code)
                    emby_failure_streak = 0
                except EmbyUnavailableError:
                    emby_failure_streak += 1
                    if emby_failure_streak >= 3:
                        emby_aborted = True
                        break
                    stats.skipped += 1
                    continue

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

        result = stats.as_dict()
        if emby_aborted:
            result["emby_unavailable"] = True
        return result

    async def generate_candidates_for_actress(
        self,
        actress_id: int,
        actress_name: str = "",
        trigger_source: str = "subscription",
        reason: str = "",
        emby_snapshot: list[dict] | None = None,
        existing_codes: set[str] | None = None,
        info_semaphore: asyncio.Semaphore | None = None,
        page_size: int = 100,
    ) -> dict:
        """Fetch complete filmography and upsert candidates for missing movies."""
        videos = await self.fetch_actress_videos(
            actress_id,
            page_size=page_size,
            info_semaphore=info_semaphore,
        )
        return await self._generate_candidates_for_videos(
            videos,
            actress_id=actress_id,
            actress_name=actress_name,
            trigger_source=trigger_source,
            reason=reason,
            emby_snapshot=emby_snapshot,
            existing_codes=existing_codes,
        )

    async def _generate_candidates_for_scope(
        self,
        scope: str,
        target_id: int,
        target_label: str = "",
        trigger_source: str = "subscription",
        reason: str = "",
        emby_snapshot: list[dict] | None = None,
        existing_codes: set[str] | None = None,
        info_semaphore: asyncio.Semaphore | None = None,
        page_size: int = 100,
    ) -> dict:
        fetchers = {
            "maker": self.fetch_maker_videos,
            "series": self.fetch_series_videos,
            "label": self.fetch_label_videos,
        }
        videos = await fetchers[scope](
            target_id,
            page_size=page_size,
            info_semaphore=info_semaphore,
        )
        result = await self._generate_candidates_for_videos(
            videos,
            actress_id=None,
            actress_name=target_label,
            trigger_source=trigger_source,
            reason=reason,
            emby_snapshot=emby_snapshot,
            existing_codes=existing_codes,
        )
        result.update({
            "scope": scope,
            "target_id": target_id,
            "target_label": target_label,
        })
        return result

    async def generate_candidates_for_maker(
        self,
        target_id: int,
        target_label: str = "",
        trigger_source: str = "subscription",
        reason: str = "",
        emby_snapshot: list[dict] | None = None,
        existing_codes: set[str] | None = None,
        info_semaphore: asyncio.Semaphore | None = None,
        page_size: int = 100,
    ) -> dict:
        return await self._generate_candidates_for_scope(
            scope="maker",
            target_id=target_id,
            target_label=target_label,
            trigger_source=trigger_source,
            reason=reason,
            emby_snapshot=emby_snapshot,
            existing_codes=existing_codes,
            info_semaphore=info_semaphore,
            page_size=page_size,
        )

    async def generate_candidates_for_series(
        self,
        target_id: int,
        target_label: str = "",
        trigger_source: str = "subscription",
        reason: str = "",
        emby_snapshot: list[dict] | None = None,
        existing_codes: set[str] | None = None,
        info_semaphore: asyncio.Semaphore | None = None,
        page_size: int = 100,
    ) -> dict:
        return await self._generate_candidates_for_scope(
            scope="series",
            target_id=target_id,
            target_label=target_label,
            trigger_source=trigger_source,
            reason=reason,
            emby_snapshot=emby_snapshot,
            existing_codes=existing_codes,
            info_semaphore=info_semaphore,
            page_size=page_size,
        )

    async def generate_candidates_for_label(
        self,
        target_id: int,
        target_label: str = "",
        trigger_source: str = "subscription",
        reason: str = "",
        emby_snapshot: list[dict] | None = None,
        existing_codes: set[str] | None = None,
        info_semaphore: asyncio.Semaphore | None = None,
        page_size: int = 100,
    ) -> dict:
        return await self._generate_candidates_for_scope(
            scope="label",
            target_id=target_id,
            target_label=target_label,
            trigger_source=trigger_source,
            reason=reason,
            emby_snapshot=emby_snapshot,
            existing_codes=existing_codes,
            info_semaphore=info_semaphore,
            page_size=page_size,
        )
