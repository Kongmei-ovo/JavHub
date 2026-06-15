"""JavInfo filmography fetcher backing subscription scope checks.

Pulls an actress/maker/series/label's complete filmography from JavInfoApi.
Existence and trigger decisions live in ``services/subscription.py`` (resource
library + persistent baseline); this is a thin paginating fetcher with no Emby
coupling.
"""
from __future__ import annotations

import asyncio


class WatchlistPipeline:
    def __init__(self, info_client=None):
        self.info_client = info_client

    async def _info(self):
        if self.info_client is None:
            from modules.info_client import get_info_client
            self.info_client = get_info_client()
        return self.info_client

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
