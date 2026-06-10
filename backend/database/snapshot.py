"""快照和演员归一化数据库层"""
import hashlib
import time
import difflib
from typing import Optional
from database.base import get_db


# === Snapshot Key ===

def create_snapshot_key() -> str:
    return hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]


# === Emby Snapshots ===

def clear_snapshot(snapshot_key: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emby_snapshots WHERE snapshot_key = ?", (snapshot_key,))
        cursor.execute("DELETE FROM emby_actors WHERE snapshot_key = ?", (snapshot_key,))

def clone_snapshot(src_key: str) -> str:
    new_key = create_snapshot_key()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO emby_snapshots
                (snapshot_key, actress_id, actress_name, emby_item_id, title, filename, collected_at)
            SELECT ?, actress_id, actress_name, emby_item_id, title, filename, CURRENT_TIMESTAMP
            FROM emby_snapshots
            WHERE snapshot_key = ?
            ''',
            (new_key, src_key),
        )
        cursor.execute(
            '''
            UPDATE emby_actors
            SET snapshot_key = ?, updated_at = CURRENT_TIMESTAMP
            WHERE snapshot_key = ?
            ''',
            (new_key, src_key),
        )
    return new_key

def save_emvy_snapshot(snapshot_key: str, actress_id: int, actress_name: str, emby_item_id: str, title: str, filename: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO emby_snapshots (snapshot_key, actress_id, actress_name, emby_item_id, title, filename, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (snapshot_key, actress_id, actress_name, emby_item_id, title, filename))

def upsert_emvy_snapshot(snapshot_key: str, actress_id: int, actress_name: str, emby_item_id: str, title: str, filename: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM emby_snapshots WHERE snapshot_key = ? AND emby_item_id = ?",
            (snapshot_key, emby_item_id),
        )
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


def list_snapshot_keys() -> list[str]:
    """All known snapshot keys, newest-first."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT snapshot_key, MAX(updated_at) AS updated_at
            FROM emby_actors
            GROUP BY snapshot_key
            ORDER BY updated_at DESC NULLS LAST, snapshot_key DESC
            """,
        )
        return [row["snapshot_key"] for row in cursor.fetchall() if row.get("snapshot_key")]


def delete_emby_snapshot_rows(snapshot_key: str, emby_item_ids: list[str]) -> int:
    """Delete specific rows from ``emby_snapshots`` for a snapshot key.

    Used by the incremental collector to drop items that no longer exist in
    Emby — otherwise the snapshot grows monotonically and every removed item
    is silently treated as "still in the library" by subsequent compares.
    Returns the number of rows deleted.
    """
    ids = [str(item_id) for item_id in emby_item_ids if str(item_id or "").strip()]
    if not ids:
        return 0
    deleted = 0
    with get_db() as conn:
        cursor = conn.cursor()
        chunk = 500
        for start in range(0, len(ids), chunk):
            batch = ids[start:start + chunk]
            placeholders = ",".join("?" for _ in batch)
            cursor.execute(
                f"DELETE FROM emby_snapshots WHERE snapshot_key = ? AND emby_item_id IN ({placeholders})",
                [snapshot_key, *batch],
            )
            deleted += getattr(cursor, "rowcount", 0) or 0
    return deleted


def get_emby_item_ids_for_snapshot(snapshot_key: str) -> list[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT emby_item_id FROM emby_snapshots WHERE snapshot_key = ?",
            (snapshot_key,),
        )
        return [row["emby_item_id"] for row in cursor.fetchall() if row.get("emby_item_id")]


def prune_old_snapshots(keep: int = 5) -> list[str]:
    """Drop every snapshot beyond the most recent ``keep`` keys.

    Without this, ``clone_snapshot`` causes the ``emby_snapshots`` table to
    grow by ~one library worth of rows per incremental run. Returns the list
    of keys that were dropped.
    """
    keep = max(1, int(keep or 1))
    keys = list_snapshot_keys()
    if len(keys) <= keep:
        return []
    drop_keys = keys[keep:]
    for snapshot_key in drop_keys:
        clear_snapshot(snapshot_key)
    return drop_keys

def get_snapshot_created_at(snapshot_key: str) -> Optional[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT COALESCE(MAX(collected_at), CURRENT_TIMESTAMP) AS created_at
            FROM emby_snapshots
            WHERE snapshot_key = ?
            ''',
            (snapshot_key,),
        )
        row = cursor.fetchone()
        return row["created_at"] if row and row["created_at"] else None

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

def count_snapshot_actors(snapshot_key: str | None) -> int:
    if not snapshot_key:
        return 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM emby_actors WHERE snapshot_key = ?", (snapshot_key,))
        row = cursor.fetchone()
        return int(row["cnt"] if row else 0)

def get_snapshot_actor(snapshot_key: str, actress_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM emby_actors WHERE snapshot_key = ? AND actress_id = ? LIMIT 1",
            (snapshot_key, actress_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

def get_snapshot_videos(snapshot_key: str, actress_id: int) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM emby_snapshots WHERE snapshot_key = ? AND actress_id = ? ORDER BY title",
            (snapshot_key, actress_id)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def iter_snapshot_videos_by_actor(snapshot_key: str, actor_id: int | None = None, limit: int = 200) -> list:
    safe_limit = max(1, min(int(limit or 200), 1000))
    with get_db() as conn:
        cursor = conn.cursor()
        where_clause = "snapshot_key = ?"
        params: list = [snapshot_key]
        if actor_id is not None:
            where_clause += " AND actress_id = ?"
            params.append(int(actor_id))
        cursor.execute(
            f"""
            SELECT *
            FROM emby_snapshots
            WHERE {where_clause}
            ORDER BY title, emby_item_id
            LIMIT ?
            """,
            params + [safe_limit],
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_snapshot_filenames(snapshot_key: str) -> set:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM emby_snapshots WHERE snapshot_key = ?", (snapshot_key,))
        rows = cursor.fetchall()
        return {row["filename"] for row in rows if row["filename"]}

def get_snapshot_duplicate_candidates(snapshot_key: str) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT s.emby_item_id, s.title, s.filename
            FROM emby_snapshots s
            LEFT JOIN ignored_duplicates i ON i.emby_item_id = s.emby_item_id
            WHERE s.snapshot_key = ? AND i.emby_item_id IS NULL
            ORDER BY s.title, s.emby_item_id
            """,
            (snapshot_key,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# === Find Similar Actresses ===

def find_similar_actresses(
    snapshot_key: str,
    name: str = None,
    threshold: float = 0.6,
    limit: int = 50,
    candidate_limit: int = 250,
) -> list:
    """查找名字相似的演员（用于发现重复演员）"""
    size = max(2, min(int(candidate_limit or 250), 1000))
    max_results = max(1, min(int(limit or 50), 200))
    search = name.strip() if isinstance(name, str) and name.strip() else None
    result = get_snapshot_actors(
        snapshot_key,
        search=search,
        sort_by="total_videos",
        sort_order="desc",
        page=1,
        page_size=size,
    )
    candidates = result["data"]

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
                if len(similar) >= max_results:
                    break
        if len(similar) >= max_results:
            break
    similar.sort(key=lambda x: x["similarity"], reverse=True)
    return similar[:max_results]
