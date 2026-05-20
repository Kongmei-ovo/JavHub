from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
import json
import io
import asyncio
import logging
from typing import Any, Optional

from config import config
from database import (
    get_all_translations,
    import_translations,
    get_translation_cache_count,
    get_translation_count,
    get_translation_coverage_counts,
    list_translation_workbench_history,
    list_translation_workbench_items,
    reset_translation_workbench_item,
    restore_translation_workbench_history,
    review_translation_workbench_item,
    save_translation_workbench_manual,
    sync_translation_workbench_from_mappings,
    translation_workbench_stats,
    _get_raw,
    upsert_translation,
    upsert_translation_workbench_item,
)
from modules.info_client import get_info_client
from translations import get_translator_service
from translations.jobs import (
    create_translation_job,
    create_translation_retry_job,
    get_job as get_translation_job_status,
    list_jobs as list_translation_job_statuses,
    pause_translation_job,
)

router = APIRouter(prefix="/api/v1/translations", tags=["translations"])
logger = logging.getLogger(__name__)

VALID_TYPES = {"actress", "category", "series", "maker", "label", "title"}

EXPORT_FIELDS = {
    "actress": ("name_kanji", "name_translated"),
    "category": ("name_ja", "name_translated"),
    "series": ("name_ja", "name_translated"),
    "maker": ("name_ja", "name_translated"),
    "label": ("name_ja", "name_translated"),
    "title": ("title_ja", "title_translated"),
}

TOTAL_ENDPOINTS = {
    "title": "/api/v1/videos",
    "actress": "/api/v1/actresses",
    "category": "/api/v1/categories",
    "series": "/api/v1/series",
    "maker": "/api/v1/makers",
    "label": "/api/v1/labels",
}


def _translation_export_payload(mapping_type: str, data: dict[str, Any]) -> dict[str, Any]:
    src, dst = EXPORT_FIELDS[mapping_type]
    return {
        "_type": mapping_type,
        "_version": "2",
        "_src": src,
        "_dst": dst,
        "data": data,
    }


def _unwrap_translation_payload(mapping_type: str, data: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    default_src, default_dst = EXPORT_FIELDS[mapping_type]
    src = str(data.get("_src") or default_src)
    dst = str(data.get("_dst") or default_dst)
    entries = data.get("data") if isinstance(data.get("data"), dict) else None
    if entries is None:
        entries = {k: v for k, v in data.items() if not str(k).startswith("_")}
    return entries, src, dst


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


def _first_text(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _title_source(item: dict[str, Any]) -> str:
    return _first_text(item, ("title_ja", "title_en", "title"))


def _content_id(item: dict[str, Any]) -> str:
    return str(item.get("content_id") or item.get("dvd_id") or item.get("canonical_number") or "").strip()


def _normalize_title_id(value: str) -> str:
    return str(value or "").replace("-", "").replace("_", "").lower()


def _existing_title_translation(content_id: str, source: str) -> str:
    for candidate in {_normalize_title_id(content_id), content_id}:
        raw = _get_raw(candidate)
        mapping = raw.get("title", {}) if raw else {}
        translated = mapping.get(source) if isinstance(mapping, dict) else ""
        if translated:
            return str(translated)
    return ""


async def _seed_workbench_from_javinfo(item_type: str | None, q: str | None) -> int:
    if not item_type or not q:
        return 0
    info = get_info_client()
    seeded = 0
    if item_type == "title":
        result = await info.search_videos(q=q, page=1, page_size=50)
        for item in result.get("data", []) if isinstance(result, dict) else []:
            content_id = _content_id(item)
            source = _title_source(item)
            if not content_id or not source:
                continue
            translated = _existing_title_translation(content_id, source)
            upsert_translation_workbench_item(
                "title",
                _normalize_title_id(content_id),
                source,
                translated_text=translated,
                status="machine_translated" if translated else "untranslated",
                provider="mapping" if translated else None,
            )
            seeded += 1
        return seeded

    loaders = {
        "actress": lambda: info.list_actresses(q=q, page=1, page_size=50),
        "category": lambda: info.list_categories(q=q),
        "series": lambda: info.list_series(q=q),
        "maker": lambda: info.list_makers(q=q),
        "label": lambda: info.list_labels(q=q),
    }
    loader = loaders.get(item_type)
    if not loader:
        return 0
    result = await loader()
    items = result.get("data", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    text_keys = {
        "actress": ("name_kanji", "name_ja", "name_romaji", "name"),
        "category": ("name_ja", "name_en", "name"),
        "series": ("name_ja", "name_en", "name"),
        "maker": ("name_ja", "name_en", "name"),
        "label": ("name_ja", "name_en", "name"),
    }
    for item in items:
        entity_id = item.get("id")
        source = _first_text(item, text_keys.get(item_type, ("name",)))
        if not entity_id or not source:
            continue
        try:
            numeric_id = int(entity_id)
        except (TypeError, ValueError):
            numeric_id = 0
        translated = (
            _lookup_actress_translation_by_id(numeric_id)
            if item_type == "actress"
            else _lookup_named_translation_by_id(item_type, numeric_id)
        ) or ""
        upsert_translation_workbench_item(
            item_type,
            entity_id,
            source,
            translated_text=translated,
            status="machine_translated" if translated else "untranslated",
            provider="mapping" if translated else None,
        )
        seeded += 1
    return seeded


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
        title_rows: dict[str, Any] = {}
        for content_id, mapping in get_all_translations("title").items():
            if not isinstance(mapping, dict):
                continue
            for source, translated in mapping.items():
                if source and translated:
                    title_rows[str(content_id)] = {
                        "content_id": content_id,
                        "title_ja": source,
                        "title_translated": translated,
                    }
                    break
        data = title_rows

    content = json.dumps(_translation_export_payload(mapping_type, data), ensure_ascii=False, indent=2)
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

    entries, src_field, dst_field = _unwrap_translation_payload(mapping_type, data)

    if mapping_type == "actress":
        # 格式: { actress_id: { name_kanji: "...", name_translated: "..." } }
        # 存储为 actress:{actress_id} → { name_kanji: translated }
        count = 0
        for key, value in entries.items():
            if not isinstance(value, dict):
                continue
            try:
                actress_id = int(key)
            except (ValueError, TypeError):
                continue
            name_translated = value.get(dst_field, "")
            if not name_translated:
                continue
            name_kanji = value.get(src_field, "") or value.get("name_kanji", "")
            if not name_kanji:
                continue
            upsert_translation(f"actress:{actress_id}", {"actress": {name_kanji: name_translated}})
            upsert_translation_workbench_item(
                "actress",
                actress_id,
                name_kanji,
                translated_text=name_translated,
                status="manual_edited",
                provider="import",
                preserve_reviewed=False,
            )
            count += 1
        return {"success": True, "imported": count, "type": mapping_type}

    if mapping_type in ("category", "series", "maker", "label"):
        # 格式: { type_id: { name: "...", name_translated: "..." } }
        # 存储为 {type}:{id} → { name: translated }
        count = 0
        for key, value in entries.items():
            if not isinstance(value, dict):
                continue
            try:
                type_id = int(key)
            except (ValueError, TypeError):
                continue
            name_translated = value.get(dst_field, "")
            if not name_translated:
                continue
            orig_name = value.get(src_field) or value.get("name_ja") or value.get("name_en") or value.get("name", "")
            if not orig_name:
                continue
            upsert_translation(f"{mapping_type}:{type_id}", {mapping_type: {orig_name: name_translated}})
            upsert_translation_workbench_item(
                mapping_type,
                type_id,
                orig_name,
                translated_text=name_translated,
                status="manual_edited",
                provider="import",
                preserve_reviewed=False,
            )
            count += 1
        return {"success": True, "imported": count, "type": mapping_type}

    is_wrapped_title = isinstance(data.get("data"), dict) or "_src" in data or "_dst" in data
    if mapping_type == "title" and is_wrapped_title:
        count = 0
        for key, value in entries.items():
            if not isinstance(value, dict):
                continue
            content_id = str(value.get("content_id") or key or "").strip()
            source = str(value.get(src_field) or value.get("title_ja") or value.get("title") or "").strip()
            translated = str(value.get(dst_field) or value.get("title_translated") or "").strip()
            if not content_id or not source or not translated:
                continue
            normalized_id = content_id.replace("-", "").replace("_", "").lower()
            upsert_translation(normalized_id, {"title": {source: translated}})
            upsert_translation_workbench_item(
                "title",
                normalized_id,
                source,
                translated_text=translated,
                status="manual_edited",
                provider="import",
                preserve_reviewed=False,
            )
            count += 1
        return {"success": True, "imported": count, "type": mapping_type}

    count = import_translations(mapping_type, data)
    sync_translation_workbench_from_mappings(item_type=mapping_type, limit=1000)
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
    info = get_info_client()
    totals: dict[str, int] = {}
    total_results = await asyncio.gather(
        *(info.get_total_count(path) for path in TOTAL_ENDPOINTS.values()),
        return_exceptions=True,
    )
    for mapping_type, result in zip(TOTAL_ENDPOINTS.keys(), total_results):
        totals[mapping_type] = 0 if isinstance(result, Exception) else int(result or 0)

    coverage: dict[str, dict[str, int]] = {}
    for mapping_type in VALID_TYPES:
        local = get_translation_coverage_counts(mapping_type)
        total = totals.get(mapping_type, 0)
        translated = min(total, int(local.get("translated", 0) or 0)) if total else int(local.get("translated", 0) or 0)
        item = {
            "total": total,
            "translated": translated,
            "untranslated": max(total - translated, 0),
        }
        if mapping_type == "title":
            item["mapped"] = int(local.get("mapped", 0) or 0)
            item["cached"] = int(local.get("cached", 0) or 0)
        coverage[mapping_type] = item

    translation_cfg = config.translation
    selected_provider = config.translation_provider
    ai_cfg = config.ai
    ai_provider = str(ai_cfg.get("provider") or "openai_compatible")
    provider_cfg = ai_cfg.get(ai_provider, {}) if isinstance(ai_cfg.get(ai_provider), dict) else {}
    stats["ai_cache"] = get_translation_cache_count()
    stats["coverage"] = coverage
    stats["workbench"] = translation_workbench_stats()
    stats["providers"] = {
        "cache": {"enabled": "cache" in config.translation_provider_order, "ready": True},
        "mapping": {"enabled": "mapping" in config.translation_provider_order, "ready": True},
        "google_free": {
            "enabled": selected_provider == "google_free",
            "ready": bool((translation_cfg.get("google_free") or {}).get("enabled", True)),
        },
        "baidu": {
            "enabled": selected_provider == "baidu",
            "ready": bool(
                (translation_cfg.get("baidu") or {}).get("enabled")
                and (translation_cfg.get("baidu") or {}).get("app_id")
                and (translation_cfg.get("baidu") or {}).get("secret")
            ),
        },
        "deepl": {
            "enabled": selected_provider == "deepl",
            "ready": bool((translation_cfg.get("deepl") or {}).get("enabled") and (translation_cfg.get("deepl") or {}).get("api_key")),
        },
        "microsoft": {
            "enabled": selected_provider == "microsoft",
            "ready": bool((translation_cfg.get("microsoft") or {}).get("enabled") and (translation_cfg.get("microsoft") or {}).get("api_key")),
        },
        "ai": {
            "enabled": selected_provider == "ai",
            "ready": bool(
                provider_cfg.get("base_url")
                and provider_cfg.get("model")
                and (ai_provider == "ollama" or provider_cfg.get("api_key"))
            ),
            "model": provider_cfg.get("model") or "",
            "provider": ai_provider,
        },
    }
    return stats


@router.get("/items")
async def list_translation_items(
    item_type: str | None = Query(None, alias="type"),
    q: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    item_type = str(item_type).strip() if isinstance(item_type, str) and item_type.strip() else None
    q = str(q).strip() if isinstance(q, str) and q.strip() else None
    status = str(status).strip() if isinstance(status, str) and status.strip() else None
    try:
        page = int(page)
    except Exception:
        page = 1
    try:
        page_size = int(page_size)
    except Exception:
        page_size = 50
    if item_type and item_type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
    seeded = 0
    if item_type:
        seeded += sync_translation_workbench_from_mappings(
            item_type=item_type,
            q=q,
            limit=None,
        )
    if item_type and q:
        try:
            seeded += await _seed_workbench_from_javinfo(item_type, q.strip())
        except Exception:
            logger.debug("JavInfo metadata seeding skipped")
    result = list_translation_workbench_items(
        item_type=item_type,
        q=q,
        status=status if status and status != "all" else None,
        page=page,
        page_size=page_size,
    )
    result["stats"] = translation_workbench_stats(item_type)
    result["seeded"] = seeded
    return result


@router.post("/items/retry")
async def retry_translation_items(body: dict[str, Any] | None = None):
    body = body or {}
    item_type = str(body.get("type") or "").strip() or None
    status = str(body.get("status") or "").strip() or None
    q = str(body.get("q") or "").strip() or None
    ids = body.get("ids")
    provider_order = body.get("provider_order")
    provider = str(body.get("provider") or "").strip() or None
    if item_type and item_type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
    if ids is not None and not isinstance(ids, list):
        raise HTTPException(400, "ids must be a list")
    if provider_order is not None and not isinstance(provider_order, list):
        raise HTTPException(400, "provider_order must be a list")
    try:
        return await create_translation_retry_job(
            item_type=item_type,
            status=status if status and status != "all" else None,
            q=q,
            ids=[str(item) for item in ids] if isinstance(ids, list) else None,
            provider_order=provider_order,
            provider=provider,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/items/{item_type}/{item_id}/history")
async def get_translation_item_history(item_type: str, item_id: str, limit: int = 50):
    if item_type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
    return {"data": list_translation_workbench_history(item_type, item_id, limit=max(1, min(int(limit or 50), 200)))}


@router.patch("/items/{item_type}/{item_id}")
async def update_translation_item(item_type: str, item_id: str, body: dict[str, Any] | None = None):
    if item_type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
    body = body or {}
    action = str(body.get("action") or ("save" if body.get("translated_text") is not None else "review")).strip()
    operator = str(body.get("operator") or "manual").strip() or "manual"
    source_text = str(body.get("source_text") or "").strip()
    if source_text:
        upsert_translation_workbench_item(item_type, item_id, source_text)

    if action in {"save", "manual_edited"}:
        translated_text = str(body.get("translated_text") or "").strip()
        if not translated_text:
            raise HTTPException(400, "translated_text is required")
        item = save_translation_workbench_manual(item_type, item_id, translated_text, operator=operator)
    elif action in {"review", "proofread"}:
        item = review_translation_workbench_item(item_type, item_id, operator=operator)
    elif action == "reset":
        item = reset_translation_workbench_item(
            item_type,
            item_id,
            operator=operator,
            clear_mapping=bool(body.get("clear_mapping", True)),
        )
    elif action == "restore":
        try:
            history_id = int(body.get("history_id") or 0)
        except Exception:
            history_id = 0
        if history_id <= 0:
            raise HTTPException(400, "history_id is required")
        item = restore_translation_workbench_history(item_type, item_id, history_id, operator=operator)
    else:
        raise HTTPException(400, "action must be save, proofread, review, reset, or restore")

    if not item:
        raise HTTPException(404, "translation workbench item not found")
    return item


@router.post("/test")
async def test_translation(body: dict[str, Any]):
    """测试当前翻译源配置。"""
    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    provider = str(body.get("provider") or config.translation_provider).strip() or None
    translator = get_translator_service()
    translated = await translator.translate_text(
        text,
        scope="test",
        context="translation configuration test",
        use_ai=True,
        persist_ai=False,
        provider_order=["cache", "mapping", provider] if provider else None,
        return_original=False,
    )
    if not translated or translated == text:
        raise HTTPException(502, "No translation provider returned a translated result")
    return {"text": text, "translated_text": translated}


@router.post("/jobs")
async def start_translation_job(body: dict[str, Any] | None = None):
    body = body or {}
    job_type = str(body.get("job_type") or "library_titles")
    provider_order = body.get("provider_order")
    provider = str(body.get("provider") or "").strip() or None
    if provider_order is not None and not isinstance(provider_order, list):
        raise HTTPException(400, "provider_order must be a list")
    mode = str(body.get("mode") or "").strip()
    if not mode:
        mode = "refresh_all" if bool(body.get("force", False)) else "remaining"
    try:
        return await create_translation_job(
            job_type,
            provider_order=provider_order,
            provider=provider,
            mode=mode,
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


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: int):
    job = pause_translation_job(job_id)
    if not job:
        raise HTTPException(404, "translation job not found")
    return job
