from fastapi import APIRouter
import asyncio
from modules.info_client import get_info_client
from services import cache
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

CATEGORY_STATS_CONCURRENCY = 8
_category_stats_rebuild_lock = asyncio.Lock()

@router.get("")
async def list_categories():
    client = get_info_client()
    categories = await client.list_categories()
    # 为每个 category 注入翻译字段
    if isinstance(categories, list):
        await get_translator_service().translate_entities(
            categories,
            entity_type="category",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )
    return categories


@router.get("/stats")
async def category_stats():
    """
    返回每个 category 的影片数量统计，用于金色传说稀有度计算（缓存1小时）。
    """
    cached = cache.get_category_stats()
    if cached is not None:
        return cached

    async with _category_stats_rebuild_lock:
        cached = cache.get_category_stats()
        if cached is not None:
            return cached

        client = get_info_client()
        categories = await client.list_categories()

        semaphore = asyncio.Semaphore(CATEGORY_STATS_CONCURRENCY)

        async def fetch_count(cat: dict) -> dict:
            async with semaphore:
                try:
                    result = await client.search_videos(category_id=cat.get('id'), page=1, page_size=1)
                    count = result.get('total_count', result.get('total', 0)) if isinstance(result, dict) else 0
                    return {**cat, 'video_count': count}
                except Exception:
                    return {**cat, 'video_count': 0}

        tasks = [fetch_count(c) for c in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stats = []
        for r in results:
            if isinstance(r, Exception):
                continue
            stats.append(r)

        cache.set_category_stats(stats)
        return stats
