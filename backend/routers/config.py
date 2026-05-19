import logging
import re
import yaml
from fastapi import APIRouter, HTTPException, Response
from urllib.parse import urlparse, urlunparse
from config import config
from services import cache
from services.ai import build_ai_client
from .proxy import _get_httpx_proxies

logger = logging.getLogger(__name__)


def _mask_url_credentials(url: str) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    if not parsed.username and not parsed.password:
        return url
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


async def _push_proxy_to_javinfo():
    """将 JavHub 的代理配置推送到 JavInfoApi"""
    try:
        from modules.info_client import get_info_client
        client = get_info_client()
        proxy_url = ""
        if config.proxy_enabled:
            proxy_url = config.proxy_http_url or config.proxy_https_url
        await client.push_proxy_config(proxy_url)
        logger.info("Pushed proxy config to JavInfoApi: %s", _mask_url_credentials(proxy_url) or "(none)")
    except Exception as e:
        logger.warning(f"Failed to push proxy config to JavInfoApi: {e}")

router = APIRouter(prefix="/api/v1", tags=["config"])

_SENSITIVE_KEYS = {'api_key', 'bot_token', 'password', 'secret', 'token', 'db_pass', 'jwt_secret'}
_WRITABLE_KEYS = {'emby', 'telegram', 'openlist', 'notification', 'scheduler',
                  'ai',
                  'automation', 'actor_mapping', 'translation',
                  'proxy', 'rate_limit', 'sources', 'javinfo', 'server'}
_TELEGRAM_BOT_TOKEN_RE = re.compile(r"^\d{5,20}:[A-Za-z0-9_-]{20,128}$")


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith('_token')
        or normalized.endswith('_secret')
        or normalized.endswith('_password')
        or normalized.endswith('_api_key')
    )


def _sanitize_config(cfg: dict) -> dict:
    """递归脱敏：移除嵌套 dict 中的敏感字段"""
    result = {}
    for k, v in cfg.items():
        if isinstance(v, dict):
            result[k] = _sanitize_config(v)
        elif isinstance(v, list):
            result[k] = [
                _sanitize_config(item) if isinstance(item, dict) else item
                for item in v
            ]
        elif not _is_sensitive_key(k):
            result[k] = v
    return result


def _strip_blank_sensitive_values(cfg: dict) -> dict:
    """保存配置时，空白敏感字段表示前端未修改，不覆盖现有密钥。"""
    result = {}
    for k, v in cfg.items():
        if isinstance(v, dict):
            result[k] = _strip_blank_sensitive_values(v)
        elif isinstance(v, list):
            result[k] = [
                _strip_blank_sensitive_values(item) if isinstance(item, dict) else item
                for item in v
            ]
        elif _is_sensitive_key(k) and (v is None or v == ""):
            continue
        else:
            result[k] = v
    return result


def _validated_telegram_bot_token(token: str) -> str | None:
    token = (token or "").strip()
    if not _TELEGRAM_BOT_TOKEN_RE.fullmatch(token):
        return None
    return token


@router.get("/config")
async def get_config():
    return _sanitize_config(config.get_all())


@router.get("/config/export")
async def export_config():
    exported = _sanitize_config(config.get_all())
    content = yaml.safe_dump(exported, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return Response(
        content=content,
        media_type="application/x-yaml",
        headers={"Content-Disposition": 'attachment; filename="javhub-config.yaml"'},
    )


@router.put("/config")
async def update_config(new_config: dict):
    # 只允许更新白名单内的顶层 key
    sanitized = {k: v for k, v in new_config.items() if k in _WRITABLE_KEYS}
    sanitized = _strip_blank_sensitive_values(sanitized)
    config.update(sanitized)
    # JavInfoApi URL 变更后立即生效
    if "javinfo" in sanitized:
        from modules.info_client import reset_info_client
        reset_info_client()
    # 代理配置变更后推送到 JavInfoApi
    if "proxy" in sanitized:
        await _push_proxy_to_javinfo()
    if "automation" in sanitized:
        try:
            from scheduler.tasks import configure_candidate_auto_process_job, scheduler
            if scheduler.running:
                configure_candidate_auto_process_job()
        except Exception as e:
            logger.warning(f"Failed to refresh candidate automation scheduler: {e}")
    return {"success": True}


@router.post("/ai/test")
async def test_ai_model(body: dict | None = None):
    """测试当前公共智能模型配置。"""
    try:
        return await build_ai_client(_ai_settings_from_body(body)).test()
    except Exception as exc:
        raise HTTPException(502, f"AI 测试失败: {exc}") from exc


@router.post("/ai/models")
async def list_ai_models(body: dict | None = None):
    """获取当前草稿 AI 配置可用模型列表。"""
    try:
        return await build_ai_client(_ai_settings_from_body(body)).list_models()
    except Exception as exc:
        raise HTTPException(502, f"获取模型列表失败: {exc}") from exc


def _ai_settings_from_body(body: dict | None) -> dict:
    body = body or {}
    saved = config.ai
    if isinstance(body.get("openai_compatible"), dict):
        draft = {"provider": "openai_compatible", "openai_compatible": body["openai_compatible"]}
    else:
        draft_ai = body.get("ai") if isinstance(body.get("ai"), dict) else {}
        draft = {**draft_ai}
        if body.get("provider"):
            draft["provider"] = body.get("provider")

    merged = config._merge_config(saved, draft)
    for provider_key in ("openai_compatible", "gemini", "ollama"):
        provider_cfg = merged.get(provider_key)
        if not isinstance(provider_cfg, dict):
            continue
        if provider_cfg.get("api_key"):
            continue
        saved_provider = saved.get(provider_key, {}) if isinstance(saved.get(provider_key), dict) else {}
        if saved_provider.get("api_key"):
            provider_cfg["api_key"] = saved_provider.get("api_key")
    return merged

@router.post("/notification/telegram/test")
async def test_telegram(token: str):
    """发送测试 Telegram 消息"""
    import httpx
    token = _validated_telegram_bot_token(token)
    if not token:
        return {"success": False, "error": "Token 格式无效"}
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
    """清除缓存，scope=all 清除全部，scope=video 只清除视频和搜索缓存，scope=enum 清枚举响应缓存"""
    if scope == "all":
        count = cache.purge_all()
    elif scope == "enum":
        count = cache.purge_enum_cache()
    elif scope == "response":
        count = cache.purge_response_cache()
    else:
        count = cache.purge_video_cache()
    return {"purged": count, "scope": scope}


@router.get("/cache/stats")
async def get_cache_stats():
    return cache.get_stats()
