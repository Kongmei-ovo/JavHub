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
