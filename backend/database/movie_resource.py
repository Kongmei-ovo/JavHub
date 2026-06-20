"""Durable playback resource references keyed by JavHub movie ItemId."""
from __future__ import annotations

import time
from typing import Any

from database.base import get_db

VALID_RESOURCE_STATUSES = {"pending", "ready", "missing", "failed"}
VALID_RESOURCE_TYPES = {"video", "subtitle"}


def _bump_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("movie_resources", time.time_ns())
    except Exception:
        pass


def _normalized_extension(extension: str | None, name: str) -> str:
    value = str(extension or "").strip().lower().lstrip(".")
    if not value and "." in name:
        value = name.rsplit(".", 1)[-1].lower()
    return value


def _validated_values(
    *,
    movie_id: str,
    provider: str,
    remote_file_id: str,
    name: str,
    status: str,
    resource_type: str,
) -> tuple[str, str, str, str, str, str]:
    values = (
        str(movie_id or "").strip(),
        str(provider or "").strip().lower(),
        str(remote_file_id or "").strip(),
        str(name or "").strip(),
        str(status or "").strip().lower(),
        str(resource_type or "").strip().lower(),
    )
    if not all(values[:4]):
        raise ValueError("movie_id, provider, remote_file_id and name are required")
    if values[4] not in VALID_RESOURCE_STATUSES:
        raise ValueError(f"invalid resource status: {values[4]}")
    if values[5] not in VALID_RESOURCE_TYPES:
        raise ValueError(f"invalid resource type: {values[5]}")
    return values


def upsert_movie_resource(
    *,
    movie_id: str,
    provider: str,
    remote_file_id: str,
    name: str,
    parent_id: str | None = None,
    pick_code: str | None = None,
    extension: str | None = None,
    size: int = 0,
    duration: int = 0,
    resource_type: str = "video",
    status: str = "pending",
    is_default: bool = False,
    download_task_id: int | None = None,
    related_resource_id: int | None = None,
    version_label: str | None = None,
    part_index: int | None = None,
    group_key: str | None = None,
) -> tuple[int, bool]:
    movie_id, provider, remote_file_id, name, status, resource_type = _validated_values(
        movie_id=movie_id,
        provider=provider,
        remote_file_id=remote_file_id,
        name=name,
        status=status,
        resource_type=resource_type,
    )
    can_be_default = bool(is_default and resource_type == "video" and status == "ready")
    normalized_extension = _normalized_extension(extension, name)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM movie_resources WHERE provider = ? AND remote_file_id = ?",
            (provider, remote_file_id),
        )
        existing = cursor.fetchone()
        if can_be_default:
            cursor.execute(
                """
                UPDATE movie_resources
                SET is_default = 0, updated_at = CURRENT_TIMESTAMP
                WHERE movie_id = ? AND provider = ? AND resource_type = 'video'
                """,
                (movie_id, provider),
            )
        if existing is None:
            cursor.execute(
                """
                INSERT INTO movie_resources (
                    movie_id, provider, remote_file_id, parent_id, pick_code,
                    name, extension, size, duration, resource_type, status,
                    is_default, download_task_id, related_resource_id,
                    version_label, part_index, group_key,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    movie_id,
                    provider,
                    remote_file_id,
                    str(parent_id or ""),
                    str(pick_code or ""),
                    name,
                    normalized_extension,
                    max(0, int(size or 0)),
                    max(0, int(duration or 0)),
                    resource_type,
                    status,
                    can_be_default,
                    download_task_id,
                    related_resource_id,
                    str(version_label or ""),
                    int(part_index) if part_index is not None else None,
                    str(group_key or ""),
                ),
            )
            resource_id = int(cursor.lastrowid)
            created = True
        else:
            resource_id = int(existing["id"])
            cursor.execute(
                """
                UPDATE movie_resources
                SET movie_id = ?, parent_id = ?, pick_code = ?, name = ?,
                    extension = ?, size = ?, duration = ?, resource_type = ?,
                    status = ?, is_default = ?, download_task_id = ?,
                    related_resource_id = ?, version_label = ?, part_index = ?,
                    group_key = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    movie_id,
                    str(parent_id or ""),
                    str(pick_code or ""),
                    name,
                    normalized_extension,
                    max(0, int(size or 0)),
                    max(0, int(duration or 0)),
                    resource_type,
                    status,
                    can_be_default,
                    download_task_id,
                    related_resource_id,
                    str(version_label or ""),
                    int(part_index) if part_index is not None else None,
                    str(group_key or ""),
                    resource_id,
                ),
            )
            created = False
        _bump_generation()
        return resource_id, created


def code_has_ready_resource(code: str) -> bool:
    movie_id = str(code or "").strip()
    if not movie_id:
        return False
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1 FROM movie_resources
            WHERE movie_id = ? AND resource_type = 'video' AND status = 'ready'
            LIMIT 1
            """,
            (movie_id,),
        )
        return cursor.fetchone() is not None


def list_ready_video_movie_ids() -> list[str]:
    """All movie_ids with a ready video resource. Scans only the sparse resource
    library (never the 1.8M metadata set) — intended for migration/parity tools."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT movie_id FROM movie_resources
            WHERE resource_type = 'video' AND status = 'ready'
            """
        )
        return [str(row["movie_id"]) for row in cursor.fetchall()]


def codes_with_ready_resource(codes: list[str]) -> set[str]:
    movie_ids = list(dict.fromkeys(str(code or "").strip() for code in codes))
    movie_ids = [movie_id for movie_id in movie_ids if movie_id]
    if not movie_ids:
        return set()
    ready_movie_ids: set[str] = set()
    with get_db() as conn:
        cursor = conn.cursor()
        for offset in range(0, len(movie_ids), 500):
            batch = movie_ids[offset : offset + 500]
            placeholders = ", ".join("?" for _ in batch)
            cursor.execute(
                f"""
                SELECT DISTINCT movie_id FROM movie_resources
                WHERE movie_id IN ({placeholders})
                  AND resource_type = 'video' AND status = 'ready'
                """,
                tuple(batch),
            )
            ready_movie_ids.update(str(row["movie_id"]) for row in cursor.fetchall())
    return ready_movie_ids


def get_movie_resource(resource_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movie_resources WHERE id = ?", (resource_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_movie_resource_by_remote_id(provider: str, remote_file_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM movie_resources WHERE provider = ? AND remote_file_id = ?",
            (str(provider).lower(), str(remote_file_id)),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_movie_resources(movie_id: str) -> list[dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM movie_resources
            WHERE movie_id = ?
            ORDER BY
                CASE WHEN resource_type = 'video' THEN 0 ELSE 1 END,
                is_default DESC,
                CASE status WHEN 'ready' THEN 0 WHEN 'pending' THEN 1
                            WHEN 'missing' THEN 2 ELSE 3 END,
                part_index ASC NULLS FIRST,
                id ASC
            """,
            (str(movie_id),),
        )
        return [dict(row) for row in cursor.fetchall()]


def list_ready_movie_videos(movie_id: str) -> list[dict[str, Any]]:
    return [
        row
        for row in list_movie_resources(movie_id)
        if row["resource_type"] == "video" and row["status"] == "ready"
    ]


def set_default_movie_resource(movie_id: str, resource_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, provider FROM movie_resources
            WHERE id = ? AND movie_id = ? AND resource_type = 'video' AND status = 'ready'
            """,
            (resource_id, str(movie_id)),
        )
        target = cursor.fetchone()
        if target is None:
            return False
        cursor.execute(
            """
            UPDATE movie_resources
            SET is_default = 0, updated_at = CURRENT_TIMESTAMP
            WHERE movie_id = ? AND provider = ? AND resource_type = 'video'
            """,
            (str(movie_id), target["provider"]),
        )
        cursor.execute(
            "UPDATE movie_resources SET is_default = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (resource_id,),
        )
        _bump_generation()
        return True


def set_movie_resource_status(resource_id: int, status: str) -> bool:
    normalized = str(status or "").strip().lower()
    if normalized not in VALID_RESOURCE_STATUSES:
        raise ValueError(f"invalid resource status: {normalized}")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE movie_resources
            SET status = ?,
                is_default = CASE WHEN ? = 'ready' THEN is_default ELSE 0 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (normalized, normalized, resource_id),
        )
        changed = cursor.rowcount > 0
        if changed:
            _bump_generation()
        return changed


def delete_movie_resource(movie_id: str, resource_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT provider, pick_code, remote_file_id, is_default, parent_id
            FROM movie_resources
            WHERE id = ? AND movie_id = ?
            """,
            (resource_id, str(movie_id)),
        )
        target = cursor.fetchone()
        if target is None:
            return None
        cursor.execute(
            "UPDATE movie_resources SET related_resource_id = NULL WHERE related_resource_id = ?",
            (resource_id,),
        )
        cursor.execute(
            "DELETE FROM movie_resources WHERE id = ? AND movie_id = ?",
            (resource_id, str(movie_id)),
        )
        if bool(target["is_default"]):
            cursor.execute(
                """
                SELECT id FROM movie_resources
                WHERE movie_id = ? AND provider = ?
                  AND resource_type = 'video' AND status = 'ready'
                ORDER BY is_default DESC, part_index ASC NULLS FIRST, id ASC
                LIMIT 1
                """,
                (str(movie_id), target["provider"]),
            )
            replacement = cursor.fetchone()
            if replacement:
                cursor.execute(
                    """
                    UPDATE movie_resources
                    SET is_default = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (replacement["id"],),
                )
        _bump_generation()
        return dict(target)


def delete_all_movie_resources(movie_id: str) -> list[dict[str, Any]]:
    """Purge every resource row for a movie (used by whole-folder delete).

    Returns the deleted rows so the caller can clean up their 115 files. Does
    not touch 115 itself — that is the service layer's job.
    """
    movie_id = str(movie_id or "").strip()
    if not movie_id:
        return []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, provider, pick_code, remote_file_id, parent_id, resource_type
            FROM movie_resources WHERE movie_id = ?
            """,
            (movie_id,),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        if not rows:
            return []
        cursor.execute(
            "UPDATE movie_resources SET related_resource_id = NULL WHERE movie_id = ?",
            (movie_id,),
        )
        cursor.execute("DELETE FROM movie_resources WHERE movie_id = ?", (movie_id,))
        _bump_generation()
        return rows
