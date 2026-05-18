import pytest
import sys
import os
from unittest.mock import mock_open
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config

def test_config_singleton():
    c1 = Config()
    c2 = Config()
    assert c1 is c2

def test_config_defaults():
    c = Config()
    assert c.openlist_default_path == '/115/AV'
    assert c.crawler_request_interval == 3
    assert c.scheduler_check_hour == 2

def test_javinfo_api_url_defaults_to_18080(monkeypatch):
    monkeypatch.delenv('JAVINFO_API_URL', raising=False)
    c = Config.__new__(Config)
    c._config = {}
    assert c.javinfo_api_url == 'http://localhost:18080'

def test_javinfo_api_url_env_overrides_yaml(monkeypatch):
    monkeypatch.setenv('JAVINFO_API_URL', 'http://javinfo.internal:18080')
    c = Config.__new__(Config)
    c._config = {'javinfo': {'api_url': 'http://localhost:8080'}}
    assert c.javinfo_api_url == 'http://javinfo.internal:18080'

def test_metatube_legacy_config_is_not_exposed():
    c = Config.__new__(Config)
    c._config = {'metatube': {'host': 'legacy.example', 'port': 8081, 'token': 'secret'}}

    assert not hasattr(c, 'metatube')
    assert not hasattr(c, 'metatube_host')
    assert 'metatube' not in c.get_all()

def test_ai_defaults_include_provider_and_native_provider_configs():
    c = Config.__new__(Config)
    c._config = {}

    assert c.ai_provider == 'openai_compatible'
    assert c.ai['provider'] == 'openai_compatible'
    assert c.ai['openai_compatible']['base_url'] == 'https://api.openai.com/v1'
    assert c.ai['gemini']['base_url'] == 'https://generativelanguage.googleapis.com/v1beta'
    assert c.ai['ollama']['base_url'] == 'http://localhost:11434'

def test_legacy_translation_openai_config_populates_shared_ai_config():
    c = Config.__new__(Config)
    c._config = {
        'translation': {
            'openai_compatible': {
                'base_url': 'https://legacy.example/v1',
                'api_key': 'legacy-token',
                'model': 'legacy-model',
            }
        }
    }

    assert c.ai_provider == 'openai_compatible'
    assert c.openai_compatible['base_url'] == 'https://legacy.example/v1'
    assert c.openai_compatible['api_key'] == 'legacy-token'
    assert c.openai_compatible['model'] == 'legacy-model'

def test_blank_ai_secret_update_preserves_existing_provider_secrets(monkeypatch):
    c = Config.__new__(Config)
    c._config = {
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
    }

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
