import yaml
import os
import sys
import threading
import logging
from pathlib import Path
from typing import Optional

from services.javinfo_import_settings import normalize_javinfo_import_db_settings

logger = logging.getLogger(__name__)

DEFAULT_JAVINFO_API_URL = "http://localhost:18080"
LEGACY_JAVINFO_API_URLS: set[str] = set()
_warned_legacy_javinfo_urls: set[str] = set()
DEFAULT_TORZNAB_SOURCE = {
    'enabled': False,
    'name': 'torznab',
    'base_url': '',
    'api_key': '',
    'indexer': 'all',
    'categories': '',
    'limit': 20,
    'timeout': 15,
}

def _env(key: str, default: str = '') -> str:
    """读取环境变量，环境变量有值时优先于配置文件"""
    return os.getenv(key) or default


def _first_env(default: str, *keys: str) -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


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
        config_path = Path(os.environ.get("JAVHUB_CONFIG_PATH") or Path(__file__).parent.parent / "config.yaml")
        self._config_path = config_path
        self._config_load_error = ""
        if not config_path.exists():
            self._config = {}
            self._config_loaded = False
            self._config_load_error = f"config file not found: {config_path}"
            logger.warning(self._config_load_error)
            return
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            self._config_loaded = True
        except Exception as exc:
            self._config = {}
            self._config_loaded = False
            self._config_load_error = f"failed to load config file {config_path}: {exc}"
            logger.exception("Failed to load config file %s", config_path)
        if isinstance(self._config.get('javinfo'), dict):
            _warn_if_legacy_javinfo_url(self._config['javinfo'].get('api_url', ''), 'config.yaml')

    def reload(self):
        self._load()

    @property
    def config_path(self) -> Path:
        return getattr(self, "_config_path", Path(os.environ.get("JAVHUB_CONFIG_PATH") or Path(__file__).parent.parent / "config.yaml"))

    @property
    def config_loaded(self) -> bool:
        return bool(getattr(self, "_config_loaded", False))

    @property
    def config_load_error(self) -> str:
        return str(getattr(self, "_config_load_error", ""))

    @property
    def server_port(self) -> int:
        return self._config.get('server', {}).get('port', 18090)

    @property
    def frontend_origin(self) -> str:
        return self._config.get('server', {}).get('frontend_origin', 'http://localhost:5174')

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
    def scheduler_check_hour(self) -> Optional[int]:
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
        return self._clamp_int(self.automation.get('auto_process_interval_minutes', 30), 30, 0)

    @property
    def automation_max_auto_downloads_per_run(self) -> int:
        return self._clamp_int(self.automation.get('max_auto_downloads_per_run', 20), 20, 0)

    @property
    def automation_max_auto_downloads_per_24h(self) -> int:
        return self._clamp_int(self.automation.get('max_auto_downloads_per_24h', 100), 100, 0)

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
        return self._clamp_int(self.actor_mapping.get('candidate_per_actor', 3), 3, 1, 10)

    @property
    def actor_mapping_candidate_min_confidence(self) -> float:
        return self._clamp_float(self.actor_mapping.get('candidate_min_confidence', 0.55), 0.55, 0.0, 1.0)

    @property
    def actor_mapping_auto_confirm_confidence(self) -> float:
        return self._clamp_float(self.actor_mapping.get('auto_confirm_confidence', 0.98), 0.98, 0.0, 1.0)

    @property
    def actor_mapping_auto_confirm_gap(self) -> float:
        return self._clamp_float(self.actor_mapping.get('auto_confirm_gap', 0.08), 0.08, 0.0, 1.0)

    # Shared AI settings
    @property
    def ai(self) -> dict:
        defaults = {
            'provider': 'openai_compatible',
            'openai_compatible': {
                'base_url': 'https://api.openai.com/v1',
                'api_key': '',
                'model': 'gpt-4o-mini',
                'timeout': 30,
            },
            'gemini': {
                'base_url': 'https://generativelanguage.googleapis.com/v1beta',
                'api_key': '',
                'model': 'gemini-2.0-flash',
                'timeout': 30,
            },
            'ollama': {
                'base_url': 'http://localhost:11434',
                'api_key': '',
                'model': '',
                'timeout': 30,
            },
        }
        cfg = self._config.get('ai', {}) or {}
        legacy_translation_cfg = self._config.get('translation', {}) or {}
        legacy_openai_cfg = legacy_translation_cfg.get('openai_compatible', {})
        merged = {**defaults, **cfg}
        provider = str(merged.get('provider') or 'openai_compatible').strip()
        merged['provider'] = provider if provider in {'openai_compatible', 'gemini', 'ollama'} else 'openai_compatible'
        merged['openai_compatible'] = {
            **defaults['openai_compatible'],
            **(legacy_openai_cfg if isinstance(legacy_openai_cfg, dict) else {}),
            **(cfg.get('openai_compatible', {}) if isinstance(cfg.get('openai_compatible'), dict) else {}),
        }
        for nested_key in ('gemini', 'ollama'):
            merged[nested_key] = {
                **defaults[nested_key],
                **(cfg.get(nested_key, {}) if isinstance(cfg.get(nested_key), dict) else {}),
            }
        return merged

    @property
    def ai_provider(self) -> str:
        return str(self.ai.get('provider') or 'openai_compatible')

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
            'provider': 'google_free',
            'provider_order': ['cache', 'mapping', 'google_free'],
            'batch_provider_order': ['cache', 'mapping', 'google_free'],
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
            'baidu': {
                'enabled': False,
                'app_id': '',
                'secret': '',
                'endpoint': 'https://fanyi-api.baidu.com/api/trans/vip/translate',
                'timeout': 15,
                'qps': 1,
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
        for nested_key in ('google_free', 'baidu', 'deepl', 'microsoft'):
            merged[nested_key] = {
                **defaults[nested_key],
                **(cfg.get(nested_key, {}) if isinstance(cfg.get(nested_key), dict) else {}),
            }
        provider = self._normalize_translation_provider(merged.get('provider'))
        if provider == 'google_free' and not cfg.get('provider'):
            provider = self._first_network_translation_provider(
                cfg.get('batch_provider_order'),
                cfg.get('provider_order'),
            )
        merged['provider'] = provider
        merged['provider_order'] = ['cache', 'mapping', provider]
        merged['batch_provider_order'] = ['cache', 'mapping', provider]
        merged.pop('openai_compatible', None)
        return merged

    @staticmethod
    def _normalize_translation_provider(value) -> str:
        provider = str(value or '').strip()
        if provider == 'openai_compatible':
            provider = 'ai'
        return provider if provider in {'google_free', 'baidu', 'deepl', 'microsoft', 'ai'} else 'google_free'

    @classmethod
    def _first_network_translation_provider(cls, *orders) -> str:
        for order in orders:
            if not isinstance(order, list):
                continue
            for item in order:
                provider = cls._normalize_translation_provider(item)
                if str(item).strip() in {'cache', 'mapping'}:
                    continue
                if provider:
                    return provider
        return 'google_free'

    @property
    def translation_enabled(self) -> bool:
        return bool(self.translation.get('enabled', True))

    @property
    def translation_target_language(self) -> str:
        return str(self.translation.get('target_language') or 'zh-CN')

    @property
    def translation_provider(self) -> str:
        return self._normalize_translation_provider(self.translation.get('provider'))

    @property
    def translation_provider_order(self) -> list:
        return ['cache', 'mapping', self.translation_provider]

    @property
    def translation_batch_provider_order(self) -> list:
        return ['cache', 'mapping', self.translation_provider]

    @property
    def translation_batch_concurrency(self) -> int:
        return self._clamp_int(self.translation.get('batch_concurrency', 32) or 32, 32, 1, 64)

    @property
    def translation_batch_size(self) -> int:
        return self._clamp_int(self.translation.get('batch_size', 200) or 200, 200, 1, 200)

    @property
    def translation_batch_char_limit(self) -> int:
        return self._clamp_int(self.translation.get('batch_char_limit', 24000) or 24000, 24000, 500, 24000)

    @property
    def translation_source_page_size(self) -> int:
        return self._clamp_int(self.translation.get('source_page_size', 500) or 500, 500, 20, 1000)

    @property
    def translation_scan_pages_per_batch(self) -> int:
        return self._clamp_int(self.translation.get('scan_pages_per_batch', 8) or 8, 8, 1, 64)

    @property
    def translation_openai(self) -> dict:
        return self.openai_compatible

    # JavInfo API settings
    @property
    def javinfo(self) -> dict:
        return self._config.get('javinfo', {})

    @property
    def javhub_database(self) -> dict:
        database_cfg = self._config.get('database', {}) if isinstance(self._config.get('database'), dict) else {}
        defaults = {
            'host': os.getenv('JAVHUB_DB_HOST') or database_cfg.get('host') or 'localhost',
            'port': os.getenv('JAVHUB_DB_PORT') or database_cfg.get('port') or '5432',
            'database': os.getenv('JAVHUB_DB_NAME') or database_cfg.get('database') or 'javhub',
            'maintenance_database': (
                os.getenv('JAVHUB_DB_MAINTENANCE_DATABASE')
                or database_cfg.get('maintenance_database')
                or 'postgres'
            ),
            'user': os.getenv('JAVHUB_DB_USER') or database_cfg.get('user') or 'kongmei',
            'password': os.getenv('JAVHUB_DB_PASSWORD') or database_cfg.get('password') or '',
        }
        try:
            defaults['port'] = int(defaults.get('port') or 5432)
        except Exception:
            defaults['port'] = 5432
        for key in ('host', 'database', 'maintenance_database', 'user', 'password'):
            defaults[key] = str(defaults.get(key) or '').strip()
        return defaults

    @property
    def javinfo_import_db(self) -> dict:
        env_overrides = {
            'host': _first_env('', 'DB_HOST', 'POSTGRES_HOST'),
            'port': _first_env('', 'DB_PORT', 'POSTGRES_PORT'),
            'database': _first_env('', 'DB_NAME', 'POSTGRES_DB'),
            'maintenance_database': _first_env('', 'DB_MAINTENANCE_DATABASE'),
            'user': _first_env('', 'DB_USER', 'POSTGRES_USER'),
            'password': _first_env('', 'DB_PASSWORD', 'POSTGRES_PASSWORD'),
        }
        defaults = {
            'host': env_overrides['host'] or 'localhost',
            'port': env_overrides['port'] or '5432',
            'database': env_overrides['database'] or 'r18',
            'maintenance_database': env_overrides['maintenance_database'] or 'postgres',
            'user': env_overrides['user'] or 'javhub',
            'password': env_overrides['password'] or '',
            'max_parallel_jobs': 2,
            'keep_previous_databases': 1,
        }
        placeholders = {
            'host': {'localhost', '127.0.0.1', 'postgres'},
            'port': {'5432'},
            'database': {'r18'},
            'maintenance_database': {'postgres'},
            'user': {'kongmei', 'javhub'},
            'password': {'', 'change-me'},
        }
        javinfo_cfg = self._config.get('javinfo', {}) or {}
        import_db = javinfo_cfg.get('import_db', {}) if isinstance(javinfo_cfg, dict) else {}
        if not isinstance(import_db, dict):
            import_db = {}
        merged = {**defaults, **import_db}
        for key, env_value in env_overrides.items():
            raw_value = import_db.get(key)
            raw_text = str(raw_value or '').strip()
            if env_value and (key not in import_db or raw_text in placeholders.get(key, set())):
                merged[key] = env_value
        return normalize_javinfo_import_db_settings(merged, defaults=defaults)

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

    # Download sources settings
    @property
    def sources(self) -> dict:
        defaults = {
            'torznab': DEFAULT_TORZNAB_SOURCE.copy(),
        }
        cfg = self._config.get('sources', {}) or {}
        if not isinstance(cfg, dict):
            cfg = {}
        merged = {**defaults, **cfg}
        merged['torznab'] = {
            **defaults['torznab'],
            **(cfg.get('torznab', {}) if isinstance(cfg.get('torznab'), dict) else {}),
        }
        return merged

    @property
    def source_settings(self) -> dict:
        return self.sources

    @staticmethod
    def _clamp_int(value, default: int, minimum: int, maximum: int | None = None) -> int:
        try:
            normalized = int(value)
        except Exception:
            normalized = default
        if maximum is not None:
            normalized = min(normalized, maximum)
        return max(minimum, normalized)

    @staticmethod
    def _clamp_float(value, default: float, minimum: float, maximum: float) -> float:
        try:
            normalized = float(value)
        except Exception:
            normalized = default
        return max(minimum, min(normalized, maximum))

    def _normalize_torznab_source_config(self, item: dict, index: int) -> dict:
        cfg = item if isinstance(item, dict) else {}
        merged = {**DEFAULT_TORZNAB_SOURCE, **cfg}
        name = str(merged.get('name') or '').strip() or f'torznab-{index}'
        indexer = str(merged.get('indexer') or '').strip() or 'all'
        api_key = merged.get('api_key')
        if not api_key:
            api_key = os.getenv('JAVHUB_TORZNAB_API_KEY') or ''
        return {
            **merged,
            'enabled': bool(merged.get('enabled', False)),
            'name': name,
            'base_url': str(merged.get('base_url') or '').strip(),
            'api_key': str(api_key or ''),
            'indexer': indexer,
            'categories': str(merged.get('categories') or '').strip(),
            'limit': self._clamp_int(merged.get('limit'), 20, 1, 100),
            'timeout': self._clamp_int(merged.get('timeout'), 15, 1, 60),
        }

    @property
    def source_torznab_configs(self) -> list:
        source_cfg = self.sources
        candidates = []
        torznab_cfg = source_cfg.get('torznab')
        if isinstance(torznab_cfg, dict):
            candidates.append(torznab_cfg)
        instances = source_cfg.get('torznab_instances')
        if isinstance(instances, list):
            candidates.extend(item for item in instances if isinstance(item, dict))
        return [
            self._normalize_torznab_source_config(item, index + 1)
            for index, item in enumerate(candidates)
        ]

    @property
    def enabled_torznab_configs(self) -> list:
        return [item for item in self.source_torznab_configs if item.get('enabled')]

    @property
    def torznab_sources_config(self) -> list:
        return self.enabled_torznab_configs

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
        cfg.pop('metatube', None)
        cfg['_meta'] = {
            'config_path': str(self.config_path),
            'config_loaded': self.config_loaded,
            'config_load_error': self.config_load_error,
        }
        cfg['ai'] = self.ai
        cfg['automation'] = self.automation
        cfg['actor_mapping'] = self.actor_mapping
        cfg['translation'] = self.translation
        cfg['sources'] = self.sources
        javinfo_cfg = cfg.get('javinfo', {}) if isinstance(cfg.get('javinfo'), dict) else {}
        cfg['javinfo'] = {
            'page_size': javinfo_cfg.get('page_size', 30),
            'timeout': self.javinfo_timeout,
            **javinfo_cfg,
            'import_db': self.javinfo_import_db,
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
            current_ai = self._config.get('ai', {}) or {}
            legacy_translation = self._config.get('translation', {}) or {}
            legacy_openai = (
                legacy_translation.get('openai_compatible', {})
                if isinstance(legacy_translation, dict)
                else {}
            )
            for provider_key in ('openai_compatible', 'gemini', 'ollama'):
                incoming_provider = incoming['ai'].get(provider_key)
                if not isinstance(incoming_provider, dict) or incoming_provider.get('api_key'):
                    continue
                current_provider = current_ai.get(provider_key, {}) if isinstance(current_ai, dict) else {}
                existing_api_key = current_provider.get('api_key') if isinstance(current_provider, dict) else ''
                if not existing_api_key and provider_key == 'openai_compatible':
                    existing_api_key = legacy_openai.get('api_key') if isinstance(legacy_openai, dict) else ''
                if existing_api_key:
                    incoming_provider['api_key'] = existing_api_key
        if isinstance(incoming.get('translation'), dict):
            incoming_translation = incoming['translation']
            current_translation = self._config.get('translation', {}) or {}
            if isinstance(incoming_translation.get('baidu'), dict):
                incoming_baidu = incoming_translation['baidu']
                if not incoming_baidu.get('secret'):
                    current_baidu = current_translation.get('baidu', {}) if isinstance(current_translation, dict) else {}
                    existing_secret = current_baidu.get('secret') if isinstance(current_baidu, dict) else ''
                    if existing_secret:
                        incoming_baidu['secret'] = existing_secret
        self._config = self._merge_config(self._config, incoming)
        if isinstance(incoming.get('javinfo'), dict):
            _warn_if_legacy_javinfo_url(incoming['javinfo'].get('api_url', ''), 'config update')
        if 'ai' in incoming and isinstance(self._config.get('translation'), dict):
            self._config['translation'].pop('openai_compatible', None)
        config_path = self.config_path
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

sys.modules.setdefault("config", sys.modules[__name__])
sys.modules.setdefault("backend.config", sys.modules[__name__])
config = Config()
