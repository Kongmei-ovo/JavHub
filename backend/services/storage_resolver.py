"""存储后端换链抽象。

两条铁律（Emby 兼容层与所有播放出口共同遵守）：
1. content_id 是对外稳定 Id 的唯一来源。
2. 任何对外播放出口必须经 resolver 实时换链——直链有时效且可能绑 UA/IP，
   严禁缓存、入库、写日志。

预留：Open115Resolver（读 library_files.ref_payload 中的 pick_code，走 115 Open API
换链 + 可选转码 m3u8 + 生活事件增量），届时在 RESOLVERS 注册即可，表结构无需变更。
"""
from __future__ import annotations

from typing import Protocol

from services.openlist import ResolvedLink, openlist_client


class StorageResolver(Protocol):
    backend: str

    async def resolve_play_url(self, file: dict) -> ResolvedLink:
        """file 为 library_files 行 dict。返回值生命周期 = 单次请求。"""
        ...


class OpenListResolver:
    backend = "openlist"

    def __init__(self, client=None):
        self.client = client or openlist_client

    async def resolve_play_url(self, file: dict) -> ResolvedLink:
        return await self.client.resolve_link(file["path"])


RESOLVERS: dict[str, StorageResolver] = {"openlist": OpenListResolver()}


def get_resolver(backend: str) -> StorageResolver:
    resolver = RESOLVERS.get(backend)
    if resolver is None:
        raise KeyError(f"no storage resolver for backend: {backend}")
    return resolver
