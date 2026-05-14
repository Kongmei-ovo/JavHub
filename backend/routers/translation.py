from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import json
import io
import asyncio
from typing import Any, Optional

from config import config
from database import (
    get_all_translations,
    import_translations,
    get_translation_cache_count,
    get_translation_count,
    _get_raw,
    upsert_translation,
)
from modules.info_client import get_info_client
from translations import get_translator_service
from translations.jobs import create_translation_job, get_job as get_translation_job_status, list_jobs as list_translation_job_statuses

router = APIRouter(prefix="/api/v1/translations", tags=["translations"])

VALID_TYPES = {"actress", "category", "series", "maker", "label", "title"}


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
    return _lookup_named_translation_by_id("category", category_id)


def _lookup_series_translation_by_id(series_id: int) -> Optional[str]:
    """根据 series ID 查找翻译（存储格式：series:{id} → {name: translated}）"""
    return _lookup_named_translation_by_id("series", series_id)


def _lookup_named_translation_by_id(mapping_type: str, entity_id: int) -> Optional[str]:
    """根据实体 ID 查找翻译（存储格式：{type}:{id} → {name: translated}）"""
    raw = _get_raw(f"{mapping_type}:{entity_id}")
    if not raw:
        return None
    mapping = raw.get(mapping_type, {})
    for k, v in mapping.items():
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
    elif mapping_type in ("maker", "label"):
        info = get_info_client()
        entities = await (info.list_makers() if mapping_type == "maker" else info.list_labels())
        result = {}
        for entity in entities:
            entity_id = entity.get("id")
            if not entity_id:
                continue
            name_ja = entity.get("name_ja", "")
            name_en = entity.get("name_en", "")
            name = entity.get("name", "")
            translated = _lookup_named_translation_by_id(mapping_type, entity_id)
            entry: dict[str, Any] = {
                "id": entity_id,
                "name_ja": name_ja,
                "name_en": name_en,
                "name": name,
                "name_translated": translated or "",
            }
            result[str(entity_id)] = entry
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

    if mapping_type in ("category", "series", "maker", "label"):
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
    stats = {t: get_translation_count(t) for t in VALID_TYPES}
    translation_cfg = config.translation
    openai_cfg = config.openai_compatible
    stats["ai_cache"] = get_translation_cache_count()
    stats["providers"] = {
        "cache": {"enabled": "cache" in config.translation_provider_order, "ready": True},
        "mapping": {"enabled": "mapping" in config.translation_provider_order, "ready": True},
        "google_free": {
            "enabled": "google_free" in config.translation_provider_order,
            "ready": bool((translation_cfg.get("google_free") or {}).get("enabled", True)),
        },
        "deepl": {
            "enabled": "deepl" in config.translation_provider_order,
            "ready": bool((translation_cfg.get("deepl") or {}).get("enabled") and (translation_cfg.get("deepl") or {}).get("api_key")),
        },
        "microsoft": {
            "enabled": "microsoft" in config.translation_provider_order,
            "ready": bool((translation_cfg.get("microsoft") or {}).get("enabled") and (translation_cfg.get("microsoft") or {}).get("api_key")),
        },
        "openai_compatible": {
            "enabled": "openai_compatible" in config.translation_provider_order,
            "ready": bool(openai_cfg.get("api_key") and openai_cfg.get("base_url") and openai_cfg.get("model")),
            "model": openai_cfg.get("model") or "",
        },
    }
    return stats


@router.post("/test")
async def test_translation(body: dict[str, Any]):
    """测试当前 AI 翻译配置。"""
    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    translator = get_translator_service()
    original_order = translator.settings.get("provider_order")
    translator.settings["provider_order"] = ["openai_compatible"]
    try:
        translated = await translator.translate_text(
            text,
            scope="test",
            context="translation configuration test",
            use_ai=True,
            persist_ai=False,
        )
    finally:
        if original_order is None:
            translator.settings.pop("provider_order", None)
        else:
            translator.settings["provider_order"] = original_order
    if not translated or translated == text:
        raise HTTPException(502, "No translation provider returned a translated result")
    return {"text": text, "translated_text": translated}


@router.post("/jobs")
async def start_translation_job(body: dict[str, Any] | None = None):
    body = body or {}
    job_type = str(body.get("job_type") or "library_titles")
    provider_order = body.get("provider_order")
    if provider_order is not None and not isinstance(provider_order, list):
        raise HTTPException(400, "provider_order must be a list")
    try:
        limit = int(body.get("limit") or 1000)
    except Exception:
        limit = 1000
    limit = max(1, min(limit, 10000))
    force = bool(body.get("force", False))
    try:
        return await create_translation_job(
            job_type,
            provider_order=provider_order,
            limit=limit,
            force=force,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/jobs")
async def list_translation_jobs(limit: int = 50):
    return {"data": list_translation_job_statuses(limit=max(1, min(limit, 100)))}


@router.get("/jobs/{job_id}")
async def get_translation_job(job_id: int):
    job = get_translation_job_status(job_id)
    if not job:
        raise HTTPException(404, "translation job not found")
    return job
