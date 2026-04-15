from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import json
import io
import asyncio
from typing import Any, Optional

from database import get_all_translations, import_translations, get_translation_count, _get_raw, upsert_translation
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/translations", tags=["translations"])

VALID_TYPES = {"actress", "category", "series", "title"}


async def _fetch_all_actresses_for_export() -> dict[int, dict[str, Any]]:
    """从 JavInfo 异步获取所有演员，建立 id → actress 映射"""
    info = get_info_client()
    # 先获取总数
    first_page = await info.list_actresses(page=1, page_size=100)
    total = first_page.get("total_count", 0)
    if not total:
        return {}

    all_actresses: dict[int, dict[str, Any]] = {}
    # 收集第一页
    for a in first_page.get("data", []):
        all_actresses[a["id"]] = a

    # 计算剩余页数，并发获取（每批10页，避免过度并发）
    total_pages = (total + 99) // 100
    pages_to_fetch = list(range(2, total_pages + 1))

    # 分批并发获取，每批10页
    for i in range(0, len(pages_to_fetch), 10):
        batch = pages_to_fetch[i:i + 10]
        tasks = [info.list_actresses(page=p, page_size=100) for p in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                continue
            for a in result.get("data", []):
                all_actresses[a["id"]] = a

    return all_actresses


def _lookup_actress_translation_by_id(actress_id: int) -> Optional[str]:
    """根据演员 ID 查找翻译（存储格式：actress:{id} → {name_kanji: translated}）"""
    raw = _get_raw(f"actress:{actress_id}")
    if not raw:
        return None
    actress_json = raw.get("actress", {})
    for k, v in actress_json.items():
        if isinstance(v, str) and v:
            return v
    return None


def _lookup_category_translation_by_id(category_id: int) -> Optional[str]:
    """根据 category ID 查找翻译（存储格式：category:{id} → {name_ja: translated}）"""
    raw = _get_raw(f"category:{category_id}")
    if not raw:
        return None
    cat_json = raw.get("category", {})
    for k, v in cat_json.items():
        if isinstance(v, str) and v:
            return v
    return None


def _lookup_series_translation_by_id(series_id: int) -> Optional[str]:
    """根据 series ID 查找翻译（存储格式：series:{id} → {name: translated}）"""
    raw = _get_raw(f"series:{series_id}")
    if not raw:
        return None
    series_json = raw.get("series", {})
    for k, v in series_json.items():
        if isinstance(v, str) and v:
            return v
    return None


@router.get("/export/{mapping_type}")
async def export_translations(mapping_type: str):
    """导出指定类型的翻译映射 JSON。
    actress: 从 JavInfo 获取全部演员并匹配翻译（耗时）。
    """
    if mapping_type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of: {', '.join(VALID_TYPES)}")

    if mapping_type == "actress":
        actresses = await _fetch_all_actresses_for_export()
        result: dict[str, dict[str, Any]] = {}
        for actress_id, actress in actresses.items():
            name_kanji = actress.get("name_kanji", "")
            name_romaji = actress.get("name_romaji", "").strip()
            translated = _lookup_actress_translation_by_id(actress_id)
            entry: dict[str, Any] = {
                "id": actress_id,
                "name_kanji": name_kanji,
                "name_romaji": name_romaji,
                "name_kana": actress.get("name_kana", ""),
            }
            entry["name_translated"] = translated or ""
            result[str(actress_id)] = entry
        data = result
    elif mapping_type == "category":
        info = get_info_client()
        categories = await info.list_categories()
        result = {}
        for cat in categories:
            cat_id = cat.get("id")
            if not cat_id:
                continue
            name_ja = cat.get("name_ja", "")
            name_en = cat.get("name_en", "")
            translated = _lookup_category_translation_by_id(cat_id)
            entry: dict[str, Any] = {"id": cat_id, "name_ja": name_ja, "name_en": name_en, "name_translated": translated or ""}
            result[str(cat_id)] = entry
        data = result
    elif mapping_type == "series":
        info = get_info_client()
        all_series = await info.list_series()
        result = {}
        for series in all_series:
            series_id = series.get("id")
            if not series_id:
                continue
            name_ja = series.get("name_ja", "")
            name_en = series.get("name_en", "")
            translated = _lookup_series_translation_by_id(series_id)
            entry: dict[str, Any] = {"id": series_id, "name_ja": name_ja, "name_en": name_en, "name_translated": translated or ""}
            result[str(series_id)] = entry
        data = result
    else:
        data = get_all_translations(mapping_type)

    content = json.dumps(data, ensure_ascii=False, indent=2)
    buffer = io.BytesIO(content.encode("utf-8"))
    filename = f"translations_{mapping_type}.json"
    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import/{mapping_type}")
async def import_trans(mapping_type: str, file: UploadFile = File(...)):
    """导入翻译映射 JSON（merge upsert）"""
    if mapping_type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of: {', '.join(VALID_TYPES)}")
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(400, f"Invalid JSON: {e}")
    if not isinstance(data, dict):
        raise HTTPException(400, "JSON must be an object")

    if mapping_type == "actress":
        # 格式: { actress_id: { name_kanji: "...", name_translated: "..." } }
        # 存储为 actress:{actress_id} → { name_kanji: translated }
        count = 0
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            try:
                actress_id = int(key)
            except (ValueError, TypeError):
                continue
            name_translated = value.get("name_translated", "")
            if not name_translated:
                continue
            name_kanji = value.get("name_kanji", "")
            if not name_kanji:
                continue
            upsert_translation(f"actress:{actress_id}", {"actress": {name_kanji: name_translated}})
            count += 1
        return {"success": True, "imported": count, "type": mapping_type}

    if mapping_type in ("category", "series"):
        # 格式: { type_id: { name: "...", name_translated: "..." } }
        # 存储为 {type}:{id} → { name: translated }
        count = 0
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            try:
                type_id = int(key)
            except (ValueError, TypeError):
                continue
            name_translated = value.get("name_translated", "")
            if not name_translated:
                continue
            orig_name = value.get("name_ja") or value.get("name_en") or value.get("name", "")
            if not orig_name:
                continue
            upsert_translation(f"{mapping_type}:{type_id}", {mapping_type: {orig_name: name_translated}})
            count += 1
        return {"success": True, "imported": count, "type": mapping_type}

    count = import_translations(mapping_type, data)
    return {"success": True, "imported": count, "type": mapping_type}


@router.get("/stats/{mapping_type}")
async def translation_stats(mapping_type: str):
    """获取翻译统计"""
    if mapping_type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of: {', '.join(VALID_TYPES)}")
    count = get_translation_count(mapping_type)
    return {"type": mapping_type, "count": count}


@router.get("/stats")
async def all_stats():
    """获取所有翻译类型的统计"""
    return {t: get_translation_count(t) for t in VALID_TYPES}
