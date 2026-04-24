"""库存对比数据库层"""
from typing import Optional
from database.base import get_db_orig


# === Missing Summary ===

def save_missing_summary(actress_id: int, actress_name: str, total: int, missing: int, videos_json: str):
    """保存或更新缺失统计缓存"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
    cursor.execute(
        "INSERT INTO actress_missing_summary (actress_id, actress_name, total_in_javinfo, missing_count, missing_videos_json, last_updated) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (actress_id, actress_name, total, missing, videos_json)
    )
    conn.commit()
    conn.close()

def get_all_missing_summaries() -> list:
    """获取所有缺失统计缓存"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actress_missing_summary ORDER BY missing_count DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_missing_summary(actress_id: int) -> Optional[dict]:
    """获取指定演员的缺失统计"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# === Inventory Jobs ===

def add_inventory_job(job_type: str, actor_id: Optional[int] = None, snapshot_key: Optional[str] = None) -> int:
    """创建对比作业记录"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO inventory_jobs (job_type, actor_id, snapshot_key, status, created_at) VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
        (job_type, actor_id, snapshot_key)
    )
    conn.commit()
    job_id = cursor.lastrowid
    conn.close()
    return job_id

def update_inventory_job(job_id: int, status: str, error_msg: Optional[str] = None, snapshot_key: Optional[str] = None):
    """更新作业状态"""
    conn = get_db_orig()
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
    conn.commit()
    conn.close()

def update_inventory_progress(job_id: int, progress: int):
    """更新作业进度"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE inventory_jobs SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (progress, job_id)
    )
    conn.commit()
    conn.close()

def get_inventory_jobs(limit: int = 50) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_inventory_job(job_id: int) -> Optional[dict]:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# === Inventory Actors ===

def upsert_inventory_actor(actress_id: int, actress_name: str, normalized_id: Optional[int] = None, primary_name: Optional[str] = None) -> int:
    """插入或更新库存演员"""
    conn = get_db_orig()
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
    conn.commit()
    conn.close()
    return actress_id

def get_inventory_actors() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_actors ORDER BY actress_name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_inventory_actor(actress_id: int) -> Optional[dict]:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_actors WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_inventory_actor_stats(actress_id: int, total_videos: int, missing_count: int):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE inventory_actors SET total_videos = ?, missing_count = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
        (total_videos, missing_count, actress_id)
    )
    conn.commit()
    conn.close()

# === Inventory Videos ===

def upsert_inventory_video(content_id: str, emby_item_id: str, actress_id: int, title: str, release_date: Optional[str], jacket_thumb_url: Optional[str]) -> int:
    conn = get_db_orig()
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
    conn.commit()
    conn.close()
    return actress_id

def get_inventory_videos(actress_id: int) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_videos WHERE actress_id = ? ORDER BY release_date DESC", (actress_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# === Missing Videos ===

def add_missing_video(content_id: str, actress_id: int, title: str, release_date: Optional[str], jacket_thumb_url: Optional[str]) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO missing_videos (content_id, actress_id, title, release_date, jacket_thumb_url, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(content_id) DO NOTHING
    ''', (content_id, actress_id, title, release_date, jacket_thumb_url))
    conn.commit()
    conn.close()
    return cursor.lastrowid or 0

def get_missing_videos(actress_id: int) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM missing_videos WHERE actress_id = ? ORDER BY release_date DESC", (actress_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_missing_videos() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM missing_videos ORDER BY release_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_missing_video(content_id: str):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM missing_videos WHERE content_id = ?", (content_id,))
    conn.commit()
    conn.close()

def get_missing_count_by_actress(actress_id: int) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM missing_videos WHERE actress_id = ?", (actress_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# === Exempt Videos ===

def add_exempt_video(content_id: str, actress_id: int, reason: str, created_by: str = "manual") -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO exempt_videos (content_id, actress_id, reason, created_by, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(content_id) DO UPDATE SET
            reason = excluded.reason,
            actress_id = excluded.actress_id
    ''', (content_id, actress_id, reason, created_by))
    conn.commit()
    conn.close()
    return cursor.lastrowid or 0

def get_exempt_videos() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exempt_videos ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_exempt_video(content_id: str):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exempt_videos WHERE content_id = ?", (content_id,))
    conn.commit()
    conn.close()

def is_video_exempt(content_id: str) -> bool:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM exempt_videos WHERE content_id = ?", (content_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

# === Actor Aliases ===

def add_actor_alias(alias_id: int, canonical_id: int) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO actor_aliases (alias_id, canonical_id, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (alias_id, canonical_id)
    )
    conn.commit()
    conn.close()
    return alias_id

def get_actor_aliases() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actor_aliases")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_canonical_actress_id(actress_id: int) -> int:
    """递归查找规范演员ID"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT canonical_id FROM actor_aliases WHERE alias_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return get_canonical_actress_id(row["canonical_id"])
    return actress_id

def set_actor_primary_name(actress_id: int, primary_name: str):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory_actors SET primary_name = ? WHERE actress_id = ?", (primary_name, actress_id))
    conn.commit()
    conn.close()

def reassign_actress_movies(from_actress_id: int, to_actress_id: int):
    """将一个演员的所有电影转移到另一个演员（批量合并）"""
    conn = get_db_orig()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE inventory_videos SET actress_id = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
        (to_actress_id, from_actress_id)
    )
    cursor.execute(
        "UPDATE missing_videos SET actress_id = ? WHERE actress_id = ?",
        (to_actress_id, from_actress_id)
    )

    for table, id_field in [("inventory_videos", "actress_id"), ("missing_videos", "actress_id")]:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE actress_id = ?", (to_actress_id,))
        new_total = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM missing_videos WHERE actress_id = ?", (to_actress_id,))
        new_missing = cursor.fetchone()["cnt"]
        cursor.execute(
            "UPDATE inventory_actors SET total_videos = ?, missing_count = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
            (new_total, new_missing, to_actress_id)
        )

    cursor.execute("DELETE FROM emby_actors WHERE actress_id = ?", (from_actress_id,))
    conn.commit()
    conn.close()
    return True

def delete_emby_actor(actress_id: int):
    """从 emby_actors 表删除演员"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emby_actors WHERE actress_id = ?", (actress_id,))
    conn.commit()
    conn.close()

def get_actor_primary_name(actress_id: int) -> Optional[str]:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT primary_name FROM inventory_actors WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return row["primary_name"] if row else None
