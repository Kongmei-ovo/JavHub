from fastapi import APIRouter
from config import config
from services import cache

router = APIRouter(prefix="/api", tags=["config"])

@router.get("/config")
async def get_config():
    return config.get_all()

@router.put("/config")
async def update_config(new_config: dict):
    config.update(new_config)
    # JavInfoApi URL 变更后立即生效
    if "javinfo" in new_config:
        from modules.info_client import reset_info_client
        reset_info_client()
    # MetaTube URL 变更后重置 client
    if "metatube" in new_config:
        from modules.metatube_client import close as mt_close
        await mt_close()
    return {"success": True}

@router.post("/cache/purge")
async def purge_cache(scope: str = "video"):
    """清除缓存，scope=all 清除全部，scope=video 只清除视频和搜索缓存"""
    if scope == "all":
        count = cache.purge_all()
    else:
        count = cache.purge_video_cache()
    return {"purged": count, "scope": scope}
