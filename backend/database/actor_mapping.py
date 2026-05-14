"""Emby actor -> JavInfo actress mapping database layer."""
from __future__ import annotations

import json
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
    javinfo_avatar_url: str | None = None,
    movie_count: int | None = None,
    confidence_breakdown: dict | None = None,
    confidence_label: str | None = None,
    risk_flags: list[str] | None = None,
) -> int:
    """Create or update a mapping candidate/decision."""
    if status not in VALID_MAPPING_STATUSES:
        raise ValueError(f"invalid actor mapping status: {status}")
    emby_actor_id = str(emby_actor_id)
    confidence_breakdown_json = json.dumps(confidence_breakdown or {}, ensure_ascii=False) if confidence_breakdown else None
    risk_flags_json = json.dumps(risk_flags or [], ensure_ascii=False) if risk_flags is not None else None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO actor_mappings (
                emby_actor_id, emby_actor_name, javinfo_actress_id, javinfo_actress_name,
                confidence, status, source, javinfo_avatar_url, movie_count,
                confidence_breakdown_json, confidence_label, risk_flags_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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
                javinfo_avatar_url = COALESCE(excluded.javinfo_avatar_url, actor_mappings.javinfo_avatar_url),
                movie_count = COALESCE(excluded.movie_count, actor_mappings.movie_count),
                confidence_breakdown_json = COALESCE(excluded.confidence_breakdown_json, actor_mappings.confidence_breakdown_json),
                confidence_label = COALESCE(excluded.confidence_label, actor_mappings.confidence_label),
                risk_flags_json = COALESCE(excluded.risk_flags_json, actor_mappings.risk_flags_json),
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
                javinfo_avatar_url,
                movie_count,
                confidence_breakdown_json,
                confidence_label,
                risk_flags_json,
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


def update_actor_mapping_ai_review(
    emby_actor_id: str | int,
    javinfo_actress_id: int,
    ai_decision: str,
    ai_confidence: float,
    ai_reason: str,
    ai_model: str,
) -> int:
    """Persist AI review metadata for an existing or newly-created candidate pair."""
    emby_actor_id = str(emby_actor_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE actor_mappings
            SET ai_decision = ?, ai_confidence = ?, ai_reason = ?, ai_model = ?,
                ai_reviewed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE emby_actor_id = ? AND javinfo_actress_id = ?
            ''',
            (ai_decision, ai_confidence, ai_reason, ai_model, emby_actor_id, javinfo_actress_id),
        )
        if cursor.rowcount:
            cursor.execute(
                "SELECT id FROM actor_mappings WHERE emby_actor_id = ? AND javinfo_actress_id = ?",
                (emby_actor_id, javinfo_actress_id),
            )
            row = cursor.fetchone()
            return row["id"] if row else 0
        return 0


def confirm_actor_mapping(
    emby_actor_id: str | int,
    emby_actor_name: str,
    javinfo_actress_id: int,
    javinfo_actress_name: str,
    confidence: float = 1.0,
    source: str = "manual",
    javinfo_avatar_url: str | None = None,
    movie_count: int | None = None,
    confidence_breakdown: dict | None = None,
    confidence_label: str | None = None,
    risk_flags: list[str] | None = None,
) -> int:
    return upsert_actor_mapping(
        emby_actor_id=emby_actor_id,
        emby_actor_name=emby_actor_name,
        javinfo_actress_id=javinfo_actress_id,
        javinfo_actress_name=javinfo_actress_name,
        confidence=confidence,
        status="confirmed",
        source=source,
        javinfo_avatar_url=javinfo_avatar_url,
        movie_count=movie_count,
        confidence_breakdown=confidence_breakdown,
        confidence_label=confidence_label,
        risk_flags=risk_flags,
    )


def ignore_actor_mapping(
    emby_actor_id: str | int,
    emby_actor_name: str,
    javinfo_actress_id: int | None = None,
    javinfo_actress_name: str | None = None,
    source: str = "manual",
    javinfo_avatar_url: str | None = None,
    movie_count: int | None = None,
    confidence_breakdown: dict | None = None,
    confidence_label: str | None = None,
    risk_flags: list[str] | None = None,
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
        javinfo_avatar_url=javinfo_avatar_url,
        movie_count=movie_count,
        confidence_breakdown=confidence_breakdown,
        confidence_label=confidence_label,
        risk_flags=risk_flags,
    )


def _json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except Exception:
        return []
    return value if isinstance(value, list) else []


def _hydrate_mapping_row(row) -> dict:
    data = dict(row)
    data["confidence_breakdown"] = _json_object(data.pop("confidence_breakdown_json", None))
    data["risk_flags"] = _json_list(data.pop("risk_flags_json", None))
    return data


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
        return [_hydrate_mapping_row(row) for row in cursor.fetchall()]


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
        return _hydrate_mapping_row(row) if row else None


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
    candidate_count = 0
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
            cursor.execute(
                f'''
                SELECT COUNT(*) AS count FROM actor_mappings
                WHERE emby_actor_id IN ({placeholders}) AND status = 'candidate'
                ''',
                ids,
            )
            candidate_count = cursor.fetchone()["count"]
        confirmed = sum(1 for aid in ids if by_actor.get(aid) == "confirmed")
        ignored = sum(1 for aid in ids if by_actor.get(aid) == "ignored")
    return {
        "total": total,
        "confirmed": confirmed,
        "ignored": ignored,
        "candidate": candidate_count,
        "unmapped": max(total - confirmed - ignored, 0),
        "coverage": (confirmed / total) if total else 0,
    }
