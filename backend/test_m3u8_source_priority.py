from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

from sources.m3u8_source import M3U8Source


def test_stream_sources_gives_jable_first_access_to_cf_session() -> None:
    source = M3U8Source()
    started: dict[str, float] = {}

    def fake_search(name: str):
        async def search(_avid: str):
            started[name] = time.monotonic()
            return None

        return search

    source._sites = lambda: [
        ("jable", fake_search("jable")),
        ("missav", fake_search("missav")),
        ("kanav", fake_search("kanav")),
        ("hohoj", fake_search("hohoj")),
    ]

    async def collect() -> None:
        async for _event in source.stream_sources("JUR-808"):
            pass

    with (
        patch("sources.m3u8_source._get_json_async", return_value=None),
        patch("sources.m3u8_source._set_json_async", return_value=None),
    ):
        asyncio.run(collect())

    assert started["jable"] < started["missav"] < started["kanav"]
    assert started["missav"] - started["jable"] >= 0.20
    assert started["kanav"] - started["jable"] >= 0.45
