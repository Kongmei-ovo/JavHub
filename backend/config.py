import yaml
import os
import threading
from pathlib import Path
from typing import Optional

def _env(key: str, default: str = '') -> str:
    """读取环境变量，环境变量有值时优先于配置文件"""
    return os.getenv(key) or default

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

    def reload(self):
        self._load()

    @property
    def server_port(self) -> int:
        return self._config.get('server', {}).get('port', 18090)

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
    def emby_api_url(self) -> str:
        return self._config.get('emby', {}).get('api_url', '')

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

    # JavInfo API settings
    @property
    def javinfo(self) -> dict:
        return self._config.get('javinfo', {})

    @property
    def javinfo_api_url(self) -> str:
        return _env('JAVINFO_API_URL', self._config.get('javinfo', {}).get('api_url', 'http://localhost:8080'))

    @property
    def javinfo_timeout(self) -> int:
        return self._config.get('javinfo', {}).get('timeout', 30)

    # MetaTube settings
    @property
    def metatube(self) -> dict:
        return self._config.get('metatube', {})

    @property
    def metatube_host(self) -> str:
        return self._config.get('metatube', {}).get('host', 'localhost')

    @property
    def metatube_port(self) -> int:
        return self._config.get('metatube', {}).get('port', 8081)

    @property
    def metatube_token(self) -> str:
        return _env('METATUBE_TOKEN', self._config.get('metatube', {}).get('token', ''))

    # Download sources settings
    @property
    def sources(self) -> dict:
        return self._config.get('sources', {})

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
        return self._config.copy()

    def update(self, new_config: dict):
        self._config.update(new_config)
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

config = Config()
