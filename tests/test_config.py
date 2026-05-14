import pytest
import sys
import os
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
