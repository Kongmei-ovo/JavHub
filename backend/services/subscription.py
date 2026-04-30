from typing import List, Optional
from database import get_subscriptions, update_last_check
from config import config
import logging

logger = logging.getLogger(__name__)


def get_all_subscriptions() -> List[dict]:
    """获取所有订阅"""
    return get_subscriptions()


async def check_all_subscriptions() -> List[dict]:
    """
    检查所有订阅的新片
    1. 使用爬虫源获取演员最新片单
    2. 对比 Emby 已有片库
    3. 返回新片列表
    """
    from modules.emby_client import get_emby_client
    from sources.registry import SourceRegistry

    emby_client = get_emby_client()
    subscriptions = get_subscriptions()
    new_movies = []

    for sub in subscriptions:
        if not sub.get("enabled"):
            continue

        actress_name = sub.get("actress_name", "")
        if not actress_name:
            continue

        try:
            # 从爬虫源获取演员最新作品
            source_videos = []
            for source in SourceRegistry.all():
                try:
                    videos = await source.get_actress_videos(actress_name)
                    if videos:
                        source_videos = videos
                        break
                except Exception as e:
                    logger.warning(f"Source {source.name} failed for {actress_name}: {e}")
                    continue

            if not source_videos:
                continue

            # 对比 Emby，筛选新片
            for video in source_videos:
                code = video.get("content_id", "")
                if not code:
                    continue

                exists = await emby_client.check_exists(code)
                if not exists:
                    new_movies.append({
                        "actress_name": actress_name,
                        "code": code,
                        "title": video.get("title", ""),
                        "release_date": video.get("release_date", ""),
                        "magnet": video.get("magnet", ""),
                    })

            # 更新最后检查时间
            last_code = source_videos[0].get("content_id", "") if source_videos else ""
            update_last_check(sub["id"], last_code)

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

    actress_name = sub.get("actress_name", "")
    from modules.emby_client import get_emby_client
    from sources.registry import SourceRegistry

    emby_client = get_emby_client()

    # 获取最新作品
    source_videos = []
    for source in SourceRegistry.all():
        try:
            videos = await source.get_actress_videos(actress_name)
            if videos:
                source_videos = videos
                break
        except Exception:
            continue

    latest_movies = []
    new_movies = []
    for video in source_videos[:10]:
        code = video.get("content_id", "")
        if not code:
            continue
        latest_movies.append({
            "code": code,
            "title": video.get("title", ""),
        })
        exists = await emby_client.check_exists(code)
        if not exists:
            new_movies.append({
                "code": code,
                "title": video.get("title", ""),
                "magnet": video.get("magnet", ""),
            })

    update_last_check(sub["id"], source_videos[0].get("content_id", "") if source_videos else "")

    return {
        "actress_name": actress_name,
        "latest_movies": latest_movies,
        "new_movies": new_movies,
        "new_movies_count": len(new_movies),
    }
