from __future__ import annotations

"""翻译映射数据库层"""
import json
import hashlib
from datetime import datetime
from typing import Optional
from database.base import get_db

# 允许的列名（防 SQL 注入）
_VALID_TYPES = {"actress", "category", "series", "title", "maker", "label"}
_METADATA_TYPES = {"actress", "category", "series", "maker", "label"}
_WORKBENCH_STATUSES = {"untranslated", "machine_translated", "reviewed", "manual_edited", "failed", "invalid"}

# 允许的列名（防 SQL 注入）
_VALID_COLUMNS = {"actress_json", "category_json", "series_json", "title_json", "maker_json", "label_json"}

# 内存缓存：避免同一请求周期内重复查询同一 translation
_translation_cache: dict[str, Optional[dict]] = {}


def _cache_key(content_id: str) -> str:
    return content_id


def _json_mapping(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _valid_mapping(mapping: object) -> dict:
    if not isinstance(mapping, dict):
        return {}
    return {k: v for k, v in mapping.items() if k and v}


def init_translation_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_mappings (
                content_id TEXT PRIMARY KEY,
                actress_json TEXT DEFAULT '{}',
                category_json TEXT DEFAULT '{}',
                series_json TEXT DEFAULT '{}',
                title_json TEXT DEFAULT '{}',
                maker_json TEXT DEFAULT '{}',
                label_json TEXT DEFAULT '{}',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        for column in ("maker_json", "label_json"):
            try:
                cursor.execute(f"ALTER TABLE translation_mappings ADD COLUMN {column} TEXT DEFAULT '{{}}'")
            except Exception:
                pass
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                source_text_hash TEXT NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                status TEXT DEFAULT 'completed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(scope, source_text_hash)
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_translation_cache_scope
            ON translation_cache(scope, updated_at DESC)
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                scope TEXT DEFAULT 'library',
                provider_order_json TEXT DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                total INTEGER DEFAULT 0,
                processed INTEGER DEFAULT 0,
                translated INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                error_msg TEXT,
                result_json TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        ''')
        for column in ("started_at", "finished_at"):
            try:
                cursor.execute(f"ALTER TABLE translation_jobs ADD COLUMN {column} TEXT")
            except Exception:
                pass
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_translation_jobs_created
            ON translation_jobs(created_at DESC)
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_workbench_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                source_text_hash TEXT NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT DEFAULT '',
                status TEXT DEFAULT 'untranslated',
                provider TEXT,
                model TEXT,
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                source_page INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_type, item_id)
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_translation_workbench_type_status
            ON translation_workbench_items(item_type, status, updated_at DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_translation_workbench_updated
            ON translation_workbench_items(updated_at DESC)
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_workbench_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                source_text TEXT NOT NULL,
                old_text TEXT,
                new_text TEXT,
                action TEXT NOT NULL,
                operator TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_translation_workbench_history_item
            ON translation_workbench_history(item_type, item_id, created_at DESC)
        ''')
    _translation_cache.clear()


def _get_raw(content_id: str) -> Optional[dict]:
    key = _cache_key(content_id)
    if key in _translation_cache:
        return _translation_cache[key]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT actress_json, category_json, series_json, title_json, maker_json, label_json FROM translation_mappings WHERE content_id = ?",
            (content_id,)
        )
        row = cursor.fetchone()
        if not row:
            _translation_cache[key] = None
            return None
        result = {
            "actress": _json_mapping(row["actress_json"]),
            "category": _json_mapping(row["category_json"]),
            "series": _json_mapping(row["series_json"]),
            "title": _json_mapping(row["title_json"]),
            "maker": _json_mapping(row["maker_json"]),
            "label": _json_mapping(row["label_json"]),
        }
        _translation_cache[key] = result
        return result


def get_translation(content_id: str) -> Optional[dict]:
    result = _get_raw(content_id)
    if result:
        return result
    for prefix in ("_global:actress:", "_global:category:", "_global:series:", "_global:maker:", "_global:label:"):
        result = _get_raw(prefix + content_id)
        if result:
            return result
    return None


def upsert_translation(content_id: str, mapping: dict) -> bool:
    existing = _get_raw(content_id)
    title_mapping = _valid_mapping(mapping.get("title"))
    _translation_cache.pop(_cache_key(content_id), None)  # 写入前清除缓存
    with get_db() as conn:
        cursor = conn.cursor()
        if existing:
            merged = {
                "actress": {**existing.get("actress", {}), **mapping.get("actress", {})},
                "category": {**existing.get("category", {}), **mapping.get("category", {})},
                "series": {**existing.get("series", {}), **mapping.get("series", {})},
                "maker": {**existing.get("maker", {}), **mapping.get("maker", {})},
                "label": {**existing.get("label", {}), **mapping.get("label", {})},
                "title": title_mapping or _valid_mapping(existing.get("title")),
            }
        else:
            merged = {
                "actress": mapping.get("actress", {}),
                "category": mapping.get("category", {}),
                "series": mapping.get("series", {}),
                "maker": mapping.get("maker", {}),
                "label": mapping.get("label", {}),
                "title": title_mapping,
            }
        cursor.execute('''
            INSERT INTO translation_mappings (
                content_id, actress_json, category_json, series_json, title_json, maker_json, label_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO UPDATE SET
                actress_json = excluded.actress_json,
                category_json = excluded.category_json,
                series_json = excluded.series_json,
                title_json = excluded.title_json,
                maker_json = excluded.maker_json,
                label_json = excluded.label_json,
                updated_at = CURRENT_TIMESTAMP
        ''', (content_id, json.dumps(merged["actress"], ensure_ascii=False),
              json.dumps(merged["category"], ensure_ascii=False),
              json.dumps(merged["series"], ensure_ascii=False),
              json.dumps(merged["title"], ensure_ascii=False),
              json.dumps(merged["maker"], ensure_ascii=False),
              json.dumps(merged["label"], ensure_ascii=False)))
    return True


def bulk_upsert_title_translations(entries: list[tuple[str, str, str]]) -> int:
    rows = [
        (_normalize_title_id(content_id), source_text, translated_text)
        for content_id, source_text, translated_text in entries
        if content_id and source_text and translated_text
    ]
    if not rows:
        return 0
    content_ids = [row[0] for row in rows]
    existing: dict[str, dict] = {}
    with get_db() as conn:
        cursor = conn.cursor()
        for start in range(0, len(content_ids), 500):
            chunk = content_ids[start:start + 500]
            placeholders = ",".join("?" for _ in chunk)
            cursor.execute(
                f"SELECT content_id, title_json FROM translation_mappings WHERE content_id IN ({placeholders})",
                chunk,
            )
            for row in cursor.fetchall():
                existing[str(row["content_id"])] = _valid_mapping(_json_mapping(row["title_json"]))

        payload = []
        for content_id, source_text, translated_text in rows:
            title_mapping = {**existing.get(content_id, {}), source_text: translated_text}
            _translation_cache.pop(_cache_key(content_id), None)
            payload.append((content_id, json.dumps(title_mapping, ensure_ascii=False)))

        cursor.executemany(
            '''
            INSERT INTO translation_mappings (content_id, title_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO UPDATE SET
                title_json = excluded.title_json,
                updated_at = CURRENT_TIMESTAMP
            ''',
            payload,
        )
    return len(payload)


def bulk_upsert_metadata_translations(entries: list[tuple[str, str, str, str]]) -> int:
    rows = [
        (entity_type, str(entity_id), source_text, translated_text)
        for entity_type, entity_id, source_text, translated_text in entries
        if entity_type in ("actress", "category", "series", "maker", "label")
        and entity_id
        and source_text
        and translated_text
    ]
    if not rows:
        return 0
    by_type: dict[str, list[tuple[str, str, str, str]]] = {}
    for row in rows:
        by_type.setdefault(row[0], []).append(row)

    written = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for entity_type, type_rows in by_type.items():
            col = f"{entity_type}_json"
            content_ids = [f"{entity_type}:{entity_id}" for _, entity_id, _, _ in type_rows]
            existing: dict[str, dict] = {}
            for start in range(0, len(content_ids), 500):
                chunk = content_ids[start:start + 500]
                placeholders = ",".join("?" for _ in chunk)
                cursor.execute(
                    f"SELECT content_id, {col} FROM translation_mappings WHERE content_id IN ({placeholders})",
                    chunk,
                )
                for row in cursor.fetchall():
                    existing[str(row["content_id"])] = _valid_mapping(_json_mapping(row[col]))

            payload = []
            for _, entity_id, source_text, translated_text in type_rows:
                content_id = f"{entity_type}:{entity_id}"
                mapping = {**existing.get(content_id, {}), source_text: translated_text}
                _translation_cache.pop(_cache_key(content_id), None)
                payload.append((content_id, json.dumps(mapping, ensure_ascii=False)))

            cursor.executemany(
                f'''
                INSERT INTO translation_mappings (content_id, {col}, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(content_id) DO UPDATE SET
                    {col} = excluded.{col},
                    updated_at = CURRENT_TIMESTAMP
                ''',
                payload,
            )
            written += len(payload)
    return written


def get_all_translations(mapping_type: str) -> dict:
    field_map = {"actress": "actress_json", "category": "category_json",
                 "series": "series_json", "maker": "maker_json",
                 "label": "label_json", "title": "title_json"}
    field = field_map.get(mapping_type)
    if not field or field not in _VALID_COLUMNS:
        return {}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT content_id, {field} FROM translation_mappings")
        rows = cursor.fetchall()
        result = {}
        for row in rows:
            parsed = _json_mapping(row[field])
            if mapping_type == "title":
                valid_title = _valid_mapping(parsed)
                if valid_title:
                    result[row["content_id"]] = valid_title
            else:
                cid = row["content_id"]
                if cid.startswith("_global:"):
                    for k, v in parsed.items():
                        if k and v:
                            result[k] = v
        return result


def import_translations(mapping_type: str, data: dict) -> int:
    if mapping_type not in ("actress", "category", "series", "maker", "label", "title"):
        return 0
    count = 0
    if mapping_type == "title":
        for cid, trans in data.items():
            upsert_translation(cid, {"title": trans})
            count += 1
    else:
        for orig_name, trans_name in data.items():
            global_key = f"_global:{mapping_type}:{orig_name}"
            upsert_translation(global_key, {mapping_type: {orig_name: trans_name}})
            count += 1
    return count


def get_translation_count(mapping_type: str) -> int:
    if mapping_type not in ("actress", "category", "series", "maker", "label", "title"):
        return 0
    with get_db() as conn:
        cursor = conn.cursor()
        if mapping_type == "actress":
            cursor.execute("SELECT actress_json FROM translation_mappings WHERE content_id LIKE 'actress:%'")
            rows = cursor.fetchall()
            return sum(len(_valid_mapping(_json_mapping(row["actress_json"]))) for row in rows)
        elif mapping_type in ("category", "series", "maker", "label"):
            col = f"{mapping_type}_json"
            if col not in _VALID_COLUMNS:
                return 0
            cursor.execute(
                f"SELECT {col} FROM translation_mappings WHERE content_id LIKE ?",
                (f"{mapping_type}:%",),
            )
            rows = cursor.fetchall()
            return sum(len(_valid_mapping(_json_mapping(row[col]))) for row in rows)
        else:
            cursor.execute(
                "SELECT title_json FROM translation_mappings WHERE content_id NOT LIKE '_global:%'"
            )
            rows = cursor.fetchall()
            return sum(1 for row in rows if _valid_mapping(_json_mapping(row["title_json"])))


def _title_id_from_scope(scope: str) -> str:
    if not scope.startswith("title:"):
        return ""
    suffix_idx = scope.rfind(":title_")
    if suffix_idx <= len("title:"):
        return ""
    return _normalize_title_id(scope[len("title:"):suffix_idx])


def _normalize_title_id(value: str) -> str:
    return str(value or "").replace("-", "").replace("_", "").lower()


def _entity_id_from_scope(scope: str, mapping_type: str) -> str:
    prefix = f"{mapping_type}:"
    if not scope.startswith(prefix):
        return ""
    entity_id = scope[len(prefix):].strip()
    return entity_id if entity_id and ":" not in entity_id else ""


def get_translation_coverage_counts(mapping_type: str) -> dict:
    """Return de-duplicated local coverage from formal mappings and realtime cache."""
    if mapping_type not in ("actress", "category", "series", "maker", "label", "title"):
        return {"mapped": 0, "cached": 0, "translated": 0}

    mapped_ids: set[str] = set()
    cached_ids: set[str] = set()

    with get_db() as conn:
        cursor = conn.cursor()
        if mapping_type == "title":
            cursor.execute(
                "SELECT content_id, title_json FROM translation_mappings WHERE content_id NOT LIKE '_global:%'"
            )
            for row in cursor.fetchall():
                if _valid_mapping(_json_mapping(row["title_json"])):
                    mapped_ids.add(_normalize_title_id(str(row["content_id"])))

            cursor.execute(
                "SELECT scope FROM translation_cache WHERE status = 'completed' AND scope LIKE 'title:%:title_%'"
            )
            for row in cursor.fetchall():
                content_id = _title_id_from_scope(str(row["scope"] or ""))
                if content_id:
                    cached_ids.add(content_id)
        else:
            col = f"{mapping_type}_json"
            if col not in _VALID_COLUMNS:
                return {"mapped": 0, "cached": 0, "translated": 0}
            cursor.execute(
                f"SELECT content_id, {col} FROM translation_mappings WHERE content_id LIKE ?",
                (f"{mapping_type}:%",),
            )
            prefix = f"{mapping_type}:"
            for row in cursor.fetchall():
                if _valid_mapping(_json_mapping(row[col])):
                    mapped_ids.add(str(row["content_id"])[len(prefix):])

            cursor.execute(
                "SELECT scope FROM translation_cache WHERE status = 'completed' AND scope LIKE ?",
                (f"{mapping_type}:%",),
            )
            for row in cursor.fetchall():
                entity_id = _entity_id_from_scope(str(row["scope"] or ""), mapping_type)
                if entity_id:
                    cached_ids.add(entity_id)

    return {
        "mapped": len(mapped_ids),
        "cached": len(cached_ids),
        "translated": len(mapped_ids),
    }


def translation_text_hash(source_text: str) -> str:
    return hashlib.sha256((source_text or "").encode("utf-8")).hexdigest()


def get_cached_translation(scope: str, source_text: str) -> Optional[dict]:
    if not scope or not source_text:
        return None
    digest = translation_text_hash(source_text)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT scope, source_text_hash, source_text, translated_text, provider, model, status, updated_at
            FROM translation_cache
            WHERE scope = ? AND source_text_hash = ? AND status = 'completed'
            ''',
            (scope, digest),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def upsert_cached_translation(
    scope: str,
    source_text: str,
    translated_text: str,
    provider: str,
    model: str | None = None,
    status: str = "completed",
) -> bool:
    if not scope or not source_text or not translated_text:
        return False
    digest = translation_text_hash(source_text)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO translation_cache (
                scope, source_text_hash, source_text, translated_text, provider, model, status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(scope, source_text_hash) DO UPDATE SET
                source_text = excluded.source_text,
                translated_text = excluded.translated_text,
                provider = excluded.provider,
                model = excluded.model,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            ''',
            (scope, digest, source_text, translated_text, provider, model, status),
        )
    return True


def bulk_upsert_cached_translations(entries: list[tuple[str, str, str, str, str | None]]) -> int:
    rows = [
        (scope, translation_text_hash(source_text), source_text, translated_text, provider, model)
        for scope, source_text, translated_text, provider, model in entries
        if scope and source_text and translated_text and provider
    ]
    if not rows:
        return 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            '''
            INSERT INTO translation_cache (
                scope, source_text_hash, source_text, translated_text, provider, model, status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
            ON CONFLICT(scope, source_text_hash) DO UPDATE SET
                source_text = excluded.source_text,
                translated_text = excluded.translated_text,
                provider = excluded.provider,
                model = excluded.model,
                status = 'completed',
                updated_at = CURRENT_TIMESTAMP
            ''',
            rows,
        )
    return len(rows)


def get_translation_cache_count(status: str | None = "completed") -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT COUNT(*) FROM translation_cache WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM translation_cache")
        return cursor.fetchone()[0]


def _valid_workbench_type(item_type: str) -> bool:
    return item_type in _VALID_TYPES


def _valid_workbench_status(status: str | None) -> bool:
    return not status or status in _WORKBENCH_STATUSES


def _normalize_workbench_item_id(item_type: str, item_id: object) -> str:
    if item_type == "title":
        return _normalize_title_id(str(item_id or ""))
    return str(item_id or "").strip()


def _workbench_scope(item_type: str, item_id: str, source_text: str) -> str:
    if item_type == "title":
        return f"title:{item_id}:title_ja"
    return f"{item_type}:{item_id}"


def _row_to_workbench_item(row) -> dict:
    data = dict(row)
    data["row_id"] = data.pop("id", None)
    return data


def _formal_mapping_text(item_type: str, item_id: str, source_text: str) -> str:
    if not _valid_workbench_type(item_type):
        return ""
    content_id = item_id if item_type == "title" else f"{item_type}:{item_id}"
    raw = _get_raw(content_id)
    mapping = raw.get(item_type, {}) if raw else {}
    value = mapping.get(source_text) if isinstance(mapping, dict) else ""
    return str(value or "")


def _remove_formal_mapping_text(item_type: str, item_id: str, source_text: str) -> None:
    if not _valid_workbench_type(item_type) or not item_id or not source_text:
        return
    content_id = item_id if item_type == "title" else f"{item_type}:{item_id}"
    col = f"{item_type}_json"
    if col not in _VALID_COLUMNS:
        return
    _translation_cache.pop(_cache_key(content_id), None)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {col} FROM translation_mappings WHERE content_id = ?", (content_id,))
        row = cursor.fetchone()
        if not row:
            return
        mapping = _valid_mapping(_json_mapping(row[col]))
        mapping.pop(source_text, None)
        cursor.execute(
            f"UPDATE translation_mappings SET {col} = ?, updated_at = CURRENT_TIMESTAMP WHERE content_id = ?",
            (json.dumps(mapping, ensure_ascii=False), content_id),
        )


def upsert_translation_workbench_item(
    item_type: str,
    item_id: object,
    source_text: str,
    *,
    translated_text: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    attempts: int | None = None,
    last_error: str | None = None,
    source_page: int | None = None,
    scope: str | None = None,
    preserve_reviewed: bool = True,
) -> dict | None:
    if not _valid_workbench_type(item_type) or not source_text or not _valid_workbench_status(status):
        return None
    normalized_id = _normalize_workbench_item_id(item_type, item_id)
    if not normalized_id:
        return None
    translated = "" if translated_text is None else str(translated_text)
    next_status = status or ("machine_translated" if translated else "untranslated")
    resolved_scope = scope or _workbench_scope(item_type, normalized_id, source_text)
    digest = translation_text_hash(source_text)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT status, translated_text, attempts
            FROM translation_workbench_items
            WHERE item_type = ? AND item_id = ?
            ''',
            (item_type, normalized_id),
        )
        existing = cursor.fetchone()
        attempt_count = attempts if attempts is not None else (int(existing["attempts"] or 0) if existing else 0)
        if existing and preserve_reviewed and existing["status"] in {"reviewed", "manual_edited"} and next_status in {"untranslated", "machine_translated"}:
            next_status = existing["status"]
            if not translated:
                translated = str(existing["translated_text"] or "")
        cursor.execute(
            '''
            INSERT INTO translation_workbench_items (
                item_type, item_id, scope, source_text_hash, source_text, translated_text,
                status, provider, model, attempts, last_error, source_page, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(item_type, item_id) DO UPDATE SET
                scope = excluded.scope,
                source_text_hash = excluded.source_text_hash,
                source_text = excluded.source_text,
                translated_text = excluded.translated_text,
                status = excluded.status,
                provider = excluded.provider,
                model = excluded.model,
                attempts = COALESCE(excluded.attempts, translation_workbench_items.attempts),
                last_error = excluded.last_error,
                source_page = COALESCE(excluded.source_page, translation_workbench_items.source_page),
                updated_at = CURRENT_TIMESTAMP
            ''',
            (
                item_type,
                normalized_id,
                resolved_scope,
                digest,
                source_text,
                translated,
                next_status,
                provider,
                model,
                attempt_count,
                last_error,
                source_page,
            ),
        )
    return get_translation_workbench_item(item_type, normalized_id)


def bulk_upsert_translation_workbench_items(entries: list[dict], *, preserve_reviewed: bool = True) -> int:
    normalized: list[dict] = []
    for entry in entries:
        item_type = str(entry.get("item_type") or entry.get("type") or "")
        item_id = _normalize_workbench_item_id(
            item_type,
            entry.get("item_id") if entry.get("item_id") is not None else entry.get("id"),
        )
        source_text = str(entry.get("source_text") or entry.get("source") or "")
        status = entry.get("status")
        if not _valid_workbench_type(item_type) or not item_id or not source_text or not _valid_workbench_status(status):
            continue
        translated = "" if entry.get("translated_text") is None else str(entry.get("translated_text"))
        normalized.append({
            "item_type": item_type,
            "item_id": item_id,
            "source_text": source_text,
            "translated_text": translated,
            "status": status or ("machine_translated" if translated else "untranslated"),
            "provider": entry.get("provider"),
            "model": entry.get("model"),
            "attempts": entry.get("attempts"),
            "last_error": entry.get("last_error"),
            "source_page": entry.get("source_page"),
            "scope": str(entry.get("scope") or _workbench_scope(item_type, item_id, source_text)),
        })
    if not normalized:
        return 0

    existing: dict[tuple[str, str], dict] = {}
    with get_db() as conn:
        cursor = conn.cursor()
        by_type: dict[str, list[str]] = {}
        for item in normalized:
            by_type.setdefault(item["item_type"], []).append(item["item_id"])
        for item_type, ids in by_type.items():
            seen_ids = list(dict.fromkeys(ids))
            for start in range(0, len(seen_ids), 500):
                chunk = seen_ids[start:start + 500]
                placeholders = ",".join("?" for _ in chunk)
                cursor.execute(
                    f'''
                    SELECT item_type, item_id, status, translated_text, attempts
                    FROM translation_workbench_items
                    WHERE item_type = ? AND item_id IN ({placeholders})
                    ''',
                    [item_type, *chunk],
                )
                for row in cursor.fetchall():
                    existing[(str(row["item_type"]), str(row["item_id"]))] = {
                        "status": row["status"],
                        "translated_text": row["translated_text"],
                        "attempts": row["attempts"],
                    }

        payload = []
        for item in normalized:
            existing_item = existing.get((item["item_type"], item["item_id"]))
            translated = item["translated_text"]
            next_status = item["status"]
            if (
                existing_item
                and preserve_reviewed
                and existing_item.get("status") in {"reviewed", "manual_edited"}
                and next_status in {"untranslated", "machine_translated"}
            ):
                next_status = str(existing_item.get("status") or next_status)
                translated = str(existing_item.get("translated_text") or "") or translated
            if item["attempts"] is not None:
                try:
                    attempt_count = int(item["attempts"])
                except Exception:
                    attempt_count = 0
            else:
                attempt_count = int(existing_item.get("attempts") or 0) if existing_item else 0
            payload.append((
                item["item_type"],
                item["item_id"],
                item["scope"],
                translation_text_hash(item["source_text"]),
                item["source_text"],
                translated,
                next_status,
                item["provider"],
                item["model"],
                attempt_count,
                item["last_error"],
                item["source_page"],
            ))

        cursor.executemany(
            '''
            INSERT INTO translation_workbench_items (
                item_type, item_id, scope, source_text_hash, source_text, translated_text,
                status, provider, model, attempts, last_error, source_page, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(item_type, item_id) DO UPDATE SET
                scope = excluded.scope,
                source_text_hash = excluded.source_text_hash,
                source_text = excluded.source_text,
                translated_text = excluded.translated_text,
                status = excluded.status,
                provider = excluded.provider,
                model = excluded.model,
                attempts = COALESCE(excluded.attempts, translation_workbench_items.attempts),
                last_error = excluded.last_error,
                source_page = COALESCE(excluded.source_page, translation_workbench_items.source_page),
                updated_at = CURRENT_TIMESTAMP
            ''',
            payload,
        )
    return len(normalized)


def sync_translation_workbench_from_mappings(
    *,
    item_type: str | None = None,
    q: str | None = None,
    limit: int | None = 500,
) -> int:
    """Seed workbench rows from authoritative translation_mappings."""
    if item_type and not _valid_workbench_type(item_type):
        return 0
    types = [item_type] if item_type else sorted(_VALID_TYPES)
    q_text = str(q or "").strip()
    q_like = f"%{q_text}%" if q_text else ""
    try:
        parsed_limit = None if limit is None else int(limit or 500)
    except Exception:
        parsed_limit = 500
    max_entries = None if parsed_limit is None else max(1, min(parsed_limit, 5000))
    entries: list[dict] = []

    def reached_limit() -> bool:
        return max_entries is not None and len(entries) >= max_entries

    with get_db() as conn:
        cursor = conn.cursor()
        for current_type in types:
            if current_type == "title":
                clauses = [
                    "content_id NOT LIKE '_global:%'",
                    "title_json IS NOT NULL",
                    "title_json NOT IN ('{}', '\"\"')",
                ]
                params: list[object] = []
                if q_text:
                    clauses.append("(content_id LIKE ? OR title_json LIKE ?)")
                    params.extend([q_like, q_like])
                sql = f'''
                    SELECT content_id, title_json
                    FROM translation_mappings
                    WHERE {' AND '.join(clauses)}
                    ORDER BY updated_at DESC
                '''
                query_params = [*params]
                if max_entries is not None:
                    sql += " LIMIT ?"
                    query_params.append(max_entries)
                cursor.execute(sql, query_params)
                for row in cursor.fetchall():
                    content_id = str(row["content_id"] or "")
                    for source, translated in _valid_mapping(_json_mapping(row["title_json"])).items():
                        if q_text and q_text not in content_id and q_text not in source and q_text not in str(translated):
                            continue
                        entries.append({
                            "item_type": "title",
                            "item_id": _normalize_title_id(content_id),
                            "source_text": source,
                            "translated_text": str(translated),
                            "status": "machine_translated",
                            "provider": "mapping",
                            "scope": _workbench_scope("title", _normalize_title_id(content_id), source),
                        })
                        if reached_limit():
                            break
                    if reached_limit():
                        break
                continue

            col = f"{current_type}_json"
            if col not in _VALID_COLUMNS:
                continue
            clauses = [
                "(content_id LIKE ? OR content_id LIKE ?)",
                f"{col} IS NOT NULL",
                f"{col} NOT IN ('{{}}', '\"\"')",
            ]
            params = [f"{current_type}:%", f"_global:{current_type}:%"]
            sql = f'''
                SELECT content_id, {col}
                FROM translation_mappings
                WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC
            '''
            query_params = [*params]
            if max_entries is not None and not q_text:
                sql += " LIMIT ?"
                query_params.append(max_entries)
            cursor.execute(sql, query_params)
            prefix = f"{current_type}:"
            global_prefix = f"_global:{current_type}:"
            for row in cursor.fetchall():
                content_id = str(row["content_id"] or "")
                if content_id.startswith(global_prefix):
                    item_id = content_id[len(global_prefix):]
                elif content_id.startswith(prefix):
                    item_id = content_id[len(prefix):]
                else:
                    continue
                for source, translated in _valid_mapping(_json_mapping(row[col])).items():
                    if q_text and q_text not in item_id and q_text not in source and q_text not in str(translated):
                        continue
                    entries.append({
                        "item_type": current_type,
                        "item_id": item_id,
                        "source_text": source,
                        "translated_text": str(translated),
                        "status": "machine_translated",
                        "provider": "mapping",
                        "scope": _workbench_scope(current_type, item_id, source),
                    })
                    if reached_limit():
                        break
                if reached_limit():
                    break
            if reached_limit():
                break

    return bulk_upsert_translation_workbench_items(entries)


def mark_translation_workbench_success(
    entries: list[dict],
    *,
    status: str = "machine_translated",
    preserve_reviewed: bool = True,
) -> int:
    if status not in {"machine_translated", "reviewed", "manual_edited"}:
        status = "machine_translated"
    return bulk_upsert_translation_workbench_items(
        [
            {
                **entry,
                "translated_text": str(entry.get("translated_text") or ""),
                "status": status,
                "last_error": None,
            }
            for entry in entries
        ],
        preserve_reviewed=preserve_reviewed,
    )


def mark_translation_workbench_failed(entries: list[dict], *, error: str = "translation failed") -> int:
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for entry in entries:
            item_type = str(entry.get("item_type") or entry.get("type") or "")
            item_id = _normalize_workbench_item_id(item_type, entry.get("item_id") if entry.get("item_id") is not None else entry.get("id"))
            source_text = str(entry.get("source_text") or entry.get("source") or "")
            if not _valid_workbench_type(item_type) or not item_id or not source_text:
                continue
            scope = str(entry.get("scope") or _workbench_scope(item_type, item_id, source_text))
            cursor.execute(
                '''
                INSERT INTO translation_workbench_items (
                    item_type, item_id, scope, source_text_hash, source_text, translated_text,
                    status, provider, model, attempts, last_error, source_page, updated_at
                )
                VALUES (?, ?, ?, ?, ?, '', 'failed', ?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(item_type, item_id) DO UPDATE SET
                    scope = excluded.scope,
                    source_text_hash = excluded.source_text_hash,
                    source_text = excluded.source_text,
                    status = 'failed',
                    provider = excluded.provider,
                    model = excluded.model,
                    attempts = COALESCE(translation_workbench_items.attempts, 0) + 1,
                    last_error = excluded.last_error,
                    source_page = COALESCE(excluded.source_page, translation_workbench_items.source_page),
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (
                    item_type,
                    item_id,
                    scope,
                    translation_text_hash(source_text),
                    source_text,
                    entry.get("provider"),
                    entry.get("model"),
                    str(entry.get("last_error") or error),
                    entry.get("source_page"),
                ),
            )
            count += 1
    return count


def get_translation_workbench_item(item_type: str, item_id: object) -> dict | None:
    if not _valid_workbench_type(item_type):
        return None
    normalized_id = _normalize_workbench_item_id(item_type, item_id)
    if not normalized_id:
        return None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM translation_workbench_items WHERE item_type = ? AND item_id = ?",
            (item_type, normalized_id),
        )
        row = cursor.fetchone()
        return _row_to_workbench_item(row) if row else None


def _workbench_where(
    *,
    item_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    ids: list[str] | None = None,
    statuses: list[str] | None = None,
    after_row_id: int | None = None,
) -> tuple[list[str], list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    if item_type and _valid_workbench_type(item_type):
        clauses.append("item_type = ?")
        params.append(item_type)
    if status and _valid_workbench_status(status):
        clauses.append("status = ?")
        params.append(status)
    elif statuses:
        valid_statuses = [item for item in statuses if _valid_workbench_status(item)]
        if valid_statuses:
            clauses.append(f"status IN ({','.join('?' for _ in valid_statuses)})")
            params.extend(valid_statuses)
    if q:
        like = f"%{q.strip()}%"
        clauses.append("(item_id LIKE ? OR source_text LIKE ? OR translated_text LIKE ?)")
        params.extend([like, like, like])
    if ids:
        normalized_ids = [_normalize_workbench_item_id(item_type or "", item) for item in ids]
        normalized_ids = [item for item in normalized_ids if item]
        if normalized_ids:
            clauses.append(f"item_id IN ({','.join('?' for _ in normalized_ids)})")
            params.extend(normalized_ids)
    if after_row_id:
        clauses.append("id > ?")
        params.append(after_row_id)
    return clauses, params


def list_translation_workbench_items(
    *,
    item_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 50), 200))
    clauses, params = _workbench_where(item_type=item_type, status=status, q=q)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM translation_workbench_items {where}", params)
        total = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            f'''
            SELECT *
            FROM translation_workbench_items
            {where}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            ''',
            [*params, page_size, (page - 1) * page_size],
        )
        rows = [_row_to_workbench_item(row) for row in cursor.fetchall()]
    return {
        "data": rows,
        "page": page,
        "page_size": page_size,
        "total_count": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def list_translation_workbench_retry_batch(
    *,
    item_type: str | None = None,
    statuses: list[str] | None = None,
    q: str | None = None,
    ids: list[str] | None = None,
    after_row_id: int = 0,
    limit: int = 1000,
) -> list[dict]:
    limit = max(1, min(int(limit or 1000), 5000))
    clauses, params = _workbench_where(
        item_type=item_type,
        statuses=statuses or ["failed", "untranslated"],
        q=q,
        ids=ids,
        after_row_id=max(0, int(after_row_id or 0)),
    )
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f'''
            SELECT *
            FROM translation_workbench_items
            {where}
            ORDER BY id ASC
            LIMIT ?
            ''',
            [*params, limit],
        )
        return [_row_to_workbench_item(row) for row in cursor.fetchall()]


def translation_workbench_stats(item_type: str | None = None) -> dict:
    clauses = []
    params: list[object] = []
    if item_type and _valid_workbench_type(item_type):
        clauses.append("item_type = ?")
        params.append(item_type)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    by_status = {status: 0 for status in sorted(_WORKBENCH_STATUSES)}
    by_type = {item: 0 for item in sorted(_VALID_TYPES)}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT status, COUNT(*) AS count FROM translation_workbench_items {where} GROUP BY status",
            params,
        )
        for row in cursor.fetchall():
            by_status[str(row["status"] or "untranslated")] = int(row["count"] or 0)
        cursor.execute(
            f"SELECT item_type, COUNT(*) AS count FROM translation_workbench_items {where} GROUP BY item_type",
            params,
        )
        for row in cursor.fetchall():
            by_type[str(row["item_type"])] = int(row["count"] or 0)
        cursor.execute(f"SELECT COUNT(*) FROM translation_workbench_items {where}", params)
        total = int(cursor.fetchone()[0] or 0)
    return {"total": total, "by_status": by_status, "by_type": by_type}


def _add_translation_workbench_history(
    item_type: str,
    item_id: str,
    source_text: str,
    old_text: str | None,
    new_text: str | None,
    action: str,
    operator: str = "manual",
) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO translation_workbench_history (
                item_type, item_id, source_text, old_text, new_text, action, operator, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''',
            (item_type, item_id, source_text, old_text, new_text, action, operator),
        )
        return int(cursor.lastrowid)


def save_translation_workbench_manual(
    item_type: str,
    item_id: object,
    translated_text: str,
    *,
    operator: str = "manual",
    status: str = "manual_edited",
) -> dict | None:
    item = get_translation_workbench_item(item_type, item_id)
    if not item:
        return None
    source_text = str(item.get("source_text") or "")
    normalized_id = str(item.get("item_id") or "")
    new_text = str(translated_text or "").strip()
    if not source_text or not new_text:
        return None
    old_text = str(item.get("translated_text") or "") or _formal_mapping_text(item_type, normalized_id, source_text)
    content_id = normalized_id if item_type == "title" else f"{item_type}:{normalized_id}"
    upsert_translation(content_id, {item_type: {source_text: new_text}})
    saved = upsert_translation_workbench_item(
        item_type,
        normalized_id,
        source_text,
        translated_text=new_text,
        status=status if status in {"manual_edited", "reviewed"} else "manual_edited",
        provider=operator or "manual",
        model=None,
        last_error=None,
        scope=str(item.get("scope") or ""),
        preserve_reviewed=False,
    )
    _add_translation_workbench_history(item_type, normalized_id, source_text, old_text, new_text, "save", operator)
    return saved


def review_translation_workbench_item(item_type: str, item_id: object, *, operator: str = "manual") -> dict | None:
    item = get_translation_workbench_item(item_type, item_id)
    if not item:
        return None
    translated = str(item.get("translated_text") or "") or _formal_mapping_text(
        item_type,
        str(item.get("item_id") or ""),
        str(item.get("source_text") or ""),
    )
    saved = upsert_translation_workbench_item(
        item_type,
        item.get("item_id"),
        str(item.get("source_text") or ""),
        translated_text=translated,
        status="reviewed",
        provider=item.get("provider"),
        model=item.get("model"),
        scope=item.get("scope"),
        preserve_reviewed=False,
    )
    _add_translation_workbench_history(
        item_type,
        str(item.get("item_id") or ""),
        str(item.get("source_text") or ""),
        translated,
        translated,
        "review",
        operator,
    )
    return saved


def reset_translation_workbench_item(
    item_type: str,
    item_id: object,
    *,
    operator: str = "manual",
    clear_mapping: bool = True,
) -> dict | None:
    item = get_translation_workbench_item(item_type, item_id)
    if not item:
        return None
    source_text = str(item.get("source_text") or "")
    normalized_id = str(item.get("item_id") or "")
    old_text = str(item.get("translated_text") or "") or _formal_mapping_text(item_type, normalized_id, source_text)
    if clear_mapping:
        _remove_formal_mapping_text(item_type, normalized_id, source_text)
    saved = upsert_translation_workbench_item(
        item_type,
        normalized_id,
        source_text,
        translated_text="",
        status="untranslated",
        provider=None,
        model=None,
        attempts=0,
        last_error=None,
        scope=item.get("scope"),
        preserve_reviewed=False,
    )
    _add_translation_workbench_history(item_type, normalized_id, source_text, old_text, "", "reset", operator)
    return saved


def restore_translation_workbench_history(
    item_type: str,
    item_id: object,
    history_id: int,
    *,
    operator: str = "manual",
) -> dict | None:
    item = get_translation_workbench_item(item_type, item_id)
    if not item:
        return None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT *
            FROM translation_workbench_history
            WHERE id = ? AND item_type = ? AND item_id = ?
            ''',
            (history_id, item_type, item["item_id"]),
        )
        history = cursor.fetchone()
    if not history:
        return None
    restore_text = str(history["old_text"] or "")
    if not restore_text:
        return reset_translation_workbench_item(item_type, item["item_id"], operator=operator, clear_mapping=True)
    saved = save_translation_workbench_manual(
        item_type,
        item["item_id"],
        restore_text,
        operator=operator,
        status="manual_edited",
    )
    _add_translation_workbench_history(
        item_type,
        str(item["item_id"]),
        str(item["source_text"] or ""),
        str(item.get("translated_text") or ""),
        restore_text,
        "restore",
        operator,
    )
    return saved


def list_translation_workbench_history(item_type: str, item_id: object, *, limit: int = 50) -> list[dict]:
    if not _valid_workbench_type(item_type):
        return []
    normalized_id = _normalize_workbench_item_id(item_type, item_id)
    if not normalized_id:
        return []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT *
            FROM translation_workbench_history
            WHERE item_type = ? AND item_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            ''',
            (item_type, normalized_id, max(1, min(int(limit or 50), 200))),
        )
        return [dict(row) for row in cursor.fetchall()]


def add_translation_job(job_type: str, scope: str = "library", provider_order: list[str] | None = None) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO translation_jobs (job_type, scope, provider_order_json, status, created_at)
            VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            ''',
            (job_type, scope, json.dumps(provider_order or [], ensure_ascii=False)),
        )
        return cursor.lastrowid


def update_translation_job(
    job_id: int,
    *,
    status: str | None = None,
    total: int | None = None,
    processed: int | None = None,
    translated: int | None = None,
    skipped: int | None = None,
    failed: int | None = None,
    error_msg: str | None = None,
    result: dict | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> None:
    fields = []
    params = []
    for key, value in (
        ("status", status),
        ("total", total),
        ("processed", processed),
        ("translated", translated),
        ("skipped", skipped),
        ("failed", failed),
        ("error_msg", error_msg),
        ("started_at", started_at),
        ("finished_at", finished_at),
    ):
        if value is not None:
            fields.append(f"{key} = ?")
            params.append(value)
    if result is not None:
        fields.append("result_json = ?")
        params.append(json.dumps(result, ensure_ascii=False))
    fields.append("updated_at = CURRENT_TIMESTAMP")
    if not fields:
        return
    params.append(job_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE translation_jobs SET {', '.join(fields)} WHERE id = ?", params)


def _parse_job_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = str(value).replace("Z", "").replace("T", " ")
    try:
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def _job_duration_seconds(data: dict) -> int | None:
    started = _parse_job_timestamp(data.get("started_at"))
    if not started:
        return None
    finished = _parse_job_timestamp(data.get("finished_at"))
    if not finished and data.get("status") in {"running", "pending"}:
        finished = datetime.utcnow()
    if not finished:
        return None
    return max(0, int((finished - started).total_seconds()))


def _job_progress_percent(data: dict) -> int:
    total = int(data.get("total") or 0)
    processed = int(data.get("processed") or 0)
    status = data.get("status")
    if total > 0:
        return max(0, min(100, round(processed * 100 / total)))
    if status == "completed":
        return 100
    return 0


def _decode_translation_job(row) -> Optional[dict]:
    if not row:
        return None
    data = dict(row)
    for field, default in (("provider_order_json", []), ("result_json", None)):
        raw = data.pop(field, None)
        key = field.replace("_json", "")
        if raw:
            try:
                data[key] = json.loads(raw)
            except Exception:
                data[key] = default
        else:
            data[key] = default
    if not isinstance(data.get("provider_order"), list):
        data["provider_order"] = []
    if isinstance(data.get("result"), dict):
        data["provider_order"] = data["provider_order"] or data["result"].get("provider_order", [])
    data["progress_percent"] = _job_progress_percent(data)
    data["duration_seconds"] = _job_duration_seconds(data)
    return data


def get_translation_job(job_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM translation_jobs WHERE id = ?", (job_id,))
        return _decode_translation_job(cursor.fetchone())


def list_translation_jobs(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM translation_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [_decode_translation_job(row) for row in cursor.fetchall()]
