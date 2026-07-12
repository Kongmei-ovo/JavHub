"""Acquisition session orchestrator.

A thin coordinator over the *existing* pipeline — it does not re-implement
search, ranking, offline submission, or resource registration. It drives the
per-movie session state machine (``searching → options_ready → submitted →
downloading → finalizing → ready|failed``) by reusing:

- ``candidate_processor.find_best_magnet`` for search + ranking,
- ``download_candidates.magnet_alternatives`` for the option list,
- ``downloader_service.create_download_task`` for the 115 offline submit,
- ``acquisition_session`` CRUD for the activity pointer.

Point-play and subscription share one chain: a new trigger for a movie that
already has an active session attaches to it instead of opening a second flow.
"""
from __future__ import annotations

import re

from modules.code_matcher import code_matches_any
from database.acquisition_session import (
    TERMINAL_STATUSES,
    get_acquisition_session,
    get_active_session_for_movie,
    get_or_create_active_session,
    mark_session_detached,
    update_acquisition_session,
)
from database.download import get_download_task
from database.download_candidate import (
    get_download_candidate,
    set_download_candidate_status,
    update_download_candidate_magnet_alternatives,
    upsert_download_candidate,
)
from database.movie_resource import code_has_ready_resource, list_movie_resources
from services.canonical_resolver import resolve_canonical_code
from services.candidate_processor import _download_uri, find_best_magnet
from services.downloader import downloader_service
from services.downloaders import get_downloaders_config

# Candidate rows opened by the acquisition flow live under their own source so
# they never collide with inventory/subscription candidates for the same code.
_ACQUISITION_SOURCE = "acquisition"
_BTIH_RE = re.compile(r"btih:([0-9a-zA-Z]+)", re.IGNORECASE)


def _info_hash_from_magnet(magnet: str | None) -> str | None:
    match = _BTIH_RE.search(str(magnet or ""))
    return match.group(1).lower() if match else None


def _resolve_open115_downloader_id() -> str:
    """Pick the enabled 115 downloader id; empty string lets create_download_task
    fall back to the configured default."""
    try:
        cfg = get_downloaders_config(include_sensitive=False)
    except Exception:
        return ""
    for client in cfg.get("clients", []) or []:
        if str(client.get("type")) == "open115" and client.get("enabled"):
            return str(client.get("id") or "")
    return ""


def _candidate_options(session: dict) -> list[dict]:
    candidate_id = session.get("candidate_id")
    if not candidate_id:
        return []
    candidate = get_download_candidate(candidate_id)
    if not candidate:
        return []
    options = candidate.get("magnet_alternatives")
    return options if isinstance(options, list) else []


def _snapshot_payload(session: dict | None, *, status_override: str | None = None) -> dict:
    if session is None:
        return {"status": "ready", "session": None, "options": [], "task": None, "resources": []}
    task = None
    if session.get("download_task_id"):
        task = get_download_task(session["download_task_id"])
    return {
        "status": status_override or session["status"],
        "session": session,
        "options": _candidate_options(session),
        "task": task,
        "resources": list_movie_resources(session["movie_id"]),
    }


def session_snapshot(session_id: int) -> dict | None:
    """Aggregate snapshot for the waiting page to poll: session state + option
    list + the bound offline task + currently registered resources."""
    session = get_acquisition_session(session_id)
    if session is None:
        return None
    return _snapshot_payload(session)


async def _submit_session(session_id: int, code: str, title: str, magnet: str) -> dict:
    update_acquisition_session(
        session_id, status="submitted", selected_info_hash=_info_hash_from_magnet(magnet)
    )
    task_id = await downloader_service.create_download_task(
        code, title, magnet, downloader_id=_resolve_open115_downloader_id()
    )
    session = get_acquisition_session(session_id)
    if session and session.get("candidate_id"):
        set_download_candidate_status(
            session["candidate_id"],
            "sent",
            download_task_id=task_id,
        )
    updated = update_acquisition_session(
        session_id, status="downloading", download_task_id=task_id
    )
    return _snapshot_payload(updated)


async def _search_register_maybe_submit(
    session_id: int, code: str, title: str, *, auto: bool
) -> dict:
    result = await find_best_magnet({"content_id": code, "code": code, "title": title})
    best = result.get("best") if isinstance(result, dict) else None
    if not best:
        # Nothing found: park in options_ready so a human can paste a magnet.
        return _snapshot_payload(update_acquisition_session(session_id, status="options_ready"))

    magnet = _download_uri(best)
    alternatives = (result.get("alternatives") if isinstance(result, dict) else None) or []
    candidate = upsert_download_candidate(
        content_id=code,
        title=title,
        source=_ACQUISITION_SOURCE,
        status="candidate",
        magnet=magnet or None,
        magnet_source=str(best.get("source") or best.get("name") or "") or None,
    )
    update_download_candidate_magnet_alternatives(candidate["id"], alternatives)
    update_acquisition_session(session_id, status="options_ready", candidate_id=candidate["id"])

    # Auto-submit only on an exact code match — never let a fuzzy hit (ABC-123
    # picking up ABC-1234) spend an offline slot unattended.
    exact = code_matches_any(code, [best.get("title"), best.get("name")])
    if auto and magnet and exact:
        return await _submit_session(session_id, code, title, magnet)
    return _snapshot_payload(get_acquisition_session(session_id))


async def start_acquisition(
    movie_id: str, *, auto: bool = True, trigger: str = "user", title: str | None = None
) -> dict:
    """Entry point for both point-play and subscription. Short-circuits when a
    ready resource already exists; otherwise reuses or opens the single active
    session for the movie."""
    requested = str(movie_id or "").strip()
    if not requested:
        raise ValueError("movie_id is required")
    # P4-2: key the whole acquisition (session / 115 folder / movie_resources)
    # by the canonical 番号 so a 番号's multiple products collapse into one
    # download + one owned work. A legacy product-keyed resource still counts as
    # ready so we never re-download something already on disk.
    code = resolve_canonical_code(requested)
    display_title = str(title or "").strip() or code

    requested_ready = requested != code and code_has_ready_resource(requested)
    if code_has_ready_resource(code) or requested_ready:
        owned_key = requested if requested_ready else code
        return {
            "status": "ready",
            "session": None,
            "options": [],
            "task": None,
            "resources": list_movie_resources(owned_key),
        }

    active = get_active_session_for_movie(code)
    if active is not None:
        return _snapshot_payload(active)

    session = get_or_create_active_session(movie_id=code, trigger=trigger)
    # Another trigger raced us and already advanced this session → attach to it.
    if session["status"] != "searching" or session.get("download_task_id"):
        return _snapshot_payload(session)

    return await _search_register_maybe_submit(session["id"], code, display_title, auto=auto)


def _resolve_choice(session: dict, *, index: int | None, magnet: str | None) -> str | None:
    if magnet:
        return str(magnet).strip()
    if index is None:
        return None
    options = _candidate_options(session)
    if 0 <= int(index) < len(options):
        return str(options[int(index)].get("magnet") or "").strip() or None
    return None


async def select_option(
    session_id: int,
    *,
    index: int | None = None,
    magnet: str | None = None,
    confirm: bool = False,
) -> dict:
    """Pick or paste an option. While a download is already in flight, choosing
    a *different* version appends a new task (additional resource) and never
    cancels the original — confirmation is required for that fan-out."""
    session = get_acquisition_session(session_id)
    if session is None:
        raise ValueError("session not found")
    if session["status"] in TERMINAL_STATUSES:
        raise ValueError("cannot select on a finished session")

    chosen = _resolve_choice(session, index=index, magnet=magnet)
    if not chosen:
        raise ValueError("no matching option to select")

    code = session["movie_id"]
    if session.get("download_task_id"):
        if not confirm:
            payload = _snapshot_payload(session)
            payload["needs_confirm"] = True
            return payload
        # Append an extra version; leave the original task untouched.
        await downloader_service.create_download_task(
            code, code, chosen, downloader_id=_resolve_open115_downloader_id()
        )
        return _snapshot_payload(get_acquisition_session(session_id))

    return await _submit_session(session_id, code, code, chosen)


async def retry(session_id: int) -> dict:
    """Re-run search/submit on an existing (typically failed or stalled) session."""
    session = get_acquisition_session(session_id)
    if session is None:
        raise ValueError("session not found")
    code = session["movie_id"]
    update_acquisition_session(session_id, status="searching", error_code=None, error_msg=None)
    return await _search_register_maybe_submit(session_id, code, code, auto=True)


def stop_waiting(session_id: int) -> dict:
    """Detach the waiting page; the background acquisition keeps running."""
    updated = mark_session_detached(session_id)
    if updated is None:
        raise ValueError("session not found")
    return _snapshot_payload(updated)
