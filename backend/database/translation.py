"""翻译映射数据库层"""
import sqlite3
import json
from pathlib import Path
from typing import Optional

# 关键：database/ 在 backend/ 下，比原 database.py 深一层，所以是 parent.parent.parent
DB_PATH = Path(__file__).parent.parent.parent / "data" / "avdownloader.db"


def _get_translation_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_translation_db():
    conn = _get_translation_db()
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
    conn.commit()
    conn.close()


def _get_raw(content_id: str) -> Optional[dict]:
    conn = _get_translation_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT actress_json, category_json, series_json, title_json, maker_json, label_json FROM translation_mappings WHERE content_id = ?",
        (content_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "actress": json.loads(row["actress_json"] or "{}"),
        "category": json.loads(row["category_json"] or "{}"),
        "series": json.loads(row["series_json"] or "{}"),
        "title": json.loads(row["title_json"] or "{}"),
        "maker": json.loads(row["maker_json"] or "{}"),
        "label": json.loads(row["label_json"] or "{}"),
    }


def get_translation(content_id: str) -> Optional[dict]:
    result = _get_raw(content_id)
    if result:
        return result
    for prefix in ("_global:actress:", "_global:category:", "_global:series:"):
        result = _get_raw(prefix + content_id)
        if result:
            return result
    return None


def upsert_translation(content_id: str, mapping: dict) -> bool:
    existing = _get_raw(content_id)
    conn = _get_translation_db()
    cursor = conn.cursor()
    if existing:
        merged = {
            "actress": {**existing.get("actress", {}), **mapping.get("actress", {})},
            "category": {**existing.get("category", {}), **mapping.get("category", {})},
            "series": {**existing.get("series", {}), **mapping.get("series", {})},
            "title": mapping.get("title") or existing.get("title", ""),
        }
    else:
        merged = {
            "actress": mapping.get("actress", {}),
            "category": mapping.get("category", {}),
            "series": mapping.get("series", {}),
            "title": mapping.get("title", ""),
        }
    cursor.execute('''
        INSERT INTO translation_mappings (content_id, actress_json, category_json, series_json, title_json, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(content_id) DO UPDATE SET
            actress_json = excluded.actress_json,
            category_json = excluded.category_json,
            series_json = excluded.series_json,
            title_json = excluded.title_json,
            updated_at = CURRENT_TIMESTAMP
    ''', (content_id, json.dumps(merged["actress"]), json.dumps(merged["category"]),
          json.dumps(merged["series"]), json.dumps(merged["title"])))
    conn.commit()
    conn.close()
    return True


def get_all_translations(mapping_type: str) -> dict:
    field_map = {"actress": "actress_json", "category": "category_json",
                 "series": "series_json", "title": "title_json"}
    field = field_map.get(mapping_type)
    if not field:
        return {}
    conn = _get_translation_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT content_id, {field} FROM translation_mappings")
    rows = cursor.fetchall()
    conn.close()
    result = {}
    for row in rows:
        parsed = json.loads(row[field] or "{}")
        if mapping_type == "title":
            if parsed:
                result[row["content_id"]] = parsed
        else:
            cid = row["content_id"]
            if cid.startswith("_global:"):
                for k, v in parsed.items():
                    result[k] = v
    return result


def import_translations(mapping_type: str, data: dict) -> int:
    if mapping_type not in ("actress", "category", "series", "title"):
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
    conn = _get_translation_db()
    cursor = conn.cursor()
    if mapping_type == "actress":
        cursor.execute("SELECT actress_json FROM translation_mappings WHERE content_id LIKE 'actress:%'")
        rows = cursor.fetchall()
        total = sum(len(json.loads(row["actress_json"] or "{}")) for row in rows)
        conn.close()
        return total
    elif mapping_type in ("category", "series"):
        cursor.execute(f"SELECT {mapping_type}_json FROM translation_mappings WHERE content_id LIKE '{mapping_type}:%'")
        rows = cursor.fetchall()
        total = sum(len(json.loads(row[mapping_type + "_json"] or "{}")) for row in rows)
        conn.close()
        return total
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM translation_mappings WHERE title_json IS NOT NULL AND title_json != '{}' AND title_json != '{ }' AND content_id NOT LIKE '_global:%'"
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
