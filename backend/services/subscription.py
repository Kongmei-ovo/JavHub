from typing import List
from database import get_subscriptions

def get_all_subscriptions() -> List[dict]:
    """获取所有订阅"""
    return get_subscriptions()

async def check_all_subscriptions():
    """
    检查所有订阅的新片
    使用 Info Module 和 Emby Module
    """
    from modules.info_client import get_info_client
    from modules.emby_client import get_emby_client

    info_client = get_info_client()
    emby_client = get_emby_client()

    subscriptions = get_subscriptions()
    new_movies = []

    for sub in subscriptions:
        actress_id = sub.get("actress_id")
        actress_name = sub.get("actress_name")

        if not actress_id or not actress_name:
            continue

        try:
            # 获取 JavInfoApi 中该演员的最新作品
            result = await info_client.get_actress_videos(actress_id, page_size=10)
            videos = result.get("data", [])

            for video in videos:
                code = video.get("dvd_id") or video.get("content_id")
                if not code:
                    continue

                # 检查是否在 Emby 中存在
                exists = await emby_client.check_exists(code)
                if not exists:
                    new_movies.append({
                        "actor": actress_name,
                        "code": code,
                        "title": video.get("title_en", ""),
                        "release_date": video.get("release_date", ""),
                        "jacket_thumb_url": video.get("jacket_thumb_url", ""),
                    })
                    break  # 只取最新的一部
        except Exception as e:
            print(f"检查订阅失败 {actress_name}: {e}")
            continue

    return new_movies
