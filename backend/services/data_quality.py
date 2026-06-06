"""Data quality audit helpers for local inventory state."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from database import get_db, get_latest_snapshot_key, get_snapshot_duplicate_candidates


_CONTENT_ID_RE = re.compile(r"([A-Z0-9_]{2,18}-?\d{1,6}[A-Z]*)", re.IGNORECASE)
_PLACEHOLDER_COVER_RE = re.compile(r"(?:no[-_]?image|placeholder|default|blank|missing)", re.IGNORECASE)


def build_data_quality_overview(
    limit: int = 8,
    repair_progress: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return prioritized, actionable data-quality issues from local state."""
    bounded_limit = max(1, min(int(limit or 8), 50))
    snapshot_key = get_latest_snapshot_key()
    issues: list[dict[str, Any]] = []
    progress = repair_progress or {}

    duplicate_issue = _duplicate_issue(snapshot_key)
    if duplicate_issue:
        issues.append(duplicate_issue)
    issues.extend([
        issue
        for issue in (
            _missing_field_issue(snapshot_key),
            _invalid_field_issue(),
            _low_quality_cover_issue(progress.get("low_quality_cover")),
            _dead_link_issue(),
            _inconsistent_metadata_issue(),
        )
        if issue is not None
    ])

    issues.sort(key=lambda item: (-int(item["score"]), item["type"], item["id"]))
    visible_issues = issues[:bounded_limit]
    return {
        "status": "ok",
        "snapshot_key": snapshot_key,
        "summary": _summary(visible_issues),
        "issues": visible_issues,
    }


def _duplicate_issue(snapshot_key: str | None) -> dict[str, Any] | None:
    if not snapshot_key:
        return None
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for row in get_snapshot_duplicate_candidates(snapshot_key):
        item_id = str(row.get("emby_item_id") or "").strip()
        if not item_id:
            continue
        key = _content_key(row.get("title"), row.get("filename"))
        if not key:
            continue
        groups.setdefault(key, {})[item_id] = {
            "emby_item_id": item_id,
            "title": row.get("title") or "",
            "filename": row.get("filename") or "",
        }
    duplicates = [
        {"content_id": key, "duplicate_count": len(items), "items": list(items.values())[:4]}
        for key, items in groups.items()
        if len(items) > 1
    ]
    if not duplicates:
        return None
    duplicates.sort(key=lambda item: (-int(item["duplicate_count"]), item["content_id"]))
    count = sum(int(item["duplicate_count"]) for item in duplicates)
    return _issue(
        issue_type="duplicate_data",
        title="重复作品",
        summary=f"Emby 快照中发现 {len(duplicates)} 组同番号重复，优先处理会直接减少检索和播放时的误选。",
        count=count,
        base_score=92,
        samples=duplicates[:5],
        action={"label": "打开重复清理", "route": "/library-organize?tab=duplicates"},
    )


def _missing_field_issue(snapshot_key: str | None) -> dict[str, Any] | None:
    samples: list[dict[str, Any]] = []
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()
        if snapshot_key:
            cursor.execute(
                """
                SELECT emby_item_id, title, filename
                FROM emby_snapshots
                WHERE snapshot_key = ?
                  AND (COALESCE(title, '') = '' OR COALESCE(filename, '') = '')
                ORDER BY collected_at DESC, emby_item_id
                LIMIT 6
                """,
                (snapshot_key,),
            )
            snapshot_rows = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM emby_snapshots
                WHERE snapshot_key = ?
                  AND (COALESCE(title, '') = '' OR COALESCE(filename, '') = '')
                """,
                (snapshot_key,),
            )
            count += int(cursor.fetchone()["cnt"] or 0)
            samples.extend({
                "source": "emby_snapshot",
                "id": row.get("emby_item_id") or "",
                "missing_fields": [
                    field
                    for field in ("title", "filename")
                    if not str(row.get(field) or "").strip()
                ],
            } for row in snapshot_rows)

        cursor.execute(
            """
            SELECT id, content_id, title, actress_name
            FROM download_candidates
            WHERE COALESCE(content_id, '') = ''
               OR COALESCE(title, '') = ''
               OR COALESCE(actress_name, '') = ''
            ORDER BY created_at DESC, id DESC
            LIMIT 6
            """
        )
        candidate_rows = [dict(row) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM download_candidates
            WHERE COALESCE(content_id, '') = ''
               OR COALESCE(title, '') = ''
               OR COALESCE(actress_name, '') = ''
            """
        )
        count += int(cursor.fetchone()["cnt"] or 0)
    samples.extend({
        "source": "download_candidate",
        "id": row.get("id"),
        "content_id": row.get("content_id") or "",
        "missing_fields": [
            field
            for field in ("content_id", "title", "actress_name")
            if not str(row.get(field) or "").strip()
        ],
    } for row in candidate_rows)
    if count <= 0:
        return None
    return _issue(
        issue_type="missing_field",
        title="缺失关键字段",
        summary=f"{count} 条记录缺少标题、文件名或演员名，会降低搜索、排序和补全准确度。",
        count=count,
        base_score=76,
        samples=samples[:6],
        action={"label": "打开片库整理", "route": "/library-organize?tab=inventory"},
    )


def _invalid_field_issue() -> dict[str, Any] | None:
    samples: list[dict[str, Any]] = []
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, content_id, dvd_id, title
            FROM download_candidates
            WHERE COALESCE(content_id, '') <> ''
            ORDER BY created_at DESC, id DESC
            LIMIT 500
            """
        )
        rows = [dict(row) for row in cursor.fetchall()]
    for row in rows:
        raw_values = [
            str(row.get("content_id") or "").strip(),
            str(row.get("dvd_id") or "").strip(),
        ]
        if any(_is_valid_content_code(value) for value in raw_values):
            continue
        count += 1
        if len(samples) < 6:
            raw = raw_values[0] or raw_values[1]
            samples.append({
                "source": "download_candidate",
                "id": row.get("id"),
                "content_id": row.get("content_id") or "",
                "field": "content_id",
                "value": raw,
            })
    if count <= 0:
        return None
    return _issue(
        issue_type="invalid_field",
        title="错误字段值",
        summary=f"{count} 条候选的番号字段格式异常，可能造成重复索引、补全和下载匹配失败。",
        count=count,
        base_score=72,
        samples=samples,
        action={"label": "打开候选队列", "route": "/downloads?tab=candidates&status=candidate"},
    )


def _low_quality_cover_issue(repair_progress: dict[str, Any] | None = None) -> dict[str, Any] | None:
    samples: list[dict[str, Any]] = []
    count = 0
    checks = (
        ("inventory_videos", "content_id", "/library-organize?tab=inventory"),
        ("missing_videos", "content_id", "/library-organize?tab=inventory"),
        ("download_candidates", "id", "/downloads?tab=candidates&status=candidate"),
    )
    with get_db() as conn:
        cursor = conn.cursor()
        for table, id_field, _route in checks:
            cursor.execute(
                f"""
                SELECT {id_field} AS id, content_id, jacket_thumb_url
                FROM {table}
                WHERE COALESCE(jacket_thumb_url, '') = ''
                   OR jacket_thumb_url LIKE '%noimage%'
                   OR jacket_thumb_url LIKE '%placeholder%'
                   OR jacket_thumb_url LIKE '%default%'
                   OR jacket_thumb_url LIKE '%blank%'
                ORDER BY id
                LIMIT 6
                """
            )
            rows = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM {table}
                WHERE COALESCE(jacket_thumb_url, '') = ''
                   OR jacket_thumb_url LIKE '%noimage%'
                   OR jacket_thumb_url LIKE '%placeholder%'
                   OR jacket_thumb_url LIKE '%default%'
                   OR jacket_thumb_url LIKE '%blank%'
                """
            )
            count += int(cursor.fetchone()["cnt"] or 0)
            for row in rows:
                if len(samples) >= 6:
                    break
                samples.append({
                    "source": table,
                    "id": row.get("id"),
                    "content_id": row.get("content_id") or "",
                    "jacket_thumb_url": row.get("jacket_thumb_url") or "",
                })
    if count <= 0:
        return None
    issue = _issue(
        issue_type="low_quality_cover",
        title="低质量封面",
        summary=f"{count} 条记录缺少封面或使用占位封面，会明显影响卡片浏览体验。",
        count=count,
        base_score=62,
        samples=samples,
        action={"label": "筛选缺封面作品", "route": "/supplement?tab=movies&quality=missing_cover"},
    )
    normalized_progress = _repair_progress(repair_progress)
    if normalized_progress:
        issue["repair_progress"] = normalized_progress
        failed = _safe_int(normalized_progress.get("failed"))
        if failed > 0:
            blocked_score = 74 + min(15, failed // 5)
            issue["score"] = min(89, max(int(issue["score"]), blocked_score))
            issue["severity"] = _severity(int(issue["score"]))
            issue["priority_reason"] = f"{failed} 个补全任务失败，先处理补全来源再批量补封面。"
    return issue


def _dead_link_issue() -> dict[str, Any] | None:
    samples: list[dict[str, Any]] = []
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, content_id, jacket_thumb_url, magnet
            FROM download_candidates
            WHERE COALESCE(jacket_thumb_url, '') <> ''
               OR COALESCE(magnet, '') <> ''
            ORDER BY created_at DESC, id DESC
            LIMIT 500
            """
        )
        rows = [dict(row) for row in cursor.fetchall()]
    for row in rows:
        for field in ("jacket_thumb_url", "magnet"):
            value = str(row.get(field) or "").strip()
            if not value or _link_looks_live(value, field):
                continue
            count += 1
            if len(samples) < 6:
                samples.append({
                    "source": "download_candidate",
                    "id": row.get("id"),
                    "content_id": row.get("content_id") or "",
                    "field": field,
                    "value": value,
                })
    if count <= 0:
        return None
    return _issue(
        issue_type="dead_link",
        title="失效或不可用链接",
        summary=f"{count} 个链接格式不可用，下载候选或封面补全需要重新抓取。",
        count=count,
        base_score=68,
        samples=samples,
        action={"label": "打开补全来源诊断", "route": "/supplement?tab=sources"},
    )


def _inconsistent_metadata_issue() -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.content_id,
                   m.title AS missing_title,
                   i.title AS inventory_title,
                   m.release_date AS missing_release_date,
                   i.release_date AS inventory_release_date,
                   m.actress_id AS missing_actress_id,
                   i.actress_id AS inventory_actress_id
            FROM missing_videos m
            JOIN inventory_videos i ON i.content_id = m.content_id
            ORDER BY m.content_id
            LIMIT 6
            """
        )
        samples = [dict(row) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM missing_videos m
            JOIN inventory_videos i ON i.content_id = m.content_id
            """
        )
        count = int(cursor.fetchone()["cnt"] or 0)
    if count <= 0:
        return None
    return _issue(
        issue_type="inconsistent_metadata",
        title="不一致元数据",
        summary=f"{count} 个番号同时存在于库存和缺失列表，说明对比状态或来源元数据需要校准。",
        count=count,
        base_score=84,
        samples=samples,
        action={"label": "打开缺失列表", "route": "/library-organize?tab=inventory"},
    )


def _issue(
    *,
    issue_type: str,
    title: str,
    summary: str,
    count: int,
    base_score: int,
    samples: list[dict[str, Any]],
    action: dict[str, str],
) -> dict[str, Any]:
    score = min(100, base_score + min(max(count, 0), 10))
    return {
        "id": f"{issue_type}:{_sample_key(samples) or count}",
        "type": issue_type,
        "severity": _severity(score),
        "title": title,
        "summary": summary,
        "count": count,
        "score": score,
        "samples": samples,
        "action": action,
    }


def _severity(score: int) -> str:
    return "critical" if score >= 90 else "high" if score >= 75 else "medium" if score >= 55 else "low"


def _summary(issues: list[dict[str, Any]]) -> dict[str, Any]:
    severities = Counter(str(issue.get("severity") or "low") for issue in issues)
    by_type = {str(issue["type"]): int(issue["count"]) for issue in issues}
    return {
        "total_issues": len(issues),
        "critical": int(severities.get("critical", 0)),
        "high": int(severities.get("high", 0)),
        "medium": int(severities.get("medium", 0)),
        "low": int(severities.get("low", 0)),
        "by_type": by_type,
    }


def _repair_progress(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    queued = _safe_int(raw.get("queued"))
    running = _safe_int(raw.get("running"))
    failed = _safe_int(raw.get("failed"))
    if running > 0:
        state = "running"
    elif queued > 0:
        state = "queued"
    elif failed > 0:
        state = "blocked"
    else:
        state = "not_started"
    parts: list[str] = []
    if running:
        parts.append(f"{running} 运行")
    if queued:
        parts.append(f"{queued} 排队")
    if failed:
        parts.append(f"{failed} 失败")
    progress = {
        "state": state,
        "queued": queued,
        "running": running,
        "failed": failed,
        "label": f"补全修复 {' · '.join(parts)}" if parts else "暂无补全修复任务",
    }
    if failed > 0:
        progress["action"] = {
            "label": "查看失败补全任务",
            "route": "/supplement?tab=jobs&status=failed",
        }
    reasons = _repair_failed_reasons(raw.get("failed_reasons"))
    if reasons:
        progress["failed_reasons"] = reasons
        progress["reason_label"] = "失败原因 " + " · ".join(
            f"{reason['label']} {reason['count']}" for reason in reasons
        )
        if any(reason["label"] == "来源暂不可用" for reason in reasons):
            progress["reason_action"] = {
                "label": "检查补全来源",
                "route": "/supplement?tab=sources",
            }
    provider_failures = _repair_provider_failures(raw.get("provider_failures"))
    if provider_failures:
        visible_provider_failures = provider_failures[:4]
        progress["provider_failures"] = visible_provider_failures
        provider_parts = [
            f"{item['provider']} {item['count']}" for item in visible_provider_failures
        ]
        folded_provider_count = len(provider_failures) - len(visible_provider_failures)
        if folded_provider_count > 0:
            provider_parts.append(f"另 {folded_provider_count} 来源")
        progress["provider_label"] = "来源 " + " · ".join(provider_parts)
        progress["provider_actions"] = [
            {
                "provider": item["provider"],
                "label": _repair_provider_action_label(item),
                "route": _repair_provider_action_route(item),
            }
            for item in visible_provider_failures
        ]
    return progress


def _repair_provider_action_route(item: dict[str, Any]) -> str:
    provider = str(item.get("provider") or "").strip()
    route_source = str(item.get("route_source") or "").strip() or provider
    route = f"/supplement?tab=jobs&status=failed&source={route_source}"
    if route_source != provider:
        route += f"&error_provider={provider}"
    return route


def _repair_provider_action_label(item: dict[str, Any]) -> str:
    provider = str(item.get("provider") or "").strip()
    route_source = str(item.get("route_source") or "").strip()
    if route_source and route_source != provider:
        return f"查看含 {provider} 的失败"
    return f"查看 {provider} 失败"


def _repair_provider_failures(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    providers: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "").strip()
        count = _safe_int(item.get("count"))
        if provider and count:
            provider_failure = {"provider": provider, "count": count}
            route_source = str(item.get("route_source") or "").strip()
            if route_source:
                provider_failure["route_source"] = route_source
            providers.append(provider_failure)
    return providers


def _repair_failed_reasons(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    reasons: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        count = _safe_int(item.get("count"))
        if label and count:
            reasons.append({"label": label, "count": count})
    return reasons[:4]


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _content_key(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").upper()
        match = _CONTENT_ID_RE.search(text)
        if match:
            raw = match.group(1).upper()
            if "-" in raw:
                prefix, suffix = raw.split("-", 1)
                return f"{prefix}-{suffix}"
            split = re.match(r"^([A-Z]+)(\d+)$", raw)
            if split:
                return f"{split.group(1)}-{split.group(2)}"
            return raw
    return None


def _is_valid_content_code(value: str) -> bool:
    compact = value.upper().replace("-", "")
    if not compact or any(ch.isspace() for ch in value):
        return False
    key = _content_key(value)
    if not key:
        return False
    return key.replace("-", "") == compact


def _link_looks_live(value: str, field: str) -> bool:
    if field == "magnet":
        return value.startswith("magnet:?xt=urn:btih:")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return not _PLACEHOLDER_COVER_RE.search(value)


def _sample_key(samples: list[dict[str, Any]]) -> str:
    if not samples:
        return ""
    sample = samples[0]
    for key in ("content_id", "id", "emby_item_id"):
        value = sample.get(key)
        if value:
            return str(value)
    return ""
