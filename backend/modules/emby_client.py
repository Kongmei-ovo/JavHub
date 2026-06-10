from __future__ import annotations
import asyncio
import httpx
import logging
import time
from typing import Any
from difflib import SequenceMatcher

from modules.code_matcher import code_matches_text, extract_code, normalize_code

logger = logging.getLogger(__name__)


class EmbyUnavailableError(RuntimeError):
    """Raised when Emby cannot be reached or rejects the request.

    Distinct from "lookup succeeded but the item is not in the library" — the
    caller must not treat this as confirmation that an item is missing.
    """


class EmbyClient:
    """Emby API 客户端"""

    _EXISTS_CACHE_TTL_SECONDS = 30.0

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._exists_cache: dict[str, tuple[float, dict | None]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        # The cached client is bound to the loop that created it; this singleton
        # is reused from both the FastAPI request loop and the shared background
        # job loop, so rebuild whenever the running loop changed (or the client
        # was closed) to avoid cross-loop hangs / "Event loop is closed".
        loop = asyncio.get_running_loop()
        if self._client is None or self._client.is_closed or self._client_loop is not loop:
            previous = self._client
            previous_loop = self._client_loop
            self._client = httpx.AsyncClient(
                headers={"X-Emby-Token": self.api_key},
                timeout=30,
            )
            self._client_loop = loop
            if previous is not None and not previous.is_closed:
                # Best-effort cleanup of the old loop's client; if its loop is
                # already gone we can't await close from here, so just log.
                if previous_loop is not None and not previous_loop.is_closed():
                    try:
                        previous_loop.call_soon_threadsafe(
                            lambda: asyncio.ensure_future(previous.aclose(), loop=previous_loop)
                        )
                    except RuntimeError:
                        logger.debug("Could not schedule aclose on previous emby client")
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, params: dict | None = None) -> Any:
        client = await self._get_client()
        response = await client.get(f"{self.api_url}{path}", params=params)
        response.raise_for_status()
        return response.json()

    # === 库检测 ===

    def _normalize_content_id(self, content_id: str) -> str:
        return (content_id or "").strip().upper()

    def _item_matches_content_id(self, item: dict, code_upper: str) -> bool:
        name = item.get("Name", "") or item.get("FileName", "")
        return code_matches_text(code_upper, name)

    def clear_exists_cache(self):
        self._exists_cache.clear()

    async def lookup(self, content_id: str) -> dict | None:
        """Return Emby match info for ``content_id`` or ``None`` if not present.

        Raises :class:`EmbyUnavailableError` when Emby cannot be queried — the
        caller must NOT interpret an exception as "missing". Successful "not
        present" results are cached; failures are not, so the next request
        will re-attempt instead of poisoning the cache.
        """
        code_upper = self._normalize_content_id(content_id)
        if not code_upper:
            return None

        now = time.monotonic()
        cached = self._exists_cache.get(code_upper)
        if cached is not None:
            cached_at, cached_result = cached
            if now - cached_at < self._EXISTS_CACHE_TTL_SECONDS:
                return cached_result

        try:
            result = await self._get(
                "/Items",
                params={
                    "limit": 10,
                    "includeItemTypes": "Movie",
                    "recursive": "true",
                    "searchTerm": code_upper,
                }
            )
        except Exception as exc:
            # Do NOT cache failures — otherwise a single Emby blip mass-floods
            # missing/candidate pipelines with false negatives.
            logger.warning("Emby lookup failed for %s: %s", code_upper, exc)
            raise EmbyUnavailableError(str(exc)) from exc

        items = result.get("Items", result.get("items", []))
        for item in items:
            if self._item_matches_content_id(item, code_upper):
                match = {
                    "exists": True,
                    "emby_item_id": item.get("Id"),
                    "name": item.get("Name") or item.get("FileName"),
                }
                self._exists_cache[code_upper] = (now, match)
                return match
        self._exists_cache[code_upper] = (now, None)
        return None

    async def check_exists(self, content_id: str) -> bool:
        """Return True iff Emby confirms the item is present.

        Propagates :class:`EmbyUnavailableError` so callers can distinguish
        "Emby says no" from "Emby could not answer".
        """
        return await self.lookup(content_id) is not None

    async def get_items(self, limit: int = 200, include_people: bool = False) -> list[dict]:
        """获取媒体库中的所有项目（单页，无分页）"""
        try:
            params = {
                "limit": limit,
                "includeItemTypes": "Movie",
                "recursive": "true",
            }
            if include_people:
                params["fields"] = "People"
            result = await self._get("/Items", params=params)
            return result.get("Items", []) if isinstance(result, dict) else result
        except Exception:
            return []

    async def get_items_with_people(
        self,
        limit: int = 500,
        start: int = 0,
        min_date_last_saved: str | None = None,
        include_people: bool = True,
    ) -> dict:
        """分页获取影片（可选含 People 演员信息），返回 {items, totalCount}"""
        try:
            params = {
                "limit": limit,
                "startIndex": start,
                "includeItemTypes": "Movie",
                "recursive": "true",
            }
            fields = ["PremiereDate", "ProductionYear"]
            if include_people:
                fields.insert(0, "People")
            params["fields"] = ",".join(fields)
            if min_date_last_saved:
                params["MinDateLastSaved"] = min_date_last_saved
            result = await self._get(
                "/Items",
                params=params,
            )
            # Emby returns "Items" (capitalized), normalize to lowercase
            if isinstance(result, dict):
                return {
                    "items": result.get("Items", result.get("items", [])),
                    "totalCount": result.get("TotalRecordCount", result.get("totalCount", 0))
                }
            return {"items": [], "totalCount": 0}
        except Exception:
            return {"items": [], "totalCount": 0}

    async def iter_item_ids(self, min_date_last_saved: str | None = None) -> list[str]:
        """Stream every Movie ``Id`` from Emby — cheap (no People, no fields).

        Used by incremental snapshot reconciliation to detect items that were
        deleted on the Emby side so the snapshot can drop them.
        """
        ids: list[str] = []
        start = 0
        page_size = 1000
        while True:
            try:
                params: dict[str, Any] = {
                    "limit": page_size,
                    "startIndex": start,
                    "includeItemTypes": "Movie",
                    "recursive": "true",
                    "fields": "",
                }
                if min_date_last_saved:
                    params["MinDateLastSaved"] = min_date_last_saved
                result = await self._get("/Items", params=params)
            except Exception:
                return ids
            items = result.get("Items", result.get("items", [])) if isinstance(result, dict) else []
            if not items:
                break
            for item in items:
                item_id = item.get("Id")
                if item_id:
                    ids.append(str(item_id))
            total = result.get("TotalRecordCount", result.get("totalCount", 0)) if isinstance(result, dict) else 0
            start += len(items)
            if total and start >= total:
                break
            if len(items) < page_size:
                break
        return ids

    async def collect_all_movies_with_actors(self) -> tuple[list[dict], int]:
        """采集所有影片及其演员信息，返回 (actors_map, total_items)
        actors_map: {actress_id: {actress_id, actress_name, video_count, items: [], image_tag}}
        """
        return await self._collect_movies_with_actors()

    async def collect_incremental_movies_with_actors(self, since_iso: str) -> tuple[list[dict], int]:
        """采集指定时间后保存过的影片及其演员信息。"""
        return await self._collect_movies_with_actors(min_date_last_saved=since_iso)

    async def _collect_movies_with_actors(self, min_date_last_saved: str | None = None) -> tuple[list[dict], int]:
        all_actors: dict[int, dict] = {}
        total = 0
        page_size = 500
        start = 0

        while True:
            result = await self.get_items_with_people(
                limit=page_size,
                start=start,
                min_date_last_saved=min_date_last_saved,
            )
            items = result.get("items", [])
            total_count = result.get("totalCount", 0)
            if total == 0:
                total = total_count

            for item in items:
                people = item.get("People", [])
                item_info = {
                    "item_id": item.get("Id"),
                    "title": item.get("Name", ""),
                    "filename": item.get("FileName", ""),
                    "production_year": item.get("ProductionYear"),
                }
                for person in people:
                    if person.get("Type") != "Actor":
                        continue
                    actress_id = int(person.get("Id"))
                    name = person.get("Name", "Unknown")
                    image_tag = person.get("PrimaryImageTag")
                    if actress_id not in all_actors:
                        all_actors[actress_id] = {
                            "actress_id": actress_id,
                            "actress_name": name,
                            "video_count": 0,
                            "items": [],
                            "image_tag": image_tag,
                        }
                    all_actors[actress_id]["video_count"] += 1
                    all_actors[actress_id]["items"].append(item_info)
                    # 保留第一个出现的 image_tag
                    if image_tag and not all_actors[actress_id].get("image_tag"):
                        all_actors[actress_id]["image_tag"] = image_tag

            start += len(items)
            if start >= total or len(items) == 0:
                break

        return list(all_actors.values()), total

    async def get_all_actresses(self) -> list[dict]:
        """List every Person in Emby tagged as Actor with their movie count.

        Uses ``/Persons`` (server-side) instead of scanning every Movie — both
        much faster and far less RAM on big libraries.
        """
        actors: list[dict] = []
        start = 0
        page_size = 500
        while True:
            try:
                result = await self._get(
                    "/Persons",
                    params={
                        "limit": page_size,
                        "startIndex": start,
                        "includeItemTypes": "Movie",
                        "personTypes": "Actor",
                        "recursive": "true",
                        "fields": "PrimaryImageTag",
                    },
                )
            except Exception:
                break
            items = result.get("Items", result.get("items", [])) if isinstance(result, dict) else []
            if not items:
                break
            for item in items:
                actor_id = item.get("Id")
                if actor_id is None:
                    continue
                try:
                    actor_id_int = int(actor_id)
                except (TypeError, ValueError):
                    continue
                actors.append({
                    "actress_id": actor_id_int,
                    "actress_name": item.get("Name", "Unknown"),
                    "video_count": int(item.get("MovieCount") or 0),
                    "image_tag": item.get("PrimaryImageTag"),
                })
            total = result.get("TotalRecordCount", result.get("totalCount", 0)) if isinstance(result, dict) else 0
            start += len(items)
            if total and start >= total:
                break
            if len(items) < page_size:
                break
        return actors

    async def get_actress_videos(self, actress_id: int) -> list[dict]:
        """Server-side filtered fetch of all Movies for one Person."""
        videos: list[dict] = []
        start = 0
        page_size = 500
        while True:
            try:
                result = await self._get(
                    "/Items",
                    params={
                        "limit": page_size,
                        "startIndex": start,
                        "PersonIds": str(actress_id),
                        "includeItemTypes": "Movie",
                        "recursive": "true",
                        "fields": "People,PremiereDate,ProductionYear",
                    },
                )
            except Exception:
                break
            items = result.get("Items", result.get("items", [])) if isinstance(result, dict) else []
            if not items:
                break
            videos.extend(items)
            total = result.get("TotalRecordCount", result.get("totalCount", 0)) if isinstance(result, dict) else 0
            start += len(items)
            if total and start >= total:
                break
            if len(items) < page_size:
                break
        return videos

    # === 去重相关 ===

    def _extract_code_from_name(self, name: str) -> str | None:
        return extract_code(name)

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, str1.upper(), str2.upper()).ratio()

    async def _iter_movies_no_people(self) -> list[dict]:
        """Pull every Movie (id+name+filename only) using normal pagination."""
        items: list[dict] = []
        start = 0
        page_size = 500
        while True:
            try:
                result = await self._get(
                    "/Items",
                    params={
                        "limit": page_size,
                        "startIndex": start,
                        "includeItemTypes": "Movie",
                        "recursive": "true",
                    },
                )
            except Exception:
                break
            page = result.get("Items", result.get("items", [])) if isinstance(result, dict) else []
            if not page:
                break
            items.extend(page)
            total = result.get("TotalRecordCount", result.get("totalCount", 0)) if isinstance(result, dict) else 0
            start += len(page)
            if total and start >= total:
                break
            if len(page) < page_size:
                break
        return items

    async def find_duplicates(self, info_client) -> list[dict]:
        """Find Emby ↔ JavInfo dup candidates across the whole library."""
        from database import is_duplicate_ignored

        duplicates = []
        embys = await self._iter_movies_no_people()

        # 收集需要查询的番号及其对应的 emby 信息
        code_to_items: dict[str, list[dict]] = {}
        for emby_item in embys:
            emby_id = emby_item.get("Id")
            emby_name = emby_item.get("Name", "")

            if is_duplicate_ignored(emby_id):
                continue

            code = self._extract_code_from_name(emby_name)
            if not code:
                continue

            if code not in code_to_items:
                code_to_items[code] = []
            code_to_items[code].append({"emby_id": emby_id, "emby_name": emby_name, "code": code})

        if not code_to_items:
            return duplicates

        # 批量查找（每批最多100个 dvd_id）
        all_codes = list(code_to_items.keys())
        javinfo_map: dict[str, dict] = {}
        for i in range(0, len(all_codes), 100):
            batch = all_codes[i:i + 100]
            try:
                result = await info_client.batch_lookup_by_dvd_id(batch)
                javinfo_map.update(result)
            except Exception:
                continue

        # 匹配并计算相似度
        for code, emby_items in code_to_items.items():
            javinfo = javinfo_map.get(code)
            if not javinfo:
                continue
            for emby_info in emby_items:
                similarity = self._calculate_similarity(emby_info["emby_name"], javinfo.get("title_en", ""))
                if similarity > 0.5:
                    duplicates.append({
                        "emby_item_id": emby_info["emby_id"],
                        "emby_name": emby_info["emby_name"],
                        "content_id": code,
                        "javinfo_title": javinfo.get("title_en"),
                        "similarity": round(similarity, 2),
                        "reason": f"Emby名称与JavInfoApi番号匹配 (相似度 {similarity:.0%})",
                    })

        return duplicates

    async def delete_item(self, item_id: str) -> bool:
        """Delete an Emby item. Returns True only when Emby confirms removal."""
        try:
            client = await self._get_client()
            response = await client.delete(f"{self.api_url}/Items/{item_id}")
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Emby delete failed for item %s: %s", item_id, exc)
            return False

    # === 缺失检测 ===

    async def get_missing_actresses_summary(self, info_client) -> list[dict]:
        """获取缺失演员统计（保留作为兜底；主路径已改为读 inventory 的
        missing_videos 表，请参考 routers/missing.py）。"""
        from database import save_missing_summary
        from services.subscription import get_all_subscriptions

        summaries = []
        subscriptions = get_all_subscriptions()

        for sub in subscriptions:
            actress_id = sub.get("actress_id")
            actress_name = sub.get("actress_name")

            if not actress_id or not actress_name:
                continue

            try:
                # Pull every JavInfo work for this actress (not just the first 100).
                from services.watchlist_pipeline import WatchlistPipeline

                pipeline = WatchlistPipeline(info_client=info_client, emby_client=self)
                javinfo_videos = await pipeline.fetch_actress_videos(int(actress_id))
                total = len(javinfo_videos)

                if total == 0:
                    continue

                # 检查哪些在 Emby 中不存在
                missing = []
                for video in javinfo_videos:
                    code = video.get("dvd_id") or video.get("content_id")
                    if not code:
                        continue
                    try:
                        exists = await self.check_exists(code)
                    except EmbyUnavailableError:
                        # Aborting this actress on Emby failure is safer than
                        # mass-flagging everything as missing.
                        logger.warning(
                            "Emby unavailable while summarising missing for %s; skipping",
                            actress_name,
                        )
                        missing = []
                        total = 0
                        break
                    if not exists:
                        missing.append({
                            "content_id": code,
                            "title": video.get("title_en"),
                            "release_date": video.get("release_date"),
                            "jacket_thumb_url": video.get("jacket_thumb_url"),
                        })

                if total == 0:
                    continue

                missing_count = len(missing)

                # 缓存到数据库
                import json
                videos_json = json.dumps(missing, ensure_ascii=False)
                save_missing_summary(actress_id, actress_name, total, missing_count, videos_json)

                summaries.append({
                    "actress_id": actress_id,
                    "actress_name": actress_name,
                    "total_in_javinfo": total,
                    "missing_count": missing_count,
                })
            except Exception:
                continue

        return sorted(summaries, key=lambda x: x["missing_count"], reverse=True)


# 全局单例
_emby_client: EmbyClient | None = None


def get_emby_client() -> EmbyClient:
    global _emby_client
    if _emby_client is None:
        from config import config
        emby_config = getattr(config, "emby", {})
        _emby_client = EmbyClient(
            api_url=emby_config.get("api_url", ""),
            api_key=emby_config.get("api_key", ""),
        )
    return _emby_client
