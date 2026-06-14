"""One-time 115 → movie_resources backfill, plus the Emby↔resource parity gate.

The de-Emby cutover order is: take over existence (P3) → backfill historical 115
resources (here) → confirm parity → only then retire the snapshot collectors (P6).
Backfill reuses ``open115_downloader.register_movie_directory`` so historical
folders register through the exact same path as live finalize.
"""
from __future__ import annotations

import logging

from database import list_ready_video_movie_ids
from modules.code_matcher import normalize_code
from services.open115 import open115_client
from services.open115_downloader import decode_movie_directory, open115_downloader

logger = logging.getLogger(__name__)


async def import_115_library(*, client=None, downloader=None) -> dict:
    """Scan the 115 root for ``v1_<b64(movie_id)>`` folders and register each into
    ``movie_resources``. Folders we cannot decode (manual uploads) are counted and
    skipped, never guessed."""
    client = client or open115_client
    downloader = downloader or open115_downloader

    root_folder_id = await client.ensure_folder_path(client.root_path)
    imported_movies = 0
    imported_videos = 0
    imported_subtitles = 0
    skipped_dirs = 0

    async for entry in client.iter_files(root_folder_id):
        if not getattr(entry, "is_dir", False):
            continue
        name = str(getattr(entry, "name", "") or "")
        if not name.startswith("v1_"):
            skipped_dirs += 1
            continue
        try:
            movie_id = decode_movie_directory(name)
        except ValueError:
            skipped_dirs += 1
            continue

        counts = await downloader.register_movie_directory(movie_id, entry.file_id, task_id=None)
        if counts["video_count"] == 0:
            skipped_dirs += 1
            continue
        imported_movies += 1
        imported_videos += counts["video_count"]
        imported_subtitles += counts["subtitle_count"]

    result = {
        "imported_movies": imported_movies,
        "imported_videos": imported_videos,
        "imported_subtitles": imported_subtitles,
        "skipped_dirs": skipped_dirs,
    }
    logger.info("115 library backfill complete: %s", result)
    return result


def emby_resource_parity() -> dict:
    """Compare the latest Emby snapshot's codes against the resource library's
    ready videos. ``only_in_emby`` non-empty == there is still stock not backfilled
    — the gate that must clear before de-Emby (P6)."""
    from services.subscription import _load_latest_existing_codes

    emby_codes = _load_latest_existing_codes() or set()
    resource_codes = {
        code
        for code in (normalize_code(movie_id) for movie_id in list_ready_video_movie_ids())
        if code
    }

    in_both = emby_codes & resource_codes
    only_in_emby = emby_codes - resource_codes
    only_in_resources = resource_codes - emby_codes
    parity_ratio = (len(in_both) / len(emby_codes)) if emby_codes else 1.0

    return {
        "emby_total": len(emby_codes),
        "resource_total": len(resource_codes),
        "in_both": sorted(in_both),
        "only_in_emby": sorted(only_in_emby),
        "only_in_resources": sorted(only_in_resources),
        "parity_ratio": parity_ratio,
        # The hard gate: do not retire snapshot collection while Emby still has
        # codes the resource library hasn't backfilled.
        "ready_for_de_emby": len(only_in_emby) == 0,
    }
