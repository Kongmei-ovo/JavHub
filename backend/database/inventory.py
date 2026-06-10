"""库存对比数据库层"""
import json
import os
import time
from typing import Optional
from database.base import get_db


_MISSING_VIDEO_SCHEMA_KEYS: set[tuple[str | None, str | None, str | None]] = set()
_INVENTORY_VIDEO_SCHEMA_KEYS: set[tuple[str | None, str | None, str | None]] = set()


def _schema_key() -> tuple[str | None, str | None, str | None]:
    return (
        os.getenv("JAVHUB_DB_HOST"),
        os.getenv("JAVHUB_DB_PORT"),
        os.getenv("JAVHUB_DB_NAME"),
    )


def _ensure_missing_video_provenance_columns(cursor) -> None:
    schema_key = _schema_key()
    if schema_key in _MISSING_VIDEO_SCHEMA_KEYS:
        return
    cursor.execute("ALTER TABLE missing_videos ADD COLUMN IF NOT EXISTS matched_emby_item_id TEXT NULL")
    cursor.execute("ALTER TABLE missing_videos ADD COLUMN IF NOT EXISTS matched_filename TEXT NULL")
    _MISSING_VIDEO_SCHEMA_KEYS.add(schema_key)


def _ensure_inventory_video_provenance_columns(cursor) -> None:
    schema_key = _schema_key()
    if schema_key in _INVENTORY_VIDEO_SCHEMA_KEYS:
        return
    cursor.execute("ALTER TABLE inventory_videos ADD COLUMN IF NOT EXISTS matched_filename TEXT NULL")
    _INVENTORY_VIDEO_SCHEMA_KEYS.add(schema_key)


def _bump_missing_summary_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("missing_summaries", time.time_ns())
    except Exception:
        pass


# === Missing Summary ===

def save_missing_summary(actress_id: int, actress_name: str, total: int, missing: int, videos_json: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
        cursor.execute(
            "INSERT INTO actress_missing_summary (actress_id, actress_name, total_in_javinfo, missing_count, missing_videos_json, last_updated) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (actress_id, actress_name, total, missing, videos_json)
        )
        _bump_missing_summary_generation()

def get_all_missing_summaries() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM actress_missing_summary ORDER BY missing_count DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def list_missing_summary_index() -> list:
    """Return missing actor summaries without the large per-actor video JSON blob."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, actress_id, actress_name, total_in_javinfo, missing_count, last_updated
            FROM actress_missing_summary
            ORDER BY missing_count DESC
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_missing_summary(actress_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# === Inventory Jobs ===

def add_inventory_job(job_type: str, actor_id: Optional[int] = None, snapshot_key: Optional[str] = None) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO inventory_jobs (job_type, actor_id, snapshot_key, status, created_at) VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
            (job_type, actor_id, snapshot_key)
        )
        return cursor.lastrowid

def _decode_inventory_job(row) -> Optional[dict]:
    if not row:
        return None
    data = dict(row)
    raw_result = data.pop("result_json", None)
    if raw_result:
        try:
            data["result"] = json.loads(raw_result)
        except Exception:
            data["result"] = None
    else:
        data["result"] = None
    return data


def update_inventory_job(
    job_id: int,
    status: str,
    error_msg: Optional[str] = None,
    snapshot_key: Optional[str] = None,
    result: Optional[dict] = None,
):
    result_json = json.dumps(result, ensure_ascii=False) if result is not None else None
    with get_db() as conn:
        cursor = conn.cursor()
        if snapshot_key is not None and result is not None:
            cursor.execute(
                "UPDATE inventory_jobs SET status = ?, error_msg = ?, snapshot_key = ?, result_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_msg, snapshot_key, result_json, job_id)
            )
        elif snapshot_key is not None:
            cursor.execute(
                "UPDATE inventory_jobs SET status = ?, error_msg = ?, snapshot_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_msg, snapshot_key, job_id)
            )
        elif result is not None:
            cursor.execute(
                "UPDATE inventory_jobs SET status = ?, error_msg = ?, result_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_msg, result_json, job_id)
            )
        elif error_msg:
            cursor.execute(
                "UPDATE inventory_jobs SET status = ?, error_msg = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_msg, job_id)
            )
        else:
            cursor.execute(
                "UPDATE inventory_jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, job_id)
            )

def update_inventory_progress(job_id: int, progress: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE inventory_jobs SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (progress, job_id)
        )

def get_inventory_jobs(limit: int = 50) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [_decode_inventory_job(row) for row in rows]

def get_inventory_job(job_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return _decode_inventory_job(row)

# === Inventory Actors ===

def upsert_inventory_actor(actress_id: int, actress_name: str, normalized_id: Optional[int] = None, primary_name: Optional[str] = None) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO inventory_actors (actress_id, actress_name, normalized_id, primary_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(actress_id) DO UPDATE SET
                actress_name = excluded.actress_name,
                normalized_id = COALESCE(excluded.normalized_id, inventory_actors.normalized_id),
                primary_name = COALESCE(excluded.primary_name, inventory_actors.primary_name),
                updated_at = CURRENT_TIMESTAMP
        ''', (actress_id, actress_name, normalized_id, primary_name))
        return actress_id

def get_inventory_actors() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_actors ORDER BY actress_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_inventory_actors_by_ids(actress_ids: list[int]) -> list:
    ids = sorted({int(actress_id) for actress_id in actress_ids if actress_id is not None})
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM inventory_actors WHERE actress_id IN ({placeholders})",
            ids,
        )
        return [dict(row) for row in cursor.fetchall()]

def get_snapshot_actors_with_inventory_stats(
    snapshot_key: str,
    search: str = None,
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Page snapshot actors after joining inventory counts for correct missing_count sorting."""
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(int(page_size or 50), 500))
    offset = (safe_page - 1) * safe_page_size
    where_clause = "WHERE e.snapshot_key = ?"
    params: list = [snapshot_key]
    if search:
        where_clause += " AND e.actress_name LIKE ?"
        params.append(f"%{search}%")
    order_dir = "ASC" if sort_order == "asc" else "DESC"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM emby_actors e {where_clause}", params)
        total = int(cursor.fetchone()["cnt"] or 0)
        cursor.execute(
            f"""
            SELECT e.*,
                   COALESCE(i.missing_count, 0) AS missing_count,
                   COALESCE(i.primary_name, '') AS primary_name
            FROM emby_actors e
            LEFT JOIN inventory_actors i ON i.actress_id = e.actress_id
            {where_clause}
            ORDER BY COALESCE(i.missing_count, 0) {order_dir}, e.actress_name ASC
            LIMIT ? OFFSET ?
            """,
            params + [safe_page_size, offset],
        )
        rows = cursor.fetchall()

    return {
        "data": [dict(row) for row in rows],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "total_pages": (total + safe_page_size - 1) // safe_page_size if total > 0 else 1,
    }

def get_inventory_actor(actress_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_actors WHERE actress_id = ?", (actress_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_inventory_actor_stats(actress_id: int, total_videos: int, missing_count: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE inventory_actors SET total_videos = ?, missing_count = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
            (total_videos, missing_count, actress_id)
        )

# === Inventory Videos ===

def upsert_inventory_video(
    content_id: str,
    emby_item_id: str,
    actress_id: int,
    title: str,
    release_date: Optional[str],
    jacket_thumb_url: Optional[str],
    matched_filename: Optional[str] = None,
) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_inventory_video_provenance_columns(cursor)
        cursor.execute('''
            INSERT INTO inventory_videos (
                content_id, emby_item_id, actress_id, title, release_date, jacket_thumb_url,
                matched_filename, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO UPDATE SET
                emby_item_id = excluded.emby_item_id,
                actress_id = excluded.actress_id,
                title = excluded.title,
                release_date = excluded.release_date,
                jacket_thumb_url = excluded.jacket_thumb_url,
                matched_filename = COALESCE(excluded.matched_filename, inventory_videos.matched_filename),
                updated_at = CURRENT_TIMESTAMP
        ''', (content_id, emby_item_id, actress_id, title, release_date, jacket_thumb_url, matched_filename))
        return actress_id

def get_inventory_videos(actress_id: int) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_inventory_video_provenance_columns(cursor)
        cursor.execute(
            """
            SELECT inventory_videos.*, emby_item_id AS matched_emby_item_id
            FROM inventory_videos
            WHERE actress_id = ?
            ORDER BY release_date DESC
            """,
            (actress_id,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# === Missing Videos ===

def add_missing_video(
    content_id: str,
    actress_id: int,
    title: str,
    release_date: Optional[str],
    jacket_thumb_url: Optional[str],
    matched_emby_item_id: Optional[str] = None,
    matched_filename: Optional[str] = None,
) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_missing_video_provenance_columns(cursor)
        cursor.execute('''
            INSERT INTO missing_videos (
                content_id, actress_id, title, release_date, jacket_thumb_url,
                matched_emby_item_id, matched_filename, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO NOTHING
        ''', (content_id, actress_id, title, release_date, jacket_thumb_url, matched_emby_item_id, matched_filename))
        return cursor.lastrowid or 0

def get_missing_videos(actress_id: int) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_missing_video_provenance_columns(cursor)
        cursor.execute("SELECT * FROM missing_videos WHERE actress_id = ? ORDER BY release_date DESC", (actress_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_all_missing_videos() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_missing_video_provenance_columns(cursor)
        cursor.execute("SELECT * FROM missing_videos ORDER BY release_date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_missing_video(content_id: str) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_missing_video_provenance_columns(cursor)
        cursor.execute("SELECT * FROM missing_videos WHERE content_id = ?", (content_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_missing_videos_page(limit: int = 80, offset: int = 0) -> dict:
    page_size = max(1, min(int(limit or 80), 500))
    start = max(0, int(offset or 0))
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_missing_video_provenance_columns(cursor)
        cursor.execute("SELECT COUNT(*) FROM missing_videos")
        total = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT * FROM missing_videos ORDER BY release_date DESC LIMIT ? OFFSET ?",
            (page_size, start),
        )
        rows = cursor.fetchall()
    return {"data": [dict(row) for row in rows], "total": total, "limit": page_size, "offset": start}

def list_missing_actresses_from_inventory(limit: int = 200) -> list[dict]:
    """Aggregate ``missing_videos`` by actress for the ``/api/v1/missing`` API.

    Replaces the legacy two-step path (subscriptions → ``check_exists`` →
    actress_missing_summary cache) which double-counted, capped at the first
    100 works per actress, and turned every Emby blip into "everything is
    missing". This reads the same table ``run_compare_job`` writes into, so
    the numbers match the inventory module by construction.
    """
    page_size = max(1, min(int(limit or 200), 1000))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.actress_id,
                   COALESCE(i.primary_name, i.actress_name, MIN(m.title), '') AS actress_name,
                   COUNT(*) AS missing_count,
                   i.total_videos AS total_in_javinfo,
                   MAX(m.created_at) AS last_updated
            FROM missing_videos m
            LEFT JOIN inventory_actors i ON i.actress_id = m.actress_id
            GROUP BY m.actress_id, i.primary_name, i.actress_name, i.total_videos
            ORDER BY missing_count DESC, actress_name ASC
            LIMIT ?
            """,
            (page_size,),
        )
        rows = cursor.fetchall()
    return [
        {
            "actress_id": row["actress_id"],
            "actress_name": row.get("actress_name") or "",
            "missing_count": int(row.get("missing_count") or 0),
            "total_in_javinfo": int(row.get("total_in_javinfo") or 0),
            "last_updated": row.get("last_updated"),
        }
        for row in rows
    ]


def missing_videos_summary(limit: int = 8) -> dict:
    page_size = max(1, min(int(limit or 8), 50))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM missing_videos")
        total = int(cursor.fetchone()["cnt"] or 0)
        cursor.execute(
            '''
            SELECT m.actress_id,
                   COALESCE(i.primary_name, i.actress_name, MIN(m.title), '') AS actress_name,
                   COUNT(*) AS missing_count
            FROM missing_videos m
            LEFT JOIN inventory_actors i ON i.actress_id = m.actress_id
            GROUP BY m.actress_id, i.primary_name, i.actress_name
            ORDER BY missing_count DESC, actress_name ASC
            LIMIT ?
            ''',
            (page_size,),
        )
        rows = cursor.fetchall()
    return {
        "total": total,
        "top_actresses": [
            {
                "actress_id": row["actress_id"],
                "actress_name": row["actress_name"] or "",
                "missing_count": int(row["missing_count"] or 0),
            }
            for row in rows
        ],
    }

def delete_missing_video(content_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM missing_videos WHERE content_id = ?", (content_id,))

def get_missing_count_by_actress(actress_id: int) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM missing_videos WHERE actress_id = ?", (actress_id,))
        return cursor.fetchone()[0]

# === Exempt Videos ===

def add_exempt_video(content_id: str, actress_id: int, reason: str, created_by: str = "manual") -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO exempt_videos (content_id, actress_id, reason, created_by, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO UPDATE SET
                reason = excluded.reason,
                actress_id = excluded.actress_id
        ''', (content_id, actress_id, reason, created_by))
        return cursor.lastrowid or 0

def get_exempt_videos() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exempt_videos ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_exempt_video(content_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM exempt_videos WHERE content_id = ?", (content_id,))

def is_video_exempt(content_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM exempt_videos WHERE content_id = ?", (content_id,))
        return cursor.fetchone() is not None

# === Actor Aliases ===

def add_actor_alias(alias_id: int, canonical_id: int) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO actor_aliases (alias_id, canonical_id, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (alias_id, canonical_id)
        )
        return alias_id

def get_actor_aliases() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM actor_aliases")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_canonical_actress_id(actress_id: int) -> int:
    """递归查找规范演员ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT canonical_id FROM actor_aliases WHERE alias_id = ?", (actress_id,))
        row = cursor.fetchone()
        if row:
            return get_canonical_actress_id(row["canonical_id"])
        return actress_id

def set_actor_primary_name(actress_id: int, primary_name: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory_actors SET primary_name = ? WHERE actress_id = ?", (primary_name, actress_id))

def reassign_actress_movies(from_actress_id: int, to_actress_id: int):
    """将一个演员的所有电影转移到另一个演员（批量合并）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE inventory_videos SET actress_id = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
            (to_actress_id, from_actress_id)
        )
        cursor.execute(
            "UPDATE missing_videos SET actress_id = ? WHERE actress_id = ?",
            (to_actress_id, from_actress_id)
        )
        cursor.execute("SELECT COUNT(*) as cnt FROM inventory_videos WHERE actress_id = ?", (to_actress_id,))
        new_total = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM missing_videos WHERE actress_id = ?", (to_actress_id,))
        new_missing = cursor.fetchone()["cnt"]
        cursor.execute(
            "UPDATE inventory_actors SET total_videos = ?, missing_count = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
            (new_total, new_missing, to_actress_id)
        )
        cursor.execute("DELETE FROM emby_actors WHERE actress_id = ?", (from_actress_id,))
        return True

def delete_emby_actor(actress_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emby_actors WHERE actress_id = ?", (actress_id,))

def get_actor_primary_name(actress_id: int) -> Optional[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT primary_name FROM inventory_actors WHERE actress_id = ?", (actress_id,))
        row = cursor.fetchone()
        return row["primary_name"] if row else None
