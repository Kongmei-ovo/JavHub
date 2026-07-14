"""PostgreSQL-backed AVDB release generations and synchronization state."""
from __future__ import annotations

import csv
import io
import json
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable, Iterator

from database.base import get_db_orig


# Stable signed bigint derived from ASCII ``JAVHUBAV``. A session advisory lock
# prevents two backend workers from importing the same release concurrently.
_AVDB_SYNC_LOCK_KEY = 0x4A41564855424156
logger = logging.getLogger(__name__)


def init_avdb_tables(cursor: Any) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS avdb_generations (
            generation_id TEXT PRIMARY KEY,
            release_id BIGINT NOT NULL,
            release_tag TEXT NOT NULL,
            release_published_at TIMESTAMPTZ NOT NULL,
            asset_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'staging',
            record_count BIGINT NOT NULL DEFAULT 0,
            source_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
            import_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            activated_at TIMESTAMPTZ,
            CHECK (status IN ('staging', 'active', 'retired'))
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS avdb_records (
            generation_id TEXT NOT NULL REFERENCES avdb_generations(generation_id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            source_tid TEXT NOT NULL,
            normalized_code TEXT,
            number TEXT,
            title TEXT NOT NULL,
            magnet TEXT NOT NULL,
            info_hash TEXT NOT NULL,
            size_text TEXT,
            publish_date TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS avdb_sync_state (
            id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            status TEXT NOT NULL DEFAULT 'never',
            active_generation TEXT REFERENCES avdb_generations(generation_id),
            current_release TEXT,
            current_release_id BIGINT,
            current_release_published_at TIMESTAMPTZ,
            asset_fingerprint TEXT,
            record_count BIGINT NOT NULL DEFAULT 0,
            source_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
            import_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
            release_etag TEXT,
            release_last_modified TEXT,
            last_checked_at TIMESTAMPTZ,
            last_started_at TIMESTAMPTZ,
            last_completed_at TIMESTAMPTZ,
            last_error TEXT,
            CHECK (status IN ('never', 'running', 'success', 'failed'))
        )
        """
    )
    cursor.execute(
        "ALTER TABLE avdb_generations ADD COLUMN IF NOT EXISTS release_published_at TIMESTAMPTZ"
    )
    cursor.execute(
        "UPDATE avdb_generations SET release_published_at = created_at WHERE release_published_at IS NULL"
    )
    cursor.execute(
        "ALTER TABLE avdb_generations ALTER COLUMN release_published_at SET NOT NULL"
    )
    cursor.execute(
        "ALTER TABLE avdb_generations ADD COLUMN IF NOT EXISTS asset_fingerprint TEXT"
    )
    cursor.execute(
        """
        UPDATE avdb_generations
        SET asset_fingerprint = 'legacy:' || generation_id
        WHERE asset_fingerprint IS NULL
        """
    )
    cursor.execute(
        "ALTER TABLE avdb_generations ALTER COLUMN asset_fingerprint SET NOT NULL"
    )
    cursor.execute(
        "ALTER TABLE avdb_generations ADD COLUMN IF NOT EXISTS import_stats JSONB NOT NULL DEFAULT '{}'::jsonb"
    )
    cursor.execute(
        "ALTER TABLE avdb_sync_state ADD COLUMN IF NOT EXISTS current_release_published_at TIMESTAMPTZ"
    )
    cursor.execute(
        "ALTER TABLE avdb_sync_state ADD COLUMN IF NOT EXISTS asset_fingerprint TEXT"
    )
    cursor.execute(
        """
        UPDATE avdb_sync_state state
        SET asset_fingerprint = generation.asset_fingerprint
        FROM avdb_generations generation
        WHERE state.active_generation = generation.generation_id
          AND state.asset_fingerprint IS NULL
        """
    )
    cursor.execute(
        "ALTER TABLE avdb_sync_state ADD COLUMN IF NOT EXISTS import_stats JSONB NOT NULL DEFAULT '{}'::jsonb"
    )
    cursor.execute("ALTER TABLE avdb_records ALTER COLUMN source_tid SET NOT NULL")
    cursor.execute("ALTER TABLE avdb_records ALTER COLUMN normalized_code DROP NOT NULL")
    cursor.execute(
        """
        INSERT INTO avdb_sync_state (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING
        """
    )


def _release_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def get_avdb_sync_state() -> dict[str, Any]:
    conn = get_db_orig()
    try:
        row = conn.execute(
            """
            SELECT status, active_generation, current_release, current_release_id,
                   asset_fingerprint, record_count, source_counts, import_stats,
                   release_etag, release_last_modified,
                   last_checked_at, last_started_at, last_completed_at, last_error
            FROM avdb_sync_state
            WHERE id = 1
            """
        ).fetchone()
        return _row_dict(row)
    finally:
        conn.close()


def get_avdb_status() -> dict[str, Any]:
    state = get_avdb_sync_state()
    source_counts = state.get("source_counts")
    if isinstance(source_counts, str):
        try:
            source_counts = json.loads(source_counts)
        except (TypeError, ValueError):
            source_counts = {}
    if not isinstance(source_counts, dict):
        source_counts = {}
    import_stats = state.get("import_stats")
    if isinstance(import_stats, str):
        try:
            import_stats = json.loads(import_stats)
        except (TypeError, ValueError):
            import_stats = {}
    if not isinstance(import_stats, dict):
        import_stats = {}
    count = int(state.get("record_count") or 0)
    generation = state.get("active_generation")
    return {
        "status": str(state.get("status") or "never"),
        "available": bool(generation and count > 0),
        "current_release": state.get("current_release"),
        "current_generation": generation,
        "asset_fingerprint": state.get("asset_fingerprint"),
        "record_count": count,
        "source_counts": {str(key): int(value or 0) for key, value in source_counts.items()},
        "import_stats": import_stats,
        "last_checked_at": state.get("last_checked_at"),
        "last_started_at": state.get("last_started_at"),
        "last_completed_at": state.get("last_completed_at"),
        "last_error": state.get("last_error"),
    }


def mark_avdb_sync_running() -> None:
    conn = get_db_orig()
    try:
        conn.execute(
            """
            UPDATE avdb_sync_state
            SET status = 'running',
                last_checked_at = CURRENT_TIMESTAMP,
                last_started_at = CURRENT_TIMESTAMP,
                last_error = NULL
            WHERE id = 1
            """
        )
        conn.commit()
    finally:
        conn.close()


def mark_avdb_sync_failed(error: str) -> None:
    conn = get_db_orig()
    try:
        conn.execute(
            """
            UPDATE avdb_sync_state
            SET status = 'failed',
                last_completed_at = CURRENT_TIMESTAMP,
                last_error = ?
            WHERE id = 1
            """,
            (str(error or "AVDB sync failed")[:2000],),
        )
        conn.commit()
    finally:
        conn.close()


def mark_avdb_sync_unchanged(*, etag: str | None, last_modified: str | None) -> None:
    conn = get_db_orig()
    try:
        conn.execute(
            """
            UPDATE avdb_sync_state
            SET status = 'success',
                release_etag = COALESCE(?, release_etag),
                release_last_modified = COALESCE(?, release_last_modified),
                last_checked_at = CURRENT_TIMESTAMP,
                last_completed_at = CURRENT_TIMESTAMP,
                last_error = NULL
            WHERE id = 1
            """,
            (etag, last_modified),
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def avdb_sync_advisory_lock() -> Iterator[bool]:
    """Hold a process-independent session lock for one complete sync attempt."""
    conn = get_db_orig()
    acquired = False
    try:
        row = conn.execute(
            "SELECT pg_try_advisory_lock(?) AS acquired",
            (_AVDB_SYNC_LOCK_KEY,),
        ).fetchone()
        acquired = bool(row and row["acquired"])
        conn.commit()
        yield acquired
    finally:
        if acquired:
            try:
                conn.execute("SELECT pg_advisory_unlock(?)", (_AVDB_SYNC_LOCK_KEY,))
                conn.commit()
            except Exception:
                conn.rollback()
        conn.close()


def recover_interrupted_avdb_sync() -> bool:
    """Mark an orphaned running state failed when no worker owns the sync lock."""
    with avdb_sync_advisory_lock() as acquired:
        if not acquired:
            return False
        conn = get_db_orig()
        try:
            cursor = conn.execute(
                """
                UPDATE avdb_sync_state
                SET status = 'failed',
                    last_completed_at = CURRENT_TIMESTAMP,
                    last_error = 'AVDB sync was interrupted by a backend restart'
                WHERE id = 1 AND status = 'running'
                """
            )
            changed = cursor.rowcount > 0
            conn.commit()
            return changed
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _insert_batch(cursor: Any, generation_id: str, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    for record in records:
        writer.writerow(
            [
                generation_id,
                record.get("source"),
                record.get("source_tid"),
                record.get("normalized_code"),
                record.get("number"),
                record.get("title"),
                record.get("magnet"),
                record.get("info_hash"),
                record.get("size_text"),
                record.get("publish_date"),
            ]
        )
    stream.seek(0)
    cursor.copy_expert(
        "COPY avdb_records (generation_id,source,source_tid,normalized_code,number,title,magnet,info_hash,size_text,publish_date) "
        "FROM STDIN WITH (FORMAT CSV)",
        stream,
    )


def replace_avdb_generation(
    *,
    release_id: int,
    release_tag: str,
    release_published_at: str,
    asset_fingerprint: str,
    etag: str | None,
    last_modified: str | None,
    assets: Iterable[tuple[str, Iterable[dict[str, Any]], dict[str, int]]],
    batch_size: int,
    keep_generations: int,
    min_source_records: int,
    min_searchable_records: int,
    min_source_ratio: float,
    max_skipped_ratio: float,
) -> dict[str, Any]:
    """Stream a full release into a staging generation, then atomically activate it."""
    generation_id = uuid.uuid4().hex
    source_counts: dict[str, int] = {}
    conn = get_db_orig()
    try:
        cursor = conn.cursor()
        current = cursor.execute(
            """
            SELECT current_release_id, current_release_published_at,
                   asset_fingerprint, source_counts, import_stats
            FROM avdb_sync_state
            WHERE id = 1
            FOR UPDATE
            """
        ).fetchone()
        current_release_id = int(current["current_release_id"] or 0) if current else 0
        current_fingerprint = str(current.get("asset_fingerprint") or "") if current else ""
        incoming_fingerprint = str(asset_fingerprint or "").strip()
        if not incoming_fingerprint:
            raise ValueError("AVDB asset fingerprint is required")
        if current_release_id and int(release_id) < current_release_id:
            raise ValueError(
                f"refusing stale AVDB release id {release_id}; active release id is {current_release_id}"
            )
        if (
            current_release_id
            and int(release_id) == current_release_id
            and current_fingerprint == incoming_fingerprint
        ):
            raise ValueError("refusing duplicate AVDB release asset fingerprint")
        current_published = _release_datetime(
            current.get("current_release_published_at") if current else None
        )
        incoming_published = _release_datetime(release_published_at)
        if incoming_published is None:
            raise ValueError("AVDB release published_at is invalid")
        if (
            current_release_id
            and int(release_id) > current_release_id
            and current_published is not None
            and incoming_published <= current_published
        ):
            raise ValueError(
                "refusing AVDB release whose published_at is not newer than the active generation"
            )
        cursor.execute(
            """
            INSERT INTO avdb_generations (
                generation_id, release_id, release_tag, release_published_at,
                asset_fingerprint, status
            )
            VALUES (?, ?, ?, ?::timestamptz, ?, 'staging')
            """,
            (
                generation_id,
                int(release_id),
                str(release_tag),
                str(release_published_at),
                incoming_fingerprint,
            ),
        )
        import_stats: dict[str, dict[str, int]] = {}
        for source, records, stats in assets:
            count = 0
            searchable = 0
            batch: list[dict[str, Any]] = []
            for record in records:
                if record.get("normalized_code"):
                    searchable += 1
                batch.append(record)
                if len(batch) >= batch_size:
                    _insert_batch(cursor, generation_id, batch)
                    count += len(batch)
                    batch.clear()
            if batch:
                _insert_batch(cursor, generation_id, batch)
                count += len(batch)
            expected = int(stats.get("expected") or 0)
            total = int(stats.get("total") or count)
            if expected <= 0 or total != expected:
                raise ValueError(
                    f"AVDB asset {source} row count {total} did not match filename count {expected}"
                )
            skipped = max(0, total - count)
            allowed_skipped_ratio = max(0.0, min(float(max_skipped_ratio), 0.5))
            if total and skipped / total > allowed_skipped_ratio:
                raise ValueError(
                    f"AVDB asset {source} skipped {skipped}/{total} records; "
                    f"maximum ratio is {allowed_skipped_ratio:.3f}"
                )
            if count < max(1, int(min_source_records)):
                raise ValueError(
                    f"AVDB asset {source} contained only {count} valid records; "
                    f"minimum is {min_source_records}"
                )
            if searchable < max(1, int(min_searchable_records)):
                raise ValueError(
                    f"AVDB asset {source} contained only {searchable} searchable records; "
                    f"minimum is {min_searchable_records}"
                )
            source_counts[source] = source_counts.get(source, 0) + count
            import_stats[source] = {
                "expected": expected,
                "total": total,
                "valid": count,
                "searchable": searchable,
                "skipped": skipped,
            }

        record_count = sum(source_counts.values())
        if record_count <= 0:
            raise ValueError("AVDB release contained no indexable records")
        old_source_counts = current.get("source_counts") if current else {}
        if isinstance(old_source_counts, str):
            try:
                old_source_counts = json.loads(old_source_counts)
            except (TypeError, ValueError):
                old_source_counts = {}
        if isinstance(old_source_counts, dict):
            ratio = max(0.0, min(float(min_source_ratio), 1.0))
            for source, new_count in source_counts.items():
                old_count = int(old_source_counts.get(source) or 0)
                if old_count and new_count < int(old_count * ratio):
                    raise ValueError(
                        f"AVDB asset {source} dropped from {old_count} to {new_count} records"
                    )
            old_import_stats = current.get("import_stats") if current else {}
            if isinstance(old_import_stats, str):
                try:
                    old_import_stats = json.loads(old_import_stats)
                except (TypeError, ValueError):
                    old_import_stats = {}
            if isinstance(old_import_stats, dict):
                for source, new_stats in import_stats.items():
                    old_stats = old_import_stats.get(source)
                    if not isinstance(old_stats, dict):
                        continue
                    old_searchable = int(old_stats.get("searchable") or 0)
                    new_searchable = int(new_stats.get("searchable") or 0)
                    if old_searchable and new_searchable < int(old_searchable * ratio):
                        raise ValueError(
                            f"AVDB asset {source} searchable records dropped from "
                            f"{old_searchable} to {new_searchable}"
                        )
        counts_json = json.dumps(source_counts, ensure_ascii=True, sort_keys=True)
        stats_json = json.dumps(import_stats, ensure_ascii=True, sort_keys=True)
        cursor.execute(
            "UPDATE avdb_generations SET status = 'retired' WHERE status = 'active'"
        )
        cursor.execute(
            """
            UPDATE avdb_generations
            SET status = 'active', record_count = ?, source_counts = ?::jsonb,
                import_stats = ?::jsonb,
                activated_at = CURRENT_TIMESTAMP
            WHERE generation_id = ?
            """,
            (record_count, counts_json, stats_json, generation_id),
        )
        cursor.execute(
            """
            UPDATE avdb_sync_state
            SET status = 'success', active_generation = ?, current_release = ?,
                current_release_id = ?, current_release_published_at = ?::timestamptz,
                asset_fingerprint = ?, record_count = ?,
                source_counts = ?::jsonb, import_stats = ?::jsonb,
                release_etag = ?, release_last_modified = ?,
                last_checked_at = CURRENT_TIMESTAMP,
                last_completed_at = CURRENT_TIMESTAMP, last_error = NULL
            WHERE id = 1
            """,
            (
                generation_id,
                str(release_tag),
                int(release_id),
                str(release_published_at),
                incoming_fingerprint,
                record_count,
                counts_json,
                stats_json,
                etag,
                last_modified,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _cleanup_old_generations(keep_generations=max(1, int(keep_generations)))
    return {
        "generation_id": generation_id,
        "release": str(release_tag),
        "record_count": record_count,
        "source_counts": source_counts,
        "import_stats": import_stats,
    }


def _cleanup_old_generations(*, keep_generations: int) -> None:
    keep_retired = max(0, keep_generations - 1)
    conn = get_db_orig()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT generation_id
            FROM avdb_generations
            WHERE status = 'retired'
            ORDER BY activated_at DESC NULLS LAST, created_at DESC
            OFFSET ?
            """,
            (keep_retired,),
        )
        stale = [str(row["generation_id"]) for row in cursor.fetchall()]
        for generation_id in stale:
            cursor.execute(
                "DELETE FROM avdb_generations WHERE generation_id = ? AND status = 'retired'",
                (generation_id,),
            )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        # Cleanup is best-effort and must never turn an activated release into a
        # reported sync failure.
        logger.warning("Failed to clean up retired AVDB generations: %s", exc)
    finally:
        conn.close()


def search_avdb_records(normalized_code: str, *, limit: int) -> list[dict[str, Any]]:
    conn = get_db_orig()
    try:
        cursor = conn.execute(
            """
            SELECT source, source_tid, normalized_code, number, title, magnet,
                   info_hash, size_text, publish_date
            FROM (
                SELECT DISTINCT ON (records.info_hash)
                       records.source, records.source_tid, records.normalized_code,
                       records.number, records.title, records.magnet,
                       records.info_hash, records.size_text, records.publish_date
                FROM avdb_sync_state state
                JOIN avdb_records records
                  ON records.generation_id = state.active_generation
                WHERE state.id = 1 AND records.normalized_code = ?
                ORDER BY records.info_hash, records.publish_date DESC NULLS LAST
            ) deduplicated
            ORDER BY publish_date DESC NULLS LAST, title
            LIMIT ?
            """,
            (normalized_code, max(1, min(int(limit), 200))),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
