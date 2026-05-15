import yaml
import os
import threading
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_JAVINFO_API_URL = "http://localhost:18080"
LEGACY_JAVINFO_API_URLS = {"http://localhost:8080", "http://127.0.0.1:8080"}
_warned_legacy_javinfo_urls: set[str] = set()

def _env(key: str, default: str = '') -> str:
    """读取环境变量，环境变量有值时优先于配置文件"""
    return os.getenv(key) or default


def _warn_if_legacy_javinfo_url(api_url: str, source: str) -> None:
    normalized = str(api_url or "").rstrip("/")
    if normalized not in LEGACY_JAVINFO_API_URLS:
        return
    warn_key = f"{source}:{normalized}"
    if warn_key in _warned_legacy_javinfo_urls:
        return
    _warned_legacy_javinfo_urls.add(warn_key)
    logger.warning(
        "JavInfoApi URL from %s is %s; default local JavInfoApi port is 18080. "
        "Use %s or set JAVINFO_API_URL for this environment.",
        source,
        normalized,
        DEFAULT_JAVINFO_API_URL,
    )


class Config:
    _instance: Optional['Config'] = None
    _config: dict = {}
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._load()
        return cls._instance

    def _load(self):
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}
        if isinstance(self._config.get('javinfo'), dict):
            _warn_if_legacy_javinfo_url(self._config['javinfo'].get('api_url', ''), 'config.yaml')

    def reload(self):
        self._load()

    @property
    def server_port(self) -> int:
        return self._config.get('server', {}).get('port', 18090)

    @property
    def frontend_origin(self) -> str:
        return self._config.get('server', {}).get('frontend_origin', 'http://localhost:5173')

    @property
    def openlist_api_url(self) -> str:
        return self._config.get('openlist', {}).get('api_url', '')

    @property
    def openlist_username(self) -> str:
        return _env('OPENLIST_USERNAME', self._config.get('openlist', {}).get('username', ''))

    @property
    def openlist_password(self) -> str:
        return _env('OPENLIST_PASSWORD', self._config.get('openlist', {}).get('password', ''))

    @property
    def openlist_token(self) -> str:
        return self._config.get('openlist', {}).get('token', '')

    @property
    def openlist_default_path(self) -> str:
        return self._config.get('openlist', {}).get('default_path', '/115/AV')

    @property
    def crawler_request_interval(self) -> int:
        return self._config.get('crawler', {}).get('request_interval', 3)

    @property
    def emby_api_url(self) -> str:
        return _env('EMBY_API_URL', self._config.get('emby', {}).get('api_url', ''))

    @property
    def emby_api_key(self) -> str:
        return _env('EMBY_API_KEY', self._config.get('emby', {}).get('api_key', ''))

    @property
    def emby(self) -> dict:
        return self._config.get('emby', {})

    @property
    def telegram_bot_token(self) -> str:
        return _env('TELEGRAM_BOT_TOKEN', self._config.get('telegram', {}).get('bot_token', ''))

    @property
    def telegram_allowed_users(self) -> list:
        return self._config.get('telegram', {}).get('allowed_user_ids', [])

    @property
    def telegram_timeout(self) -> int:
        return self._config.get('telegram', {}).get('timeout', 10)

    @property
    def telegram(self) -> dict:
        return self._config.get('telegram', {})

    @property
    def openlist(self) -> dict:
        return self._config.get('openlist', {})

    @property
    def scheduler_check_hour(self) -> int:
        return self._config.get('scheduler', {}).get('subscription_check_hour', 2)

    # Automation policy settings
    @property
    def automation(self) -> dict:
        defaults = {
            'download_policy': 'manual',
            'candidate_sources': ['subscription', 'inventory', 'supplement'],
            'rules_require_magnet': True,
            'auto_process_interval_minutes': 30,
            'max_auto_downloads_per_run': 20,
            'max_auto_downloads_per_24h': 100,
        }
        cfg = self._config.get('automation', {}) or {}
        return {**defaults, **cfg}

    @property
    def automation_download_policy(self) -> str:
        policy = str(self.automation.get('download_policy') or 'manual').lower()
        return policy if policy in {'manual', 'rules', 'auto'} else 'manual'

    @property
    def automation_candidate_sources(self) -> list:
        sources = self.automation.get('candidate_sources')
        if not isinstance(sources, list):
            return ['subscription', 'inventory', 'supplement']
        return [str(source) for source in sources if str(source).strip()]

    @property
    def automation_rules_require_magnet(self) -> bool:
        return bool(self.automation.get('rules_require_magnet', True))

    @property
    def automation_auto_process_interval_minutes(self) -> int:
        try:
            value = int(self.automation.get('auto_process_interval_minutes', 30))
        except Exception:
            value = 30
        return max(0, value)

    @property
    def automation_max_auto_downloads_per_run(self) -> int:
        try:
            value = int(self.automation.get('max_auto_downloads_per_run', 20))
        except Exception:
            value = 20
        return max(0, value)

    @property
    def automation_max_auto_downloads_per_24h(self) -> int:
        try:
            value = int(self.automation.get('max_auto_downloads_per_24h', 100))
        except Exception:
            value = 100
        return max(0, value)

    # Actor mapping automation settings
    @property
    def actor_mapping(self) -> dict:
        defaults = {
            'auto_match_after_collect': True,
            'auto_confirm_policy': 'conservative',
            'candidate_per_actor': 3,
            'candidate_min_confidence': 0.55,
            'auto_confirm_confidence': 0.98,
            'auto_confirm_gap': 0.08,
        }
        cfg = self._config.get('actor_mapping', {}) or {}
        return {**defaults, **cfg}

    @property
    def actor_mapping_auto_match_after_collect(self) -> bool:
        return bool(self.actor_mapping.get('auto_match_after_collect', True))

    @property
    def actor_mapping_auto_confirm_policy(self) -> str:
        policy = str(self.actor_mapping.get('auto_confirm_policy') or 'conservative').lower()
        return policy if policy in {'conservative'} else 'conservative'

    @property
    def actor_mapping_candidate_per_actor(self) -> int:
        try:
            value = int(self.actor_mapping.get('candidate_per_actor', 3))
        except Exception:
            value = 3
        return max(1, min(value, 10))

    @property
    def actor_mapping_candidate_min_confidence(self) -> float:
        try:
            value = float(self.actor_mapping.get('candidate_min_confidence', 0.55))
        except Exception:
            value = 0.55
        return max(0.0, min(value, 1.0))

    @property
    def actor_mapping_auto_confirm_confidence(self) -> float:
        try:
            value = float(self.actor_mapping.get('auto_confirm_confidence', 0.98))
        except Exception:
            value = 0.98
        return max(0.0, min(value, 1.0))

    @property
    def actor_mapping_auto_confirm_gap(self) -> float:
        try:
            value = float(self.actor_mapping.get('auto_confirm_gap', 0.08))
        except Exception:
            value = 0.08
        return max(0.0, min(value, 1.0))

    # Shared AI settings
    @property
    def ai(self) -> dict:
        defaults = {
            'openai_compatible': {
                'base_url': 'https://api.openai.com/v1',
                'api_key': '',
                'model': 'gpt-4o-mini',
                'timeout': 30,
            },
        }
        cfg = self._config.get('ai', {}) or {}
        legacy_translation_cfg = self._config.get('translation', {}) or {}
        legacy_openai_cfg = legacy_translation_cfg.get('openai_compatible', {})
        merged = {**defaults, **cfg}
        merged['openai_compatible'] = {
            **defaults['openai_compatible'],
            **(legacy_openai_cfg if isinstance(legacy_openai_cfg, dict) else {}),
            **(cfg.get('openai_compatible', {}) if isinstance(cfg.get('openai_compatible'), dict) else {}),
        }
        return merged

    @property
    def openai_compatible(self) -> dict:
        cfg = self.ai.get('openai_compatible', {})
        return cfg if isinstance(cfg, dict) else {}

    # Translation settings
    @property
    def translation(self) -> dict:
        defaults = {
            'enabled': True,
            'target_language': 'zh-CN',
            'provider_order': ['cache', 'mapping', 'google_free', 'deepl', 'microsoft', 'openai_compatible'],
            'batch_provider_order': ['cache', 'mapping', 'google_free', 'deepl', 'microsoft'],
            'realtime_mode': 'cache_only',
            'batch_concurrency': 32,
            'batch_size': 200,
            'batch_char_limit': 24000,
            'source_page_size': 500,
            'scan_pages_per_batch': 8,
            'google_free': {
                'enabled': True,
                'base_url': 'https://translate.googleapis.com/translate_a/single',
                'timeout': 10,
            },
            'deepl': {
                'enabled': False,
                'api_key': '',
                'free_api': True,
                'timeout': 15,
            },
            'microsoft': {
                'enabled': False,
                'api_key': '',
                'region': '',
                'endpoint': 'https://api.cognitive.microsofttranslator.com',
                'timeout': 15,
            },
        }
        cfg = self._config.get('translation', {}) or {}
        merged = {**defaults, **cfg}
        for nested_key in ('google_free', 'deepl', 'microsoft'):
            merged[nested_key] = {
                **defaults[nested_key],
                **(cfg.get(nested_key, {}) if isinstance(cfg.get(nested_key), dict) else {}),
            }
        merged.pop('openai_compatible', None)
        return merged

    @property
    def translation_enabled(self) -> bool:
        return bool(self.translation.get('enabled', True))

    @property
    def translation_target_language(self) -> str:
        return str(self.translation.get('target_language') or 'zh-CN')

    @property
    def translation_provider_order(self) -> list:
        order = self.translation.get('provider_order')
        if not isinstance(order, list):
            return ['cache', 'mapping', 'google_free', 'deepl', 'microsoft', 'openai_compatible']
        return [str(item) for item in order if str(item).strip()]

    @property
    def translation_batch_provider_order(self) -> list:
        order = self.translation.get('batch_provider_order')
        if not isinstance(order, list):
            return ['cache', 'mapping', 'google_free', 'deepl', 'microsoft']
        return [str(item) for item in order if str(item).strip()]

    @property
    def translation_batch_concurrency(self) -> int:
        try:
            value = int(self.translation.get('batch_concurrency', 32) or 32)
        except Exception:
            value = 32
        return max(1, min(value, 64))

    @property
    def translation_batch_size(self) -> int:
        try:
            value = int(self.translation.get('batch_size', 200) or 200)
        except Exception:
            value = 200
        return max(1, min(value, 200))

    @property
    def translation_batch_char_limit(self) -> int:
        try:
            value = int(self.translation.get('batch_char_limit', 24000) or 24000)
        except Exception:
            value = 24000
        return max(500, min(value, 24000))

    @property
    def translation_source_page_size(self) -> int:
        try:
            value = int(self.translation.get('source_page_size', 500) or 500)
        except Exception:
            value = 500
        return max(20, min(value, 1000))

    @property
    def translation_scan_pages_per_batch(self) -> int:
        try:
            value = int(self.translation.get('scan_pages_per_batch', 8) or 8)
        except Exception:
            value = 8
        return max(1, min(value, 64))

    @property
    def translation_openai(self) -> dict:
        return self.openai_compatible

    # JavInfo API settings
    @property
    def javinfo(self) -> dict:
        return self._config.get('javinfo', {})

    @property
    def javinfo_api_url(self) -> str:
        api_url = _env('JAVINFO_API_URL', self._config.get('javinfo', {}).get('api_url', DEFAULT_JAVINFO_API_URL))
        source = 'JAVINFO_API_URL' if os.getenv('JAVINFO_API_URL') else 'config.yaml'
        _warn_if_legacy_javinfo_url(api_url, source)
        return api_url

    @property
    def javinfo_timeout(self) -> int:
        return self._config.get('javinfo', {}).get('timeout', 30)

    @property
    def supplement_admin_token(self) -> str:
        return _env('SUPPLEMENT_ADMIN_TOKEN', self._config.get('javinfo', {}).get('supplement_admin_token', ''))

    # MetaTube settings
    @property
    def metatube(self) -> dict:
        return self._config.get('metatube', {})

    @property
    def metatube_host(self) -> str:
        return _env('METATUBE_HOST', self._config.get('metatube', {}).get('host', 'localhost'))

    @property
    def metatube_port(self) -> int:
        return int(_env('METATUBE_PORT', str(self._config.get('metatube', {}).get('port', 8081))))

    @property
    def metatube_token(self) -> str:
        return _env('METATUBE_TOKEN', self._config.get('metatube', {}).get('token', ''))

    # Download sources settings
    @property
    def sources(self) -> dict:
        return self._config.get('sources', {})

    @property
    def downloaders(self) -> dict:
        return self._config.get('downloaders', {})

    # Proxy settings
    @property
    def proxy(self) -> dict:
        return self._config.get('proxy', {})

    @property
    def proxy_enabled(self) -> bool:
        return self._config.get('proxy', {}).get('enabled', False)

    @property
    def proxy_http_url(self) -> str:
        return self._config.get('proxy', {}).get('http_url', '')

    @property
    def proxy_https_url(self) -> str:
        return self._config.get('proxy', {}).get('https_url', '')

    # Notification settings
    @property
    def notification_enabled(self) -> bool:
        return self._config.get('notification', {}).get('enabled', False)

    @property
    def notification_telegram(self) -> bool:
        return self._config.get('notification', {}).get('telegram', True)

    @property
    def notification_auto_download(self) -> bool:
        return self._config.get('notification', {}).get('auto_download_notify', True)

    @property
    def notification_download_complete(self) -> bool:
        return self._config.get('notification', {}).get('download_complete_notify', True)

    @property
    def notification_new_movie(self) -> bool:
        return self._config.get('notification', {}).get('new_movie_notify', True)

    # Rate limiting
    @property
    def rate_limit_enabled(self) -> bool:
        return self._config.get('rate_limit', {}).get('enabled', False)

    @property
    def rate_limit_rpm(self) -> int:
        return self._config.get('rate_limit', {}).get('requests_per_minute', 60)

    @property
    def rate_limit_burst(self) -> int:
        return self._config.get('rate_limit', {}).get('burst', 10)

    def get_all(self) -> dict:
        cfg = self._config.copy()
        cfg['ai'] = self.ai
        cfg['automation'] = self.automation
        cfg['actor_mapping'] = self.actor_mapping
        cfg['translation'] = self.translation
        javinfo_cfg = cfg.get('javinfo', {}) if isinstance(cfg.get('javinfo'), dict) else {}
        cfg['javinfo'] = {
            'page_size': javinfo_cfg.get('page_size', 30),
            'timeout': self.javinfo_timeout,
            **javinfo_cfg,
            'api_url': self.javinfo_api_url,
        }
        return cfg

    def _merge_config(self, current: dict, incoming: dict) -> dict:
        merged = current.copy()
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged

    def update(self, new_config: dict):
        incoming = self._merge_config({}, new_config)
        if isinstance(incoming.get('ai'), dict):
            incoming_openai = incoming['ai'].get('openai_compatible')
            if isinstance(incoming_openai, dict) and not incoming_openai.get('api_key'):
                current_ai = self._config.get('ai', {}) or {}
                current_openai = current_ai.get('openai_compatible', {}) if isinstance(current_ai, dict) else {}
                legacy_translation = self._config.get('translation', {}) or {}
                legacy_openai = (
                    legacy_translation.get('openai_compatible', {})
                    if isinstance(legacy_translation, dict)
                    else {}
                )
                existing_api_key = (
                    current_openai.get('api_key') if isinstance(current_openai, dict) else ''
                ) or (
                    legacy_openai.get('api_key') if isinstance(legacy_openai, dict) else ''
                )
                if existing_api_key:
                    incoming_openai['api_key'] = existing_api_key
        self._config = self._merge_config(self._config, incoming)
        if isinstance(incoming.get('javinfo'), dict):
            _warn_if_legacy_javinfo_url(incoming['javinfo'].get('api_url', ''), 'config update')
        if 'ai' in incoming and isinstance(self._config.get('translation'), dict):
            self._config['translation'].pop('openai_compatible', None)
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

config = Config()
