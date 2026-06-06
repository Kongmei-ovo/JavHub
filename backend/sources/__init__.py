from __future__ import annotations

from sources.base import MagnetSource
from sources.registry import SourceRegistry
from sources.m3u8_source import M3U8Source
from sources.torznab_source import TorznabSource
from config import config

__all__ = [
    "MagnetSource",
    "SourceRegistry",
    "M3U8Source",
    "TorznabSource",
]

def register_all_sources():
    """注册所有下载源到全局注册表"""
    for name, source in list(SourceRegistry._sources.items()):
        if isinstance(source, TorznabSource):
            SourceRegistry._sources.pop(name, None)
            if name in SourceRegistry._priority:
                SourceRegistry._priority.remove(name)
    sources = [M3U8Source()]
    sources.extend(TorznabSource(**item) for item in config.enabled_torznab_configs)
    for source in sources:
        SourceRegistry.register(source)
