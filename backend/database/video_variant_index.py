"""Persistence helpers for Phase 2 video variant groups."""
from __future__ import annotations

import json
from typing import Any

from database.base import get_db


_JOB_FIELDS = {"status", "total", "processed", "result", "result_json", "error"}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _decode_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _decode_labels(raw: str | None) -> list:
    if isinstance(raw, list):
        return raw
    labels = _decode_json(raw, [])
    return labels if isinstance(labels, list) else []


def _decode_job(row) -> dict | None:
    if not row:
        return None
    data = dict(row)
    data["result"] = _decode_json(data.pop("result_json", None), None)
    return data


def _group_payload(row, items: list[dict]) -> dict:
    data = dict(row)
    data["items"] = items
    return data


def replace_variant_groups(groups: list[dict]) -> dict:
    """Replace the variant index atomically after all new rows insert cleanly."""
    group_rows: list[tuple] = []
    item_rows: list[tuple] = []
    for group in groups:
        group_id = group.get("group_id")
        items = list(group.get("items") or [])
        group_rows.append(
            (
                group_id,
                group.get("canonical_code"),
                group.get("primary_content_id"),
                group.get("group_count", len(items)),
                group.get("confidence"),
            )
        )
        for rank, item in enumerate(items):
            item_rows.append(
                (
                    group_id,
                    item.get("content_id"),
                    item.get("dvd_id"),
                    item.get("display_code"),
                    item.get("service_code"),
                    _json_dumps(_decode_labels(item.get("variant_labels") or item.get("variant_labels_json"))),
                    item.get("sort_rank", rank),
                )
            )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM video_variant_group_items")
        cursor.execute("DELETE FROM video_variant_groups")
        if group_rows:
            cursor.executemany(
                '''
                INSERT INTO video_variant_groups (
                    group_id, canonical_code, primary_content_id, group_count, confidence, updated_at
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                group_rows,
            )
        if item_rows:
            cursor.executemany(
                '''
                INSERT INTO video_variant_group_items (
                    group_id, content_id, dvd_id, display_code, service_code, variant_labels_json, sort_rank
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                item_rows,
            )
    return {"group_count": len(group_rows), "item_count": len(item_rows)}


def get_variant_group_by_content_ids(content_ids: list[str]) -> dict[str, dict]:
    ids = [content_id for content_id in content_ids if content_id]
    if not ids:
        return {}

    placeholders = ",".join("?" for _ in ids)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f'''
            SELECT DISTINCT group_id
            FROM video_variant_group_items
            WHERE content_id IN ({placeholders})
            ''',
            ids,
        )
        group_ids = [row["group_id"] for row in cursor.fetchall()]
        if not group_ids:
            return {}

        group_placeholders = ",".join("?" for _ in group_ids)
        cursor.execute(
            f"SELECT * FROM video_variant_groups WHERE group_id IN ({group_placeholders})",
            group_ids,
        )
        groups = {row["group_id"]: dict(row) for row in cursor.fetchall()}
        cursor.execute(
            f'''
            SELECT *
            FROM video_variant_group_items
            WHERE group_id IN ({group_placeholders})
            ORDER BY group_id, sort_rank, content_id
            ''',
            group_ids,
        )
        items_by_group: dict[str, list[dict]] = {group_id: [] for group_id in group_ids}
        content_to_group: dict[str, str] = {}
        for row in cursor.fetchall():
            item = dict(row)
            item["variant_labels"] = _decode_labels(item.pop("variant_labels_json", None))
            items_by_group.setdefault(item["group_id"], []).append(item)
            if item["content_id"] in ids:
                content_to_group[item["content_id"]] = item["group_id"]

    result: dict[str, dict] = {}
    for content_id in ids:
        group_id = content_to_group.get(content_id)
        if group_id and group_id in groups:
            result[content_id] = _group_payload(groups[group_id], items_by_group.get(group_id, []))
    return result


def add_variant_group_job(status: str = "pending") -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO video_variant_group_jobs (status, created_at, updated_at) VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (status,),
        )
        return int(cursor.lastrowid)


def update_variant_group_job(job_id, **fields) -> dict | None:
    updates = []
    params = []
    for key, value in fields.items():
        if key not in _JOB_FIELDS or value is None:
            continue
        if key in {"result", "result_json"}:
            updates.append("result_json = ?")
            params.append(value if isinstance(value, str) else _json_dumps(value))
        else:
            updates.append(f"{key} = ?")
            params.append(value)
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(job_id)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE video_variant_group_jobs SET {', '.join(updates)} WHERE id = ?", params)
        if cursor.rowcount <= 0:
            return None
        cursor.execute("SELECT * FROM video_variant_group_jobs WHERE id = ?", (job_id,))
        return _decode_job(cursor.fetchone())


def get_variant_group_job(job_id) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM video_variant_group_jobs WHERE id = ?", (job_id,))
        return _decode_job(cursor.fetchone())


def list_variant_group_jobs(limit: int = 20) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM video_variant_group_jobs ORDER BY created_at DESC, id DESC LIMIT ?", (limit,))
        return [_decode_job(row) for row in cursor.fetchall()]


def variant_group_stats() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count, MAX(updated_at) AS last_built_at FROM video_variant_groups")
        group_row = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) AS count FROM video_variant_group_items")
        item_row = cursor.fetchone()
        cursor.execute("SELECT * FROM video_variant_group_jobs ORDER BY created_at DESC, id DESC LIMIT 1")
        last_job = _decode_job(cursor.fetchone())
    return {
        "group_count": int(group_row["count"] or 0),
        "item_count": int(item_row["count"] or 0),
        "last_built_at": group_row["last_built_at"],
        "last_job": last_job,
    }
