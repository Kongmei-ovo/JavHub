"""收藏与收藏夹数据库层"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict

# 关键：database/ 在 backend/ 下，比原 database.py 深一层，所以是 parent.parent.parent
DB_PATH = Path(__file__).parent.parent.parent / "data" / "avdownloader.db"


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_favorite_db():
    conn = _get_db()
    cursor = conn.cursor()
    # 收藏表：支持视频、女优、系列等
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            entity_type TEXT,
            entity_id TEXT,
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (entity_type, entity_id)
        )
    ''')
    # 收藏夹表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 收藏夹内容表
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
    conn.commit()
    conn.close()


def toggle_favorite(entity_type: str, entity_id: str, metadata: Optional[Dict] = None) -> bool:
    """切换收藏状态。返回 True 表示已收藏，False 表示已取消。"""
    conn = _get_db()
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
        is_favorited = False
    else:
        cursor.execute(
            "INSERT INTO favorites (entity_type, entity_id, metadata_json) VALUES (?, ?, ?)",
            (entity_type, entity_id, json.dumps(metadata or {}))
        )
        is_favorited = True
        
    conn.commit()
    conn.close()
    return is_favorited


def is_favorite(entity_type: str, entity_id: str) -> bool:
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM favorites WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def list_favorites(entity_type: Optional[str] = None) -> List[Dict]:
    conn = _get_db()
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
    conn.close()
    
    result = []
    for row in rows:
        item = dict(row)
        item['metadata'] = json.loads(item.pop('metadata_json') or '{}')
        result.append(item)
    return result


def list_collections() -> List[Dict]:
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, created_at FROM collections ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
