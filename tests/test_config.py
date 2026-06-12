import sys
import os
import importlib
from unittest.mock import mock_open
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config

def fresh_config(initial=None):
    c = object.__new__(Config)
    c._config = initial or {}
    return c

def test_config_singleton():
    c1 = Config()
    c2 = Config()
    assert c1 is c2

def test_config_defaults():
    c = fresh_config()
    assert c.open115_root_path == '/JavHub'
    assert c.crawler_request_interval == 3
    assert c.scheduler_check_hour == 2

def test_javinfo_api_url_defaults_to_18080(monkeypatch):
    monkeypatch.delenv('JAVINFO_API_URL', raising=False)
    c = fresh_config()
    assert c.javinfo_api_url == 'http://localhost:18080'

def test_javinfo_api_url_env_overrides_yaml(monkeypatch):
    monkeypatch.setenv('JAVINFO_API_URL', 'http://javinfo.internal:18080')
    c = fresh_config({'javinfo': {'api_url': 'http://localhost:8080'}})
    assert c.javinfo_api_url == 'http://javinfo.internal:18080'

def test_load_uses_javhub_config_path(monkeypatch, tmp_path):
    config_path = tmp_path / 'custom-config.yaml'
    config_path.write_text(
        'emby:\n'
        '  api_url: http://emby.example:8096\n'
        'javinfo:\n'
        '  api_url: http://javinfo.example:18080\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JAVHUB_CONFIG_PATH', str(config_path))

    c = fresh_config()
    c._load()

    assert c.emby_api_url == 'http://emby.example:8096'
    assert c.javinfo_api_url == 'http://javinfo.example:18080'
    assert c.config_path == config_path
    assert c.config_loaded is True

def test_config_path_metadata_flags_missing_file(monkeypatch, tmp_path):
    missing_path = tmp_path / 'missing.yaml'
    monkeypatch.setenv('JAVHUB_CONFIG_PATH', str(missing_path))

    c = fresh_config()
    c._load()

    assert c.config_path == missing_path
    assert c.config_loaded is False
    assert c.config_load_error

def test_backend_import_alias_uses_same_config_class():
    backend_config = importlib.import_module('backend.config')
    root_config = importlib.import_module('config')

    assert root_config.Config is backend_config.Config

def test_metatube_legacy_config_is_not_exposed():
    c = fresh_config({'metatube': {'host': 'legacy.example', 'port': 8081, 'token': 'secret'}})

    assert not hasattr(c, 'metatube')
    assert not hasattr(c, 'metatube_host')
    assert 'metatube' not in c.get_all()

def test_ai_defaults_include_provider_and_native_provider_configs():
    c = fresh_config()

    assert c.ai_provider == 'openai_compatible'
    assert c.ai['provider'] == 'openai_compatible'
    assert c.ai['openai_compatible']['base_url'] == 'https://api.openai.com/v1'
    assert c.ai['gemini']['base_url'] == 'https://generativelanguage.googleapis.com/v1beta'
    assert c.ai['ollama']['base_url'] == 'http://localhost:11434'

def test_legacy_translation_openai_config_populates_shared_ai_config():
    c = fresh_config({
        'translation': {
            'openai_compatible': {
                'base_url': 'https://legacy.example/v1',
                'api_key': 'legacy-token',
                'model': 'legacy-model',
            }
        }
    })

    assert c.ai_provider == 'openai_compatible'
    assert c.openai_compatible['base_url'] == 'https://legacy.example/v1'
    assert c.openai_compatible['api_key'] == 'legacy-token'
    assert c.openai_compatible['model'] == 'legacy-model'

def test_blank_ai_secret_update_preserves_existing_provider_secrets(monkeypatch):
    c = fresh_config({
        'ai': {
            'provider': 'gemini',
            'gemini': {
                'base_url': 'https://generativelanguage.googleapis.com/v1beta',
                'api_key': 'saved-gemini-token',
                'model': 'gemini-old',
                'timeout': 30,
            },
            'openai_compatible': {
                'base_url': 'https://openai.example/v1',
                'api_key': 'saved-openai-token',
                'model': 'old-openai',
                'timeout': 30,
            },
        }
    })

    c._merge_config = Config._merge_config.__get__(c, Config)
    monkeypatch.setattr('builtins.open', mock_open())
    c.update({'ai': {
        'provider': 'gemini',
        'gemini': {'api_key': '', 'model': 'gemini-new'},
        'openai_compatible': {'api_key': '', 'model': 'new-openai'},
    }})

    assert c.ai['gemini']['api_key'] == 'saved-gemini-token'
    assert c.ai['gemini']['model'] == 'gemini-new'
    assert c.ai['openai_compatible']['api_key'] == 'saved-openai-token'
    assert c.ai['openai_compatible']['model'] == 'new-openai'

def test_translation_defaults_include_single_provider_and_baidu_config():
    c = fresh_config()

    assert c.translation['provider'] == 'google_free'
    assert c.translation_provider == 'google_free'
    assert c.translation_provider_order == ['cache', 'mapping', 'google_free']
    assert c.translation_batch_provider_order == ['cache', 'mapping', 'google_free']
    assert c.translation['baidu']['enabled'] is False
    assert c.translation['baidu']['endpoint'] == 'https://fanyi-api.baidu.com/api/trans/vip/translate'
    assert c.translation['baidu']['qps'] == 1

def test_legacy_translation_order_selects_first_network_provider():
    c = fresh_config({
        'translation': {
            'provider_order': ['cache', 'mapping', 'baidu', 'deepl'],
            'baidu': {'enabled': True, 'app_id': 'appid'},
        }
    })

    assert c.translation_provider == 'baidu'
    assert c.translation_provider_order == ['cache', 'mapping', 'baidu']
    assert c.translation['baidu']['app_id'] == 'appid'

def test_blank_translation_secret_update_preserves_existing_secret(monkeypatch):
    c = fresh_config({
        'translation': {
            'provider': 'baidu',
            'baidu': {
                'enabled': True,
                'app_id': 'saved-app-id',
                'secret': 'saved-secret',
            },
        }
    })

    c._merge_config = Config._merge_config.__get__(c, Config)
    monkeypatch.setattr('builtins.open', mock_open())
    c.update({'translation': {'baidu': {'app_id': 'new-app-id', 'secret': ''}}})

    assert c.translation['baidu']['app_id'] == 'new-app-id'
    assert c.translation['baidu']['secret'] == 'saved-secret'
