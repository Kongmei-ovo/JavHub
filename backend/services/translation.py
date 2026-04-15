"""翻译映射服务：应用字段翻译到影片数据"""
from database import get_translation
from typing import Any


def _translate_item(original: str, mapping: dict[str, str]) -> str:
    """单个字段翻译，有映射返回译文，无映射返回原文"""
    if not original or not mapping:
        return original
    return mapping.get(original, original)


def apply_translation(content_id: str, data: dict) -> dict:
    """对影片数据应用翻译映射，返回带 translated_ 前缀字段的副本"""
    if not content_id or not data:
        return data
    data = dict(data)

    # per-content_id 映射（标题翻译等）
    content_mapping = get_translation(content_id)

    # === actress：按 ID 查找翻译 ===
    if "actresses" in data and isinstance(data["actresses"], list):
        for actress in data["actresses"]:
            if not isinstance(actress, dict):
                continue
            actress_id = actress.get("id")
            if actress_id:
                actress_trans = get_translation(f"actress:{actress_id}")
                actress_map = actress_trans.get("actress", {}) if actress_trans else {}
            else:
                actress_map = {}
            for name_key in ["name_ja", "name_en", "name_kanji", "name_romaji", "name"]:
                orig = actress.get(name_key)
                if orig:
                    translated = _translate_item(orig, actress_map)
                    actress[f"{name_key}_translated"] = translated
                    break

    # === category：按 ID 查找翻译 ===
    if "categories" in data and isinstance(data["categories"], list):
        for cat in data["categories"]:
            if not isinstance(cat, dict):
                continue
            cat_id = cat.get("id")
            cat_map = {}
            if cat_id:
                cat_trans = get_translation(f"category:{cat_id}")
                if cat_trans:
                    cat_map = cat_trans.get("category", {})
            if not cat_map and content_mapping:
                cat_map = content_mapping.get("category", {})
            for name_key in ["name_ja", "name_en", "name"]:
                orig = cat.get(name_key)
                if orig:
                    translated = _translate_item(orig, cat_map)
                    cat[f"{name_key}_translated"] = translated
                    break

    # === series：按 ID 查找翻译 ===
    if "series" in data and isinstance(data["series"], dict) and data["series"]:
        series = data["series"]
        series_id = series.get("id")
        series_map = {}
        if series_id:
            series_trans = get_translation(f"series:{series_id}")
            if series_trans:
                series_map = series_trans.get("series", {})
        if not series_map and content_mapping:
            series_map = content_mapping.get("series", {})
        name = series.get("name")
        if name:
            translated = _translate_item(name, series_map)
            series["name_translated"] = translated

    # === maker：按 ID 查找翻译 ===
    if "maker" in data and isinstance(data["maker"], dict) and data["maker"]:
        maker = data["maker"]
        maker_id = maker.get("id")
        maker_map = {}
        if maker_id:
            maker_trans = get_translation(f"maker:{maker_id}")
            if maker_trans:
                maker_map = maker_trans.get("maker", {})
        if not maker_map and content_mapping:
            maker_map = content_mapping.get("maker", {})
        for name_key in ["name_ja", "name_en", "name"]:
            orig = maker.get(name_key)
            if orig:
                translated = _translate_item(orig, maker_map)
                maker[f"{name_key}_translated"] = translated
                break

    # === label：按 ID 查找翻译 ===
    if "label" in data and isinstance(data["label"], dict) and data["label"]:
        label = data["label"]
        label_id = label.get("id")
        label_map = {}
        if label_id:
            label_trans = get_translation(f"label:{label_id}")
            if label_trans:
                label_map = label_trans.get("label", {})
        if not label_map and content_mapping:
            label_map = content_mapping.get("label", {})
        for name_key in ["name_ja", "name_en", "name"]:
            orig = label.get(name_key)
            if orig:
                translated = _translate_item(orig, label_map)
                label[f"{name_key}_translated"] = translated
                break

    # === title ===
    title_map = {}
    if content_mapping:
        title_map = content_mapping.get("title", {})
    for title_key in ["title_en", "title_ja"]:
        orig = data.get(title_key)
        if orig:
            translated = _translate_item(orig, title_map)
            data[f"{title_key}_translated"] = translated

    return data
