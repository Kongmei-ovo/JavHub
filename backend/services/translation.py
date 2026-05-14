"""Backward-compatible translation service facade."""
import asyncio

from translations.service import (
    apply_translation as apply_translation_async,
    translate_item as _translate_item,
)


def apply_translation(content_id: str, data: dict) -> dict:
    """Sync compatibility wrapper for older callers."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(apply_translation_async(content_id, data))
    raise RuntimeError("apply_translation() cannot run inside an event loop; use translations.apply_translation()")
