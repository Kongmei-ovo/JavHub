import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from config import config

from database import (
    candidate_content_id,
    candidate_title,
    code_has_ready_resource,
    get_active_session_for_movie,
    get_subscriptions,
    is_video_exempt,
    update_last_check,
    upsert_candidate_from_video,
)
from database.subscription import set_subscription_cooldown
from database.subscription_baseline import (
    add_to_baseline,
    establish_baseline,
    filter_new_against_baseline,
    get_baseline_at,
)
from services.acquisition import start_acquisition
from services.video_variants import is_non_movie_item
from services.watchlist_pipeline import WatchlistPipeline

logger = logging.getLogger(__name__)

VALID_SUBSCRIPTION_SCOPES = {"actress", "maker", "series", "label"}
SUBSCRIPTION_CONCURRENCY = 8


def _subscription_auto_acquire_enabled(sub: dict) -> bool:
    """Only the explicit full-auto policy may bypass the candidate queue.

    Previously every fresh release called ``start_acquisition(auto=True)`` even
    when the subscription explicitly disabled auto-download and the global
    policy was manual. Treating ``rules`` as full-auto was also unsafe: it
    bypassed candidate source rules, magnet requirements, and per-run/24h
    quotas. Under ``rules`` the release stays a subscription candidate and the
    normal scheduled candidate processor applies those controls.
    """
    return bool(sub.get("auto_download")) and config.automation_download_policy == "auto"


def _parse_timestamp(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _video_release_date(video: dict) -> datetime | None:
    return _parse_timestamp(video.get("release_date") or video.get("date"))


def _movie_code(movie: dict) -> str:
    return str(movie.get("dvd_id") or movie.get("code") or movie.get("content_id") or "").strip()


def _seen_codes_from_movies(movies: list[dict]) -> list[str]:
    seen: list[str] = []
    seen_set: set[str] = set()
    for movie in movies:
        code = _movie_code(movie)
        if code and code not in seen_set:
            seen.append(code)
            seen_set.add(code)
    return seen


def _new_codes_since_last(codes: list[str], last_seen_codes: list[str]) -> list[str]:
    previous = {str(code) for code in (last_seen_codes or []) if code}
    return [code for code in codes if code not in previous]


def _merge_seen_codes(previous: list[str], current: list[str], *, limit: int = 500) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for code in list(current) + list(previous or []):
        value = str(code).strip()
        if value and value not in seen:
            merged.append(value)
            seen.add(value)
        if len(merged) >= limit:
            break
    return merged


def _skip_reason(sub: dict, now: datetime) -> str | None:
    cooldown_until = _parse_timestamp(sub.get("cooldown_until"))
    if cooldown_until and cooldown_until > now:
        return "cooldown"

    last_run_at = _parse_timestamp(sub.get("last_run_at"))
    cadence_value = sub.get("cadence_minutes")
    cadence_minutes = int(cadence_value) if cadence_value is not None else 1440
    if cadence_minutes > 0 and last_run_at:
        next_run_at = last_run_at + timedelta(minutes=cadence_minutes)
        if next_run_at > now:
            return "cadence"
    return None


def _subscription_identity(sub: dict) -> dict:
    scope = str(sub.get("scope") or "actress").strip().lower()
    if scope not in VALID_SUBSCRIPTION_SCOPES:
        scope = "actress"

    if scope == "actress":
        target_id = sub.get("target_id") or sub.get("actress_id")
        target_label = sub.get("target_label") or sub.get("actress_name") or ""
        actress_id = sub.get("actress_id") or target_id
        actress_name = sub.get("actress_name") or target_label
    else:
        target_id = sub.get("target_id")
        target_label = sub.get("target_label") or sub.get("actress_name") or ""
        actress_id = sub.get("actress_id")
        actress_name = sub.get("actress_name") or ""

    return {
        "scope": scope,
        "target_id": int(target_id) if target_id is not None else None,
        "target_label": target_label,
        "actress_id": int(actress_id) if actress_id is not None else None,
        "actress_name": actress_name,
    }


def _subscription_result_identity(identity: dict) -> dict:
    data = {
        "scope": identity.get("scope"),
        "target_id": identity.get("target_id"),
        "target_label": identity.get("target_label") or "",
    }
    if identity.get("actress_id") is not None:
        data["actress_id"] = identity.get("actress_id")
    if identity.get("actress_name"):
        data["actress_name"] = identity.get("actress_name")
    return data


async def _fetch_filmography(
    pipeline: WatchlistPipeline,
    identity: dict,
    *,
    info_semaphore: asyncio.Semaphore | None,
) -> list[dict]:
    """Pipeline is used as a fetcher only — existence/trigger are decided here."""
    scope = identity["scope"]
    if scope == "actress":
        # Drive the JavInfoApi supplement pipeline before reading the
        # filmography: without this, an actress whose supplement data never got
        # fetched silently checks against the bare r18 list forever. TTL-deduped
        # internally; lands by this (or the next) check without blocking here.
        from services.supplement_autopilot import ensure_actress_supplement
        await ensure_actress_supplement(identity["target_id"])
        return await pipeline.fetch_actress_videos(
            identity["target_id"], info_semaphore=info_semaphore
        )
    fetch = getattr(pipeline, f"fetch_{scope}_videos")
    return await fetch(identity["target_id"], info_semaphore=info_semaphore)


async def _run_subscription_check(
    sub: dict,
    pipeline: WatchlistPipeline,
    *,
    info_semaphore: asyncio.Semaphore | None = None,
) -> dict:
    identity = _subscription_identity(sub)
    scope = identity["scope"]
    sub_id = sub["id"]

    videos = await _fetch_filmography(pipeline, identity, info_semaphore=info_semaphore)

    # Dedup to stable per-movie keys (content_id == movie_id == code).
    movie_videos: dict[str, dict] = {}
    for video in videos:
        if is_non_movie_item(video):
            continue
        code = candidate_content_id(video)
        if not code or is_video_exempt(code):
            continue
        movie_videos.setdefault(code, video)
    all_codes = list(movie_videos.keys())

    stats = {
        "checked": len(all_codes),
        "created": 0,
        "existing": 0,
        "skipped": 0,
        "skipped_exempt": 0,
        "in_library": 0,
        "candidate_count": 0,
    }

    # First check: record the whole filmography as the baseline, download nothing.
    baseline_at = _parse_timestamp(get_baseline_at(sub_id))
    if baseline_at is None:
        establish_baseline(sub_id, all_codes)
        result = {
            **stats,
            "baseline_established": True,
            "candidates": [],
            "new_movies": [],
            "new_since_last": [],
        }
        result.update(_subscription_result_identity(identity))
        update_last_check(sub_id, "", last_run_at=_now(), cooldown_until=None)
        return result

    new_codes = filter_new_against_baseline(sub_id, all_codes)
    auto_acquire = _subscription_auto_acquire_enabled(sub)

    candidates: list[dict] = []
    new_movies: list[dict] = []
    for code in new_codes:
        video = movie_videos[code]
        release_date = _video_release_date(video)
        is_fresh = (
            release_date is not None
            and baseline_at is not None
            and release_date > baseline_at
        )
        if is_fresh and auto_acquire:
            # Truly new release → auto-acquire, but never double-spend an offline
            # slot: skip if a resource is already ready or a session is active.
            if code_has_ready_resource(code):
                stats["in_library"] += 1
            elif get_active_session_for_movie(code) is not None:
                stats["existing"] += 1
            else:
                await start_acquisition(
                    code,
                    auto=True,
                    trigger="subscription",
                    title=candidate_title(video) or code,
                )
                stats["created"] += 1
        else:
            # Manual policy/disabled auto-download, dateless, or older than the
            # baseline: keep the release visible as a human candidate and never
            # spend an offline slot implicitly.
            candidates.append(
                upsert_candidate_from_video(
                    video=video,
                    actress_id=identity["actress_id"],
                    actress_name=identity["actress_name"],
                    source="subscription",
                    reason="subscription_check",
                )
            )
        add_to_baseline(sub_id, code)
        new_movies.append(
            {
                "code": code,
                "content_id": code,
                "dvd_id": video.get("dvd_id") or code,
                "title": candidate_title(video),
                "release_date": video.get("release_date"),
                "actress_name": identity["actress_name"] or None,
                "target_label": identity["target_label"] or None,
                "subscription_id": sub_id,
                "subscription_scope": scope,
                "target_id": identity["target_id"],
            }
        )

    stats["candidate_count"] = len(candidates)
    fresh = _seen_codes_from_movies(new_movies)
    result = {
        **stats,
        "candidates": candidates,
        "new_movies": new_movies,
        "new_since_last": fresh,
    }
    result.update(_subscription_result_identity(identity))
    update_last_check(
        sub_id,
        fresh[0] if fresh else "",
        last_run_at=_now(),
        cooldown_until=None,
    )
    return result


async def _run_subscription_check_guarded(
    sub: dict,
    identity: dict,
    semaphore: asyncio.Semaphore,
    info_semaphore: asyncio.Semaphore,
) -> dict:
    async with semaphore:
        pipeline = WatchlistPipeline()
        try:
            result = await _run_subscription_check(
                sub,
                pipeline,
                info_semaphore=info_semaphore,
            )
            return {"subscription": sub, "identity": identity, "result": result}
        except Exception as exc:
            logger.error(f"检查订阅失败 {identity.get('target_label')}: {exc}")
            set_subscription_cooldown(sub["id"], _now() + timedelta(minutes=30), last_run_at=_now())
            return {"subscription": sub, "identity": identity, "error": exc}


def get_all_subscriptions() -> List[dict]:
    """获取所有订阅"""
    return get_subscriptions()


async def check_all_subscriptions() -> List[dict]:
    """
    检查所有订阅的新片
    使用 JavInfoApi include_supplement=1 获取完整片单，缺失项写入下载候选。
    """
    report = await check_all_subscriptions_report()
    return report.get("movies", [])


async def check_all_subscriptions_report() -> dict:
    """Check all subscriptions and return structured candidate pipeline stats."""
    subscriptions = get_subscriptions()
    results = []
    movies = []
    new_since_last = []
    totals = {
        "subscriptions_checked": 0,
        "subscriptions_baselined": 0,
        "subscriptions_skipped_cadence": 0,
        "subscriptions_skipped_cooldown": 0,
        "subscriptions_failed": 0,
        "checked": 0,
        "created": 0,
        "existing": 0,
        "skipped": 0,
        "skipped_exempt": 0,
        "in_library": 0,
        "candidate_count": 0,
    }

    # Existence is now resource-backed (per-code) inside _run_subscription_check;
    # the Emby snapshot path (_load_latest_existing_codes) is retired from the main
    # flow but kept for rollback until P6.
    subscription_semaphore = asyncio.Semaphore(SUBSCRIPTION_CONCURRENCY)
    info_semaphore = asyncio.Semaphore(SUBSCRIPTION_CONCURRENCY)
    tasks = []

    for sub in subscriptions:
        if not sub.get("enabled"):
            continue

        identity = _subscription_identity(sub)
        if not identity.get("target_id") or not identity.get("target_label"):
            continue

        skip_reason = _skip_reason(sub, _now())
        if skip_reason:
            totals[f"subscriptions_skipped_{skip_reason}"] += 1
            results.append({
                "subscription_id": sub["id"],
                **_subscription_result_identity(identity),
                "skipped_reason": skip_reason,
                "new_since_last": [],
            })
            continue

        tasks.append(_run_subscription_check_guarded(
            sub,
            identity,
            subscription_semaphore,
            info_semaphore,
        ))

    for task_result in await asyncio.gather(*tasks):
        sub = task_result["subscription"]
        identity = task_result["identity"]
        if "error" in task_result:
            totals["subscriptions_failed"] += 1
            results.append({
                "subscription_id": sub["id"],
                **_subscription_result_identity(identity),
                "error": str(task_result["error"]),
                "new_since_last": [],
            })
            continue

        result = task_result["result"]

        totals["subscriptions_checked"] += 1
        if result.get("baseline_established"):
            totals["subscriptions_baselined"] += 1
        for key in ("checked", "created", "existing", "skipped", "skipped_exempt", "in_library", "candidate_count"):
            totals[key] += int(result.get(key) or 0)
        fresh_codes = result.get("new_since_last", [])
        new_since_last.extend(fresh_codes)
        fresh_code_set = set(fresh_codes)
        movies.extend([
            movie for movie in result.get("new_movies", [])
            if _movie_code(movie) in fresh_code_set
        ])
        results.append({
            "subscription_id": sub["id"],
            **_subscription_result_identity(identity),
            **result,
        })

    return {
        "status": "ok",
        **totals,
        "new_found": len(movies),
        "new_since_last": new_since_last,
        "movies": movies,
        "results": results,
    }


async def check_single_subscription(subscription_id: int) -> Optional[dict]:
    """检查单条订阅"""
    subs = get_subscriptions()
    sub = next((s for s in subs if s["id"] == subscription_id), None)
    if not sub:
        return None

    pipeline = WatchlistPipeline()
    identity = _subscription_identity(sub)
    result = await _run_subscription_check(sub, pipeline)
    if identity["scope"] == "actress":
        videos = await pipeline.fetch_actress_videos(identity["target_id"], page_size=10)
    else:
        fetcher = getattr(pipeline, f"fetch_{identity['scope']}_videos")
        videos = await fetcher(identity["target_id"], page_size=10)
    latest_movies = [
        {
            "code": video.get("dvd_id") or video.get("content_id"),
            "title": video.get("title_ja") or video.get("title_en") or video.get("title", ""),
        }
        for video in videos[:10]
        if video.get("dvd_id") or video.get("content_id")
    ]

    return {
        **_subscription_result_identity(identity),
        "latest_movies": latest_movies,
        **result,
    }
