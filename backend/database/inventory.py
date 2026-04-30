"""库存对比数据库层"""
from typing import Optional
from database.base import get_db


# === Missing Summary ===

def save_missing_summary(actress_id: int, actress_name: str, total: int, missing: int, videos_json: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
        cursor.execute(
            "INSERT INTO actress_missing_summary (actress_id, actress_name, total_in_javinfo, missing_count, missing_videos_json, last_updated) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (actress_id, actress_name, total, missing, videos_json)
        )

def get_all_missing_summaries() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM actress_missing_summary ORDER BY missing_count DESC")
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

def update_inventory_job(job_id: int, status: str, error_msg: Optional[str] = None, snapshot_key: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if snapshot_key is not None:
            cursor.execute(
                "UPDATE inventory_jobs SET status = ?, error_msg = ?, snapshot_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_msg, snapshot_key, job_id)
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
        return [dict(row) for row in rows]

def get_inventory_job(job_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

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

def upsert_inventory_video(content_id: str, emby_item_id: str, actress_id: int, title: str, release_date: Optional[str], jacket_thumb_url: Optional[str]) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO inventory_videos (content_id, emby_item_id, actress_id, title, release_date, jacket_thumb_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO UPDATE SET
                emby_item_id = excluded.emby_item_id,
                actress_id = excluded.actress_id,
                title = excluded.title,
                release_date = excluded.release_date,
                jacket_thumb_url = excluded.jacket_thumb_url,
                updated_at = CURRENT_TIMESTAMP
        ''', (content_id, emby_item_id, actress_id, title, release_date, jacket_thumb_url))
        return actress_id

def get_inventory_videos(actress_id: int) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_videos WHERE actress_id = ? ORDER BY release_date DESC", (actress_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# === Missing Videos ===

def add_missing_video(content_id: str, actress_id: int, title: str, release_date: Optional[str], jacket_thumb_url: Optional[str]) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO missing_videos (content_id, actress_id, title, release_date, jacket_thumb_url, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO NOTHING
        ''', (content_id, actress_id, title, release_date, jacket_thumb_url))
        return cursor.lastrowid or 0

def get_missing_videos(actress_id: int) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM missing_videos WHERE actress_id = ? ORDER BY release_date DESC", (actress_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_all_missing_videos() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM missing_videos ORDER BY release_date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

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
