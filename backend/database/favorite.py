"""收藏与收藏夹数据库层"""
import json
from typing import List, Optional, Dict
from database.base import get_db


def init_favorite_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                entity_type TEXT,
                entity_id TEXT,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_type, entity_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_items (
                collection_id INTEGER,
                entity_type TEXT,
                entity_id TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (collection_id, entity_type, entity_id),
                FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE
            )
        ''')


def toggle_favorite(entity_type: str, entity_id: str, metadata: Optional[Dict] = None) -> bool:
    """切换收藏状态。返回 True 表示已收藏，False 表示已取消。"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM favorites WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id)
        )
        exists = cursor.fetchone()
        if exists:
            cursor.execute(
                "DELETE FROM favorites WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            )
            return False
        else:
            cursor.execute(
                "INSERT INTO favorites (entity_type, entity_id, metadata_json) VALUES (?, ?, ?)",
                (entity_type, entity_id, json.dumps(metadata or {}))
            )
            return True


def is_favorite(entity_type: str, entity_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM favorites WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id)
        )
        return cursor.fetchone() is not None


def list_favorites(entity_type: Optional[str] = None) -> List[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        if entity_type:
            cursor.execute(
                "SELECT entity_type, entity_id, metadata_json, created_at FROM favorites WHERE entity_type = ? ORDER BY created_at DESC",
                (entity_type,)
            )
        else:
            cursor.execute(
                "SELECT entity_type, entity_id, metadata_json, created_at FROM favorites ORDER BY created_at DESC"
            )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item['metadata'] = json.loads(item.pop('metadata_json') or '{}')
            result.append(item)
        return result


def list_collections() -> List[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, created_at FROM collections ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
