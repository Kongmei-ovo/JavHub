"""Emby actor -> JavInfo actress mapping database layer."""
from __future__ import annotations

from typing import Optional

from database.base import get_db


VALID_MAPPING_STATUSES = {"candidate", "confirmed", "ignored"}


def upsert_actor_mapping(
    emby_actor_id: str | int,
    emby_actor_name: str,
    javinfo_actress_id: int | None = None,
    javinfo_actress_name: str | None = None,
    confidence: float = 0,
    status: str = "candidate",
    source: str = "manual",
) -> int:
    """Create or update a mapping candidate/decision."""
    if status not in VALID_MAPPING_STATUSES:
        raise ValueError(f"invalid actor mapping status: {status}")
    emby_actor_id = str(emby_actor_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO actor_mappings (
                emby_actor_id, emby_actor_name, javinfo_actress_id, javinfo_actress_name,
                confidence, status, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(emby_actor_id, javinfo_actress_id) DO UPDATE SET
                emby_actor_name = excluded.emby_actor_name,
                javinfo_actress_name = COALESCE(excluded.javinfo_actress_name, actor_mappings.javinfo_actress_name),
                confidence = CASE
                    WHEN excluded.status = 'candidate' AND actor_mappings.status IN ('confirmed', 'ignored')
                    THEN actor_mappings.confidence
                    ELSE excluded.confidence
                END,
                status = CASE
                    WHEN excluded.status = 'candidate' AND actor_mappings.status IN ('confirmed', 'ignored')
                    THEN actor_mappings.status
                    ELSE excluded.status
                END,
                source = CASE
                    WHEN excluded.status = 'candidate' AND actor_mappings.status IN ('confirmed', 'ignored')
                    THEN actor_mappings.source
                    ELSE excluded.source
                END,
                updated_at = CURRENT_TIMESTAMP
            ''',
            (
                emby_actor_id,
                emby_actor_name,
                javinfo_actress_id,
                javinfo_actress_name,
                confidence,
                status,
                source,
            ),
        )
        if cursor.lastrowid:
            return cursor.lastrowid
        cursor.execute(
            "SELECT id FROM actor_mappings WHERE emby_actor_id = ? AND javinfo_actress_id IS ?",
            (emby_actor_id, javinfo_actress_id),
        )
        row = cursor.fetchone()
        return row["id"] if row else 0


def confirm_actor_mapping(
    emby_actor_id: str | int,
    emby_actor_name: str,
    javinfo_actress_id: int,
    javinfo_actress_name: str,
    confidence: float = 1.0,
    source: str = "manual",
) -> int:
    return upsert_actor_mapping(
        emby_actor_id=emby_actor_id,
        emby_actor_name=emby_actor_name,
        javinfo_actress_id=javinfo_actress_id,
        javinfo_actress_name=javinfo_actress_name,
        confidence=confidence,
        status="confirmed",
        source=source,
    )


def ignore_actor_mapping(
    emby_actor_id: str | int,
    emby_actor_name: str,
    javinfo_actress_id: int | None = None,
    javinfo_actress_name: str | None = None,
    source: str = "manual",
) -> int:
    if javinfo_actress_id is None:
        emby_actor_id = str(emby_actor_id)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id FROM actor_mappings
                WHERE emby_actor_id = ? AND javinfo_actress_id IS NULL
                LIMIT 1
                ''',
                (emby_actor_id,),
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    '''
                    UPDATE actor_mappings
                    SET emby_actor_name = ?, status = 'ignored', source = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    ''',
                    (emby_actor_name, source, row["id"]),
                )
                return row["id"]
    return upsert_actor_mapping(
        emby_actor_id=emby_actor_id,
        emby_actor_name=emby_actor_name,
        javinfo_actress_id=javinfo_actress_id,
        javinfo_actress_name=javinfo_actress_name,
        confidence=0,
        status="ignored",
        source=source,
    )


def list_actor_mappings(
    status: str | None = None,
    emby_actor_id: str | int | None = None,
    q: str | None = None,
    limit: int = 200,
) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        where = []
        params: list = []
        if status:
            where.append("status = ?")
            params.append(status)
        if emby_actor_id is not None:
            where.append("emby_actor_id = ?")
            params.append(str(emby_actor_id))
        if q:
            where.append("(emby_actor_name LIKE ? OR javinfo_actress_name LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        where_clause = f"WHERE {' AND '.join(where)}" if where else ""
        cursor.execute(
            f'''
            SELECT * FROM actor_mappings
            {where_clause}
            ORDER BY
                CASE status WHEN 'confirmed' THEN 0 WHEN 'candidate' THEN 1 ELSE 2 END,
                updated_at DESC,
                created_at DESC
            LIMIT ?
            ''',
            params + [limit],
        )
        return [dict(row) for row in cursor.fetchall()]


def get_confirmed_actor_mapping(emby_actor_id: str | int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM actor_mappings
            WHERE emby_actor_id = ? AND status = 'confirmed'
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            ''',
            (str(emby_actor_id),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_actor_mapping(mapping_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM actor_mappings WHERE id = ?", (mapping_id,))
        return cursor.rowcount > 0


def mapping_summary(snapshot_actors: list[dict] | None = None) -> dict:
    """Return mapping coverage for a snapshot actor list."""
    total = len(snapshot_actors or [])
    confirmed = 0
    ignored = 0
    if snapshot_actors:
        ids = [str(a.get("actress_id")) for a in snapshot_actors]
        placeholders = ",".join("?" for _ in ids)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'''
                SELECT emby_actor_id, status FROM actor_mappings
                WHERE emby_actor_id IN ({placeholders}) AND status IN ('confirmed', 'ignored')
                ''',
                ids,
            )
            by_actor = {row["emby_actor_id"]: row["status"] for row in cursor.fetchall()}
        confirmed = sum(1 for aid in ids if by_actor.get(aid) == "confirmed")
        ignored = sum(1 for aid in ids if by_actor.get(aid) == "ignored")
    return {
        "total": total,
        "confirmed": confirmed,
        "ignored": ignored,
        "unmapped": max(total - confirmed - ignored, 0),
        "coverage": (confirmed / total) if total else 0,
    }
