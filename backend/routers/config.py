from fastapi import APIRouter
from config import config
from services import cache
from .proxy import _get_httpx_proxies

router = APIRouter(prefix="/api/v1", tags=["config"])

_SENSITIVE_KEYS = {'api_key', 'bot_token', 'password', 'secret', 'token', 'db_pass', 'jwt_secret'}
_WRITABLE_KEYS = {'emby', 'telegram', 'openlist', 'metatube', 'notification', 'scheduler',
                  'proxy', 'rate_limit', 'sources', 'javinfo', 'server'}


def _sanitize_config(cfg: dict) -> dict:
    """递归脱敏：移除嵌套 dict 中的敏感字段"""
    result = {}
    for k, v in cfg.items():
        if isinstance(v, dict):
            result[k] = {sk: sv for sk, sv in v.items() if sk not in _SENSITIVE_KEYS}
        elif k not in _SENSITIVE_KEYS:
            result[k] = v
    return result


@router.get("/config")
async def get_config():
    return _sanitize_config(config.get_all())


@router.put("/config")
async def update_config(new_config: dict):
    # 只允许更新白名单内的顶层 key
    sanitized = {k: v for k, v in new_config.items() if k in _WRITABLE_KEYS}
    config.update(sanitized)
    # JavInfoApi URL 变更后立即生效
    if "javinfo" in sanitized:
        from modules.info_client import reset_info_client
        reset_info_client()
    # MetaTube URL 变更后重置 client
    if "metatube" in sanitized:
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
