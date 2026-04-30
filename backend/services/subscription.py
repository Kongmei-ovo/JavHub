from typing import List, Optional
from database import get_subscriptions, update_last_check
import logging

logger = logging.getLogger(__name__)


def get_all_subscriptions() -> List[dict]:
    """获取所有订阅"""
    return get_subscriptions()


async def check_all_subscriptions() -> List[dict]:
    """
    检查所有订阅的新片
    使用 JavInfoApi 获取演员最新片单，对比 Emby 已有片库
    """
    from modules.info_client import get_info_client
    from modules.emby_client import get_emby_client

    info_client = get_info_client()
    emby_client = get_emby_client()
    subscriptions = get_subscriptions()
    new_movies = []

    for sub in subscriptions:
        if not sub.get("enabled"):
            continue

        actress_id = sub.get("actress_id")
        actress_name = sub.get("actress_name", "")

        if not actress_id or not actress_name:
            continue

        try:
            result = await info_client.get_actress_videos(actress_id, page_size=10)
            videos = result.get("data", [])

            for video in videos:
                code = video.get("dvd_id") or video.get("content_id")
                if not code:
                    continue

                exists = await emby_client.check_exists(code)
                if not exists:
                    new_movies.append({
                        "actress_name": actress_name,
                        "code": code,
                        "title": video.get("title_en", "") or video.get("title", ""),
                        "release_date": video.get("release_date", ""),
                    })

            update_last_check(sub["id"], videos[0].get("dvd_id", "") if videos else "")

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

    from modules.info_client import get_info_client
    from modules.emby_client import get_emby_client

    info_client = get_info_client()
    emby_client = get_emby_client()

    result = await info_client.get_actress_videos(actress_id, page_size=10)
    videos = result.get("data", [])

    latest_movies = []
    new_movies = []
    for video in videos[:10]:
        code = video.get("dvd_id") or video.get("content_id")
        if not code:
            continue
        latest_movies.append({
            "code": code,
            "title": video.get("title_en", "") or video.get("title", ""),
        })
        exists = await emby_client.check_exists(code)
        if not exists:
            new_movies.append({
                "code": code,
                "title": video.get("title_en", "") or video.get("title", ""),
            })

    update_last_check(sub["id"], videos[0].get("dvd_id", "") if videos else "")

    return {
        "actress_name": actress_name,
        "latest_movies": latest_movies,
        "new_movies": new_movies,
        "new_movies_count": len(new_movies),
    }
