from fastapi import APIRouter
from modules.info_client import get_info_client
from services import cache

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

@router.get("")
async def list_categories():
    client = get_info_client()
    return await client.list_categories()


@router.get("/stats")
async def category_stats():
    """
    返回每个 category 的影片数量统计，用于金色传说稀有度计算（缓存1小时）。
    """
    cached = cache.get_category_stats()
    if cached is not None:
        return cached

    client = get_info_client()
    categories = await client.list_categories()

    import asyncio
    async def fetch_count(cat: dict) -> dict:
        try:
            result = await client.search_videos(category_id=cat.get('id'), page=1, page_size=1)
            count = result.get('total', 0) if isinstance(result, dict) else 0
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
