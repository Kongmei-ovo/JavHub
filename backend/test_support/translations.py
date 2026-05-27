from __future__ import annotations

from unittest.mock import AsyncMock


def passthrough_video_translator() -> AsyncMock:
    translator = AsyncMock()
    translator.translate_videos.side_effect = lambda items, **_kwargs: items
    return translator


def noop_entity_translator() -> AsyncMock:
    translator = AsyncMock()
    translator.translate_entities.return_value = None
    return translator
