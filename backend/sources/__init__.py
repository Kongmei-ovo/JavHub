from __future__ import annotations

from sources.base import MagnetSource
from sources.registry import SourceRegistry
from sources.javbus_source import JavBusSource
from sources.javdb_source import JavDBSource
from sources.javlib_source import JavLibSource
from sources.m3u8_source import M3U8Source

__all__ = [
    "MagnetSource",
    "SourceRegistry",
    "JavBusSource",
    "JavDBSource",
    "JavLibSource",
    "M3U8Source",
]

def register_all_sources():
    """注册所有下载源到全局注册表"""
    sources = [JavBusSource(), JavDBSource(), JavLibSource()]
    for source in sources:
        SourceRegistry.register(source)
