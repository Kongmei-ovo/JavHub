"""Close the candidate→download→Emby loop.

For every candidate currently in ``sent`` status, check what really
happened on the downloader and Emby side and promote/revert the status:

- downloader task says ``failed``     → revert candidate to ``failed``
- downloader still in flight          → leave alone
- downloader done AND Emby has it     → promote to ``completed`` and remove
                                        the corresponding ``missing_videos``
                                        row so subsequent compares don't
                                        re-queue it
- downloader done but Emby missing    → leave alone (Emby may not have
                                        scanned yet); the next audit run
                                        will retry. If this persists for
                                        too long the candidate will surface
                                        in ops dashboards via the audit
                                        result counters.

This was the missing closing loop called out by the workflow audit. Without
it the system never learned which downloads actually succeeded, so missing
counts kept drifting and "candidate" rows accumulated indefinitely.
"""

from __future__ import annotations

import logging
from typing import Any

from database import (
    add_download_candidate_event,
    delete_missing_video,
    get_download_task,
    list_download_candidates,
    set_download_candidate_status,
)
from modules.code_matcher import normalize_code
from modules.emby_client import EmbyUnavailableError, get_emby_client

logger = logging.getLogger(__name__)

# Downloader task statuses that mean "no point waiting any longer".
_DOWNLOADER_TERMINAL_SUCCESS = {"completed", "success", "done", "finished", "seeding"}
_DOWNLOADER_TERMINAL_FAILURE = {"failed", "error", "cancelled", "canceled"}


def _candidate_code(candidate: dict) -> str:
    return str(candidate.get("dvd_id") or candidate.get("content_id") or "").strip()


async def audit_sent_candidates(limit: int = 500) -> dict[str, Any]:
    """Run one pass over ``sent`` candidates. See module docstring."""
    rows = list_download_candidates(status="sent", limit=limit)
    summary: dict[str, Any] = {
        "checked": len(rows),
        "completed": 0,
        "failed": 0,
        "pending": 0,
        "emby_unavailable": 0,
        "no_code": 0,
    }
    if not rows:
        return summary

    emby = get_emby_client()
    emby_skipped = False
    for candidate in rows:
        code = _candidate_code(candidate)
        if not normalize_code(code):
            summary["no_code"] += 1
            continue

        task_id = candidate.get("download_task_id")
        task = get_download_task(int(task_id)) if task_id else None
        task_status = str((task or {}).get("status") or "").lower()

        if task_status in _DOWNLOADER_TERMINAL_FAILURE:
            error_msg = (task or {}).get("error_msg") or "downloader reported failure"
            set_download_candidate_status(candidate["id"], "failed", error_msg=error_msg)
            add_download_candidate_event(
                candidate["id"],
                "audit_reverted_failed",
                f"download_task_id={task_id} status={task_status} error={error_msg}",
                "audit",
            )
            summary["failed"] += 1
            continue

        if task_status and task_status not in _DOWNLOADER_TERMINAL_SUCCESS:
            summary["pending"] += 1
            continue

        # Downloader is either done or status unknown (legacy rows) — defer
        # the final say to Emby. A confirmed Emby presence means we're done.
        if emby_skipped:
            summary["emby_unavailable"] += 1
            continue
        try:
            exists = await emby.check_exists(code)
        except EmbyUnavailableError:
            # Once Emby starts erroring we bail for the whole batch — the
            # next audit run will re-check. Treating an error as "not in
            # Emby" would risk demoting candidates that are actually fine.
            logger.warning("[SentAudit] Emby unavailable — skipping remaining checks")
            emby_skipped = True
            summary["emby_unavailable"] += 1
            continue

        if not exists:
            summary["pending"] += 1
            continue

        set_download_candidate_status(candidate["id"], "completed")
        add_download_candidate_event(
            candidate["id"],
            "audit_completed",
            f"download_task_id={task_id} status={task_status or 'unknown'}",
            "audit",
        )
        # Drop the matching missing_videos row so the next compare doesn't
        # immediately recreate this candidate.
        if candidate.get("content_id"):
            try:
                delete_missing_video(candidate["content_id"])
            except Exception:
                logger.debug("delete_missing_video failed for %s", candidate.get("content_id"))
        summary["completed"] += 1

    return summary
