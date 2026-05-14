from __future__ import annotations

"""翻译映射数据库层"""
import json
import hashlib
from datetime import datetime
from typing import Optional
from database.base import get_db

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
        ''', (content_id, json.dumps(merged["actress"]), json.dumps(merged["category"]),
              json.dumps(merged["series"]), json.dumps(merged["title"]),
              json.dumps(merged["maker"]), json.dumps(merged["label"])))
    return True


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


def get_translation_cache_count(status: str | None = "completed") -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT COUNT(*) FROM translation_cache WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM translation_cache")
        return cursor.fetchone()[0]


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
