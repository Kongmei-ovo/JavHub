from __future__ import annotations
import httpx
import re
from typing import Any
from difflib import SequenceMatcher


class EmbyClient:
    """Emby API 客户端"""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"X-Emby-Token": self.api_key},
                timeout=30,
            )
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

    async def check_exists(self, content_id: str) -> bool:
        """检查影片是否在库中（使用 Emby 查询接口，替代遍历全量数据）"""
        try:
            result = await self._get(
                "/Items",
                params={
                    "limit": 10,
                    "includeItemTypes": "Movie",
                    "recursive": "true",
                    "searchTerm": content_id,
                }
            )
            items = result.get("Items", result.get("items", []))
            code_upper = content_id.upper()
            for item in items:
                name = item.get("Name", "") or item.get("FileName", "")
                name_upper = name.upper()
                # 精确匹配：content_id 作为独立词组出现（前后是分隔符或边界）
                # 匹配: ABC-123, ABC-123-c, ABC-123.hack 等
                # 不匹配: XABC-123, ABC-123-456, ABC-1234
                if re.search(
                    r'(?<![A-Z0-9])' + re.escape(code_upper) + r'(?:-(?=[A-Za-z])[A-Za-z]*)?(?=\s|[().,!]|$)',
                    name_upper
                ):
                    return True
            return False
        except Exception:
            return False

    async def get_all_movies(self) -> list[dict]:
        """获取所有影片库项"""
        try:
            result = await self._get("/Library/MediaCounts")
            return result.get("Items", [])
        except Exception:
            return []

    async def get_items(self, limit: int = 200, include_people: bool = False) -> list[dict]:
        """获取媒体库中的所有项目"""
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

    async def get_items_with_people(self, limit: int = 9999, start: int = 0) -> dict:
        """分页获取影片（含People演员信息），返回 {items, totalCount}"""
        try:
            result = await self._get(
                "/Items",
                params={
                    "limit": limit,
                    "startIndex": start,
                    "includeItemTypes": "Movie",
                    "recursive": "true",
                    "fields": "People,PremiereDate,ProductionYear",
                }
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

    async def collect_all_movies_with_actors(self) -> tuple[list[dict], int]:
        """采集所有影片及其演员信息，返回 (actors_map, total_items)
        actors_map: {actress_id: {actress_id, actress_name, video_count, items: [], image_tag}}
        """
        all_actors: dict[int, dict] = {}
        total = 0
        page_size = 500
        start = 0

        while True:
            result = await self.get_items_with_people(limit=page_size, start=start)
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
        """获取所有演员及其在Emby的影片数"""
        items = await self.get_items(limit=9999)
        actors_map: dict[int, dict] = {}
        for item in items:
            people = item.get("People", [])
            for person in people:
                if person.get("Type") != "Actor":
                    continue
                actress_id = int(person.get("Id"))
                name = person.get("Name", "Unknown")
                if actress_id not in actors_map:
                    actors_map[actress_id] = {
                        "actress_id": actress_id,
                        "actress_name": name,
                        "video_count": 0,
                    }
                actors_map[actress_id]["video_count"] += 1
        return list(actors_map.values())

    async def get_actress_videos(self, actress_id: int) -> list[dict]:
        """获取指定演员在Emby中的影片（支持自动分页）"""
        all_items = []
        page_size = 500
        start = 0
        while True:
            result = await self.get_items_with_people(limit=page_size, start=start)
            items = result.get("items", [])
            if not items:
                break
            for item in items:
                people = item.get("People", [])
                for person in people:
                    if person.get("Type") == "Actor" and str(person.get("Id")) == str(actress_id):
                        all_items.append(item)
                        break
            start += len(items)
            total = result.get("totalCount", 0)
            if start >= total:
                break
        return all_items

    # === 去重相关 ===

    def _extract_code_from_name(self, name: str) -> str | None:
        """从 Emby 影片名称中提取番号"""
        # 匹配格式如 ABC-123, ABC-001, etc.
        match = re.search(r'([A-Z]+-\d+)', name.upper())
        return match.group(1) if match else None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, str1.upper(), str2.upper()).ratio()

    async def find_duplicates(self, info_client) -> list[dict]:
        """查找可疑重复（Emby名称 ↔ JavInfoApi匹配）"""
        from database import is_duplicate_ignored

        duplicates = []
        embys = await self.get_items()

        for emby_item in embys:
            emby_id = emby_item.get("Id")
            emby_name = emby_item.get("Name", "")

            # 跳过已忽略的
            if is_duplicate_ignored(emby_id):
                continue

            # 提取番号
            code = self._extract_code_from_name(emby_name)
            if not code:
                continue

            # 查询 JavInfoApi
            try:
                result = await info_client.search_videos(content_id=code, page_size=1)
                items = result.get("data", [])
                if items:
                    javinfo = items[0]
                    similarity = self._calculate_similarity(emby_name, javinfo.get("title_en", ""))
                    if similarity > 0.5:  # 相似度阈值
                        duplicates.append({
                            "emby_item_id": emby_id,
                            "emby_name": emby_name,
                            "content_id": code,
                            "javinfo_title": javinfo.get("title_en"),
                            "similarity": round(similarity, 2),
                            "reason": f"Emby名称与JavInfoApi番号匹配 (相似度 {similarity:.0%})",
                        })
            except Exception:
                continue

        return duplicates

    async def delete_item(self, item_id: str) -> bool:
        """删除 Emby 媒体库条目"""
        try:
            client = await self._get_client()
            await client.delete(f"{self.api_url}/Items/{item_id}")
            return True
        except Exception:
            return False

    # === 缺失检测 ===

    async def get_missing_actresses_summary(self, info_client) -> list[dict]:
        """获取缺失演员统计"""
        from database import save_missing_summary, get_all_missing_summaries
        from services.subscription import get_all_subscriptions

        summaries = []
        subscriptions = get_all_subscriptions()

        for sub in subscriptions:
            actress_id = sub.get("actress_id")
            actress_name = sub.get("actress_name")

            if not actress_id or not actress_name:
                continue

            try:
                # 获取 JavInfoApi 中该演员的所有作品
                javinfo_result = await info_client.get_actress_videos(actress_id, page_size=100)
                javinfo_videos = javinfo_result.get("data", [])
                total = len(javinfo_videos)

                if total == 0:
                    continue

                # 检查哪些在 Emby 中不存在
                missing = []
                for video in javinfo_videos:
                    code = video.get("dvd_id") or video.get("content_id")
                    if code:
                        exists = await self.check_exists(code)
                        if not exists:
                            missing.append({
                                "content_id": code,
                                "title": video.get("title_en"),
                                "release_date": video.get("release_date"),
                                "jacket_thumb_url": video.get("jacket_thumb_url"),
                            })

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
