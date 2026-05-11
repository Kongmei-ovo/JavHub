from typing import List, Optional
from database import get_subscriptions, update_last_check
import logging
from services.watchlist_pipeline import WatchlistPipeline

logger = logging.getLogger(__name__)


def get_all_subscriptions() -> List[dict]:
    """获取所有订阅"""
    return get_subscriptions()


async def check_all_subscriptions() -> List[dict]:
    """
    检查所有订阅的新片
    使用 JavInfoApi include_supplement=1 获取完整片单，缺失项写入下载候选。
    """
    subscriptions = get_subscriptions()
    pipeline = WatchlistPipeline()
    new_movies = []

    for sub in subscriptions:
        if not sub.get("enabled"):
            continue

        actress_id = sub.get("actress_id")
        actress_name = sub.get("actress_name", "")

        if not actress_id or not actress_name:
            continue

        try:
            result = await pipeline.generate_candidates_for_actress(
                actress_id=actress_id,
                actress_name=actress_name,
                trigger_source="subscription",
                reason="subscription_check",
            )
            for movie in result.get("new_movies", []):
                movie["actress_name"] = actress_name
                movie["subscription_id"] = sub["id"]
            new_movies.extend(result.get("new_movies", []))
            latest = result.get("new_movies", [{}])[0].get("dvd_id", "") if result.get("new_movies") else ""
            update_last_check(sub["id"], latest)

        except Exception as e:
            logger.error(f"检查订阅失败 {actress_name}: {e}")
            continue

    return new_movies


async def check_single_subscription(subscription_id: int) -> Optional[dict]:
    """检查单条订阅"""
    subs = get_subscriptions()
    sub = next((s for s in subs if s["id"] == subscription_id), None)
    if not sub:
        return None

    actress_id = sub.get("actress_id")
    actress_name = sub.get("actress_name", "")

    pipeline = WatchlistPipeline()
    result = await pipeline.generate_candidates_for_actress(
        actress_id=actress_id,
        actress_name=actress_name,
        trigger_source="subscription",
        reason="subscription_check",
    )
    videos = await pipeline.fetch_actress_videos(actress_id, page_size=10)
    latest_movies = [
        {
            "code": video.get("dvd_id") or video.get("content_id"),
            "title": video.get("title_ja") or video.get("title_en") or video.get("title", ""),
        }
        for video in videos[:10]
        if video.get("dvd_id") or video.get("content_id")
    ]

    update_last_check(sub["id"], latest_movies[0].get("code", "") if latest_movies else "")

    return {
        "actress_name": actress_name,
        "latest_movies": latest_movies,
        **result,
    }
