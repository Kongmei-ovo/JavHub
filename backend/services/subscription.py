import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from database import (
    get_latest_snapshot_key,
    get_snapshot_actors,
    get_snapshot_videos,
    get_subscriptions,
    update_last_check,
)
from database.subscription import set_subscription_cooldown
from services.watchlist_pipeline import WatchlistPipeline, normalize_code

logger = logging.getLogger(__name__)

VALID_SUBSCRIPTION_SCOPES = {"actress", "maker", "series", "label"}
SNAPSHOT_PAGE_SIZE = 500
SUBSCRIPTION_CONCURRENCY = 8
CODE_PATTERN = re.compile(r"\b(?:FC2[-_\s]?(?:PPV[-_\s]?)?\d{3,8}|[A-Z]{2,10}[-_\s]?\d{2,8})\b", re.IGNORECASE)


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


def _movie_code(movie: dict) -> str:
    return str(movie.get("dvd_id") or movie.get("code") or movie.get("content_id") or "").strip()


def _snapshot_item_codes(item: dict) -> set[str]:
    codes: set[str] = set()
    for field in ("filename", "title", "Name", "FileName"):
        for match in CODE_PATTERN.finditer(str(item.get(field) or "")):
            code = normalize_code(match.group(0))
            if code:
                codes.add(code)
    return codes


def _load_latest_existing_codes() -> set[str] | None:
    try:
        snapshot_key = get_latest_snapshot_key()
        if not snapshot_key:
            logger.warning("No Emby snapshot available; falling back to per-code check_exists")
            return None

        existing_codes: set[str] = set()
        page = 1
        while True:
            actors_page = get_snapshot_actors(snapshot_key, page=page, page_size=SNAPSHOT_PAGE_SIZE)
            actors = actors_page.get("data", []) if isinstance(actors_page, dict) else []
            for actor in actors:
                actor_id = actor.get("actress_id")
                if actor_id is None:
                    continue
                for video in get_snapshot_videos(snapshot_key, actor_id):
                    existing_codes.update(_snapshot_item_codes(video))

            total_pages = actors_page.get("total_pages") if isinstance(actors_page, dict) else None
            if not isinstance(total_pages, int) or page >= total_pages:
                break
            page += 1

        logger.info("Loaded %s normalized codes from Emby snapshot %s", len(existing_codes), snapshot_key)
        return existing_codes
    except Exception as exc:
        logger.warning("Failed to load Emby snapshot; falling back to per-code check_exists: %s", exc)
        return None


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


async def _run_subscription_check(
    sub: dict,
    pipeline: WatchlistPipeline,
    *,
    existing_codes: set[str] | None = None,
    info_semaphore: asyncio.Semaphore | None = None,
) -> dict:
    identity = _subscription_identity(sub)
    scope = identity["scope"]
    if scope == "actress":
        # Drive the JavInfoApi supplement pipeline before reading the
        # filmography: without this, an actress whose supplement data never
        # got fetched silently checks against the bare r18 list forever.
        # TTL-deduped internally; the job is async upstream, so data lands by
        # this (or the next) check without blocking here.
        from services.supplement_autopilot import ensure_actress_supplement
        await ensure_actress_supplement(identity["target_id"])
        kwargs = {
            "actress_id": identity["target_id"],
            "actress_name": identity["target_label"],
            "trigger_source": "subscription",
            "reason": "subscription_check",
        }
        if existing_codes is not None:
            kwargs["existing_codes"] = existing_codes
        if existing_codes is not None and info_semaphore is not None:
            kwargs["info_semaphore"] = info_semaphore
        result = await pipeline.generate_candidates_for_actress(**kwargs)
    else:
        generator = getattr(pipeline, f"generate_candidates_for_{scope}")
        kwargs = {
            "target_id": identity["target_id"],
            "target_label": identity["target_label"],
            "trigger_source": "subscription",
            "reason": "subscription_check",
        }
        if existing_codes is not None:
            kwargs["existing_codes"] = existing_codes
        if existing_codes is not None and info_semaphore is not None:
            kwargs["info_semaphore"] = info_semaphore
        result = await generator(**kwargs)
    for movie in result.get("new_movies", []):
        if identity["target_label"]:
            movie["target_label"] = identity["target_label"]
        if identity["actress_name"]:
            movie["actress_name"] = identity["actress_name"]
        movie["subscription_id"] = sub["id"]
        movie["subscription_scope"] = scope
        movie["target_id"] = identity["target_id"]
    result.update(_subscription_result_identity(identity))
    latest = _movie_code(result.get("new_movies", [{}])[0]) if result.get("new_movies") else ""
    codes = _seen_codes_from_movies(result.get("new_movies", []))
    new_since_last = _new_codes_since_last(codes, sub.get("last_seen_codes") or [])
    result["new_since_last"] = new_since_last
    update_last_check(
        sub["id"],
        latest,
        last_seen_codes=_merge_seen_codes(sub.get("last_seen_codes") or [], codes),
        last_run_at=_now(),
        cooldown_until=None,
    )
    return result


async def _run_subscription_check_guarded(
    sub: dict,
    identity: dict,
    semaphore: asyncio.Semaphore,
    info_semaphore: asyncio.Semaphore,
    existing_codes: set[str] | None,
) -> dict:
    async with semaphore:
        pipeline = WatchlistPipeline()
        try:
            result = await _run_subscription_check(
                sub,
                pipeline,
                existing_codes=existing_codes,
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

    existing_codes = await asyncio.to_thread(_load_latest_existing_codes)
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
            existing_codes,
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
