"""快照和演员归一化数据库层"""
import hashlib
import time
import difflib
from typing import Optional
from database.base import get_db


# === Snapshot Key ===

def create_snapshot_key() -> str:
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]


# === Emby Snapshots ===

def clear_snapshot(snapshot_key: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emby_snapshots WHERE snapshot_key = ?", (snapshot_key,))
        cursor.execute("DELETE FROM emby_actors WHERE snapshot_key = ?", (snapshot_key,))

def save_emvy_snapshot(snapshot_key: str, actress_id: int, actress_name: str, emby_item_id: str, title: str, filename: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO emby_snapshots (snapshot_key, actress_id, actress_name, emby_item_id, title, filename, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (snapshot_key, actress_id, actress_name, emby_item_id, title, filename))

def save_emby_actors_snapshot(snapshot_key: str, actors: list):
    with get_db() as conn:
        cursor = conn.cursor()
        for actor in actors:
            cursor.execute('''
                INSERT INTO emby_actors (actress_id, actress_name, total_videos, image_tag, snapshot_key, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(actress_id) DO UPDATE SET
                    actress_name = excluded.actress_name,
                    total_videos = excluded.total_videos,
                    image_tag = COALESCE(excluded.image_tag, emby_actors.image_tag),
                    snapshot_key = excluded.snapshot_key,
                    updated_at = CURRENT_TIMESTAMP
            ''', (actor["actress_id"], actor["actress_name"], actor["video_count"], actor.get("image_tag"), snapshot_key))

def get_latest_snapshot_key() -> Optional[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT snapshot_key FROM emby_actors ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row["snapshot_key"] if row else None

def get_snapshot_actors(snapshot_key: str, search: str = None, sort_by: str = None, sort_order: str = "asc",
                          page: int = 1, page_size: int = 50) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        where_clause = "WHERE snapshot_key = ?"
        params = [snapshot_key]
        if search:
            where_clause += " AND actress_name LIKE ?"
            params.append(f"%{search}%")

        cursor.execute(f"SELECT COUNT(*) as cnt FROM emby_actors {where_clause}", params)
        total = cursor.fetchone()["cnt"]

        order_col = "actress_name"
        if sort_by == "total_videos":
            order_col = "total_videos"
        elif sort_by == "missing_count":
            order_col = "actress_name"

        order_dir = "ASC" if sort_order == "asc" else "DESC"
        offset = (page - 1) * page_size

        sql = f"SELECT * FROM emby_actors {where_clause} ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return {
            "data": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
        }

def get_snapshot_videos(snapshot_key: str, actress_id: int) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM emby_snapshots WHERE snapshot_key = ? AND actress_id = ? ORDER BY title",
            (snapshot_key, actress_id)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_snapshot_filenames(snapshot_key: str) -> set:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM emby_snapshots WHERE snapshot_key = ?", (snapshot_key,))
        rows = cursor.fetchall()
        return {row["filename"] for row in rows if row["filename"]}


# === Find Similar Actresses ===

def find_similar_actresses(snapshot_key: str, name: str = None, threshold: float = 0.6) -> list:
    """查找名字相似的演员（用于发现重复演员）"""
    result = get_snapshot_actors(snapshot_key, page_size=10000)
    all_actors = result["data"]
    if name:
        candidates = [a for a in all_actors if name.lower() in a["actress_name"].lower()]
    else:
        candidates = all_actors

    similar = []
    checked = set()
    for i, a in enumerate(candidates):
        for j, b in enumerate(candidates):
            if i >= j or b["actress_id"] in checked:
                continue
            ratio = difflib.SequenceMatcher(None, a["actress_name"].lower(), b["actress_name"].lower()).ratio()
            if ratio >= threshold and a["actress_id"] != b["actress_id"]:
                similar.append({
                    "actor_a": a,
                    "actor_b": b,
                    "similarity": round(ratio, 2)
                })
                checked.add(b["actress_id"])
    similar.sort(key=lambda x: x["similarity"], reverse=True)
    return similar
