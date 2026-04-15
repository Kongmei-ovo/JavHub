from fastapi import APIRouter
from config import config
from services import cache
from .proxy import _get_httpx_proxies

router = APIRouter(prefix="/api/v1", tags=["config"])

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

@router.post("/notification/telegram/test")
async def test_telegram(token: str):
    """发送测试 Telegram 消息"""
    import httpx
    if not token:
        return {"success": False, "error": "Token is required"}
    proxies = _get_httpx_proxies()
    # 从配置读取 allowed_user_ids
    allowed_users = config.telegram.get("allowed_user_ids", [])
    if not allowed_users:
        return {"success": False, "error": "请先在「允许的用户 ID」填入你的 Telegram User ID，并确保已给 Bot 发送过 /start"}
    chat_id = allowed_users[0]
    try:
        async with httpx.AsyncClient(timeout=10, proxies=proxies) as client:
            # 先验证 token 有效
            info_resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if info_resp.status_code != 200:
                return {"success": False, "error": "Token 无效"}
            # 发送测试消息给 allowed user
            data = {"chat_id": chat_id, "text": "✅ JavHub 测试消息：Telegram Bot 连接正常！"}
            resp = await client.post(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
            if resp.status_code == 200:
                return {"success": True}
            else:
                err = resp.json().get("description", "发送失败")
                return {"success": False, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/cache/purge")
async def purge_cache(scope: str = "video"):
    """清除缓存，scope=all 清除全部，scope=video 只清除视频和搜索缓存"""
    if scope == "all":
        count = cache.purge_all()
    else:
        count = cache.purge_video_cache()
    return {"purged": count, "scope": scope}
