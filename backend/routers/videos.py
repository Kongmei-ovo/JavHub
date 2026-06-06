import asyncio
import calendar
import logging
import re
import unicodedata
from datetime import date
from fastapi import APIRouter, Query
from fastapi.params import Query as QueryParam
from typing import Any, Optional, Dict
from modules.info_client import get_info_client
from services import cache
from services.video_variants import enrich_video_variants
from services.video_variant_index import apply_indexed_variant_groups
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])
logger = logging.getLogger(__name__)
_LIST_CACHE_NAMESPACE = "videos"
_LIST_CACHE_TTL = 600
_SEARCH_CACHE_NAMESPACE = "video_search"
_SEARCH_CACHE_TTL = 600
_RANDOM_CACHE_NAMESPACE = "video_random"
_RANDOM_CACHE_TTL = 5
_DETAIL_CACHE_NAMESPACE = "video_detail"
_DETAIL_CACHE_TTL = 600


def _content_cache_id(content_id: str) -> str:
    return content_id.replace("-", "").lower()


_FREE_TEXT_CODE_RE = re.compile(r"\b([A-Za-z]{2,8})[\s_-]*([0-9]{2,6})\b")
_FREE_TEXT_YEAR_RE = re.compile(r"\b(19[8-9][0-9]|20[0-4][0-9])\b")
_FREE_TEXT_YEAR_RANGE_RE = re.compile(r"\b(19[8-9][0-9]|20[0-4][0-9])\.\.(19[8-9][0-9]|20[0-4][0-9])\b")
_FREE_TEXT_YEAR_MONTH_RE = re.compile(r"\b(19[8-9][0-9]|20[0-4][0-9])[-/.](0?[1-9]|1[0-2])\b")
_FREE_TEXT_DATE_RE = re.compile(r"\b(19[8-9][0-9]|20[0-4][0-9])[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12][0-9]|3[01])\b")
_QUARTER_RE = re.compile(r"\b(?:q([1-4])|([1-4])q)\b", re.IGNORECASE)
_FIELD_OPERATOR_RE = re.compile(r"\b(actor|actress|maker|studio|series|tag|category|label|year|date):([^\s]+)", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[0-9A-Za-z]+|[\u3040-\u30ff\u3400-\u9fff]+")
_LATIN_VOWELS_RE = re.compile(r"[aeiou]+", re.IGNORECASE)
_SEMANTIC_CATEGORY_ALIASES = {
    "cosplay": "コスプレ",
    "cosply": "コスプレ",
    "roleplay": "コスプレ",
    "maid": "メイド",
    "meido": "メイド",
    "swimsuit": "水着",
    "mizugi": "水着",
    "bikini": "水着",
    "idol": "アイドル",
    "制服": "制服",
    "uniform": "制服",
    "school": "制服",
    "student": "女子校生",
    "nurse": "ナース",
    "office": "OL",
    "ol": "OL",
    "4k": "4K",
    "drama": "ドラマ",
    "剧情": "ドラマ",
    "story": "ドラマ",
    "plot": "ドラマ",
}
_SEASON_DATE_RANGES = {
    "spring": ("03-01", "05-31"),
    "spr": ("03-01", "05-31"),
    "春": ("03-01", "05-31"),
    "summer": ("06-01", "08-31"),
    "sum": ("06-01", "08-31"),
    "夏": ("06-01", "08-31"),
    "autumn": ("09-01", "11-30"),
    "fall": ("09-01", "11-30"),
    "秋": ("09-01", "11-30"),
    "winter": ("12-01", "02-28"),
    "win": ("12-01", "02-28"),
    "冬": ("12-01", "02-28"),
}
_QUARTER_DATE_RANGES = {
    1: ("01-01", "03-31"),
    2: ("04-01", "06-30"),
    3: ("07-01", "09-30"),
    4: ("10-01", "12-31"),
}
_RECENCY_SORT_TOKENS = {"latest", "recent", "new", "newest", "最新", "最近", "近期", "新作"}
_OLDEST_SORT_TOKENS = {"oldest", "old", "earliest", "older", "最早", "最旧", "旧作"}
_RELATIVE_YEAR_OFFSETS = {"今年": 0, "本年": 0, "去年": -1, "昨年": -1, "前年": -2}
_SEARCH_FIELD_WEIGHTS = {
    "actress_name": 90,
    "maker_name": 76,
    "series_name": 72,
    "category_name": 68,
    "label_name": 60,
    "year": 8,
    "q": 8,
}
_PREFERENCE_FIELD_WEIGHTS = {
    "actress_name": 34,
    "maker_name": 24,
    "series_name": 22,
    "category_name": 18,
}
_METADATA_RECALL_MIN_TOKENS = 2
_METADATA_RECALL_ENTITY_PAGE_SIZE = 10
_METADATA_RECALL_RESULT_PAGE_SIZE = 20
_METADATA_RECALL_REQUEST_LIMIT = 6


def _normalize_query_text(value: str | None) -> str | None:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", " ", text.strip())
    return text or None


def _current_year() -> int:
    return date.today().year


def _tokenize_search_text(value: str | None) -> list[str]:
    text = _normalize_query_text(value)
    if not text:
        return []
    return [match.group(0) for match in _TOKEN_RE.finditer(text)]


def _canonical_content_code(prefix: str, digits: str) -> str:
    return f"{prefix.upper()}-{str(int(digits))}"


def _extract_code_from_free_text(query: str | None) -> tuple[str | None, str | None]:
    text = _normalize_query_text(query)
    if not text:
        return None, None
    match: re.Match[str] | None = None
    for candidate in _FREE_TEXT_CODE_RE.finditer(text):
        prefix, digits = candidate.groups()
        raw_candidate = candidate.group(0)
        if re.search(r"\s", raw_candidate) and len(prefix) > 5:
            continue
        if re.search(r"\s", raw_candidate) and _FREE_TEXT_YEAR_RE.fullmatch(digits):
            continue
        match = candidate
        break
    if match is None:
        return None, text
    code = _canonical_content_code(match.group(1), match.group(2))
    remaining = f"{text[:match.start()]} {text[match.end():]}"
    return code, _normalize_query_text(remaining)


def _smart_search_inputs(
    *,
    q: str | None,
    content_id: str | None,
    dvd_id: str | None,
) -> dict[str, str | None]:
    normalized_q = _normalize_query_text(q)
    normalized_content_id = _normalize_query_text(content_id)
    normalized_dvd_id = _normalize_query_text(dvd_id)
    if normalized_content_id or normalized_dvd_id:
        return {
            "q": normalized_q,
            "content_id": normalized_content_id,
            "dvd_id": normalized_dvd_id,
        }
    extracted_code, remaining_q = _extract_code_from_free_text(normalized_q)
    return {
        "q": remaining_q,
        "content_id": extracted_code,
        "dvd_id": None,
    }


def _apply_smart_inputs(
    kwargs: dict[str, Any],
    smart_inputs: dict[str, str | None],
) -> dict[str, Any]:
    next_kwargs = dict(kwargs)
    next_kwargs.update(smart_inputs)
    return next_kwargs


def _parse_compact_query_operators(query: str | None) -> tuple[dict[str, Any], str | None]:
    text = _normalize_query_text(query)
    if not text:
        return {}, None
    parsed: dict[str, Any] = {}

    def replace_field(match: re.Match[str]) -> str:
        field = match.group(1).casefold()
        value = _normalize_query_text(match.group(2))
        if not value:
            return " "
        if field in {"actor", "actress"}:
            parsed["actress_name"] = value
        elif field in {"maker", "studio"}:
            parsed["maker_name"] = value
        elif field == "series":
            parsed["series_name"] = value
        elif field in {"tag", "category"}:
            parsed["category_name"] = _SEMANTIC_CATEGORY_ALIASES.get(value.casefold(), value)
        elif field == "label":
            parsed["label_name"] = value
        elif field == "year":
            year_match = _FREE_TEXT_YEAR_RE.fullmatch(value)
            if year_match:
                parsed["year"] = int(value)
        elif field == "date":
            date_match = _FREE_TEXT_DATE_RE.fullmatch(value)
            if date_match:
                year, month, day = date_match.groups()
                exact = f"{year}-{int(month):02d}-{int(day):02d}"
                parsed["release_date_from"] = exact
                parsed["release_date_to"] = exact
        return " "

    text = _FIELD_OPERATOR_RE.sub(replace_field, text)
    range_match = _FREE_TEXT_YEAR_RANGE_RE.search(text)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        parsed["year_from"] = min(start, end)
        parsed["year_to"] = max(start, end)
        text = f"{text[:range_match.start()]} {text[range_match.end():]}"

    return parsed, _normalize_query_text(text)


def _parse_natural_query_filters(query: str | None) -> tuple[dict[str, Any], str | None]:
    text = _normalize_query_text(query)
    if not text:
        return {}, None
    parsed: dict[str, Any] = {}
    tokens = _tokenize_search_text(text)

    for token in tokens:
        if token.casefold() in _RECENCY_SORT_TOKENS:
            parsed["sort_by"] = "release_date"
            parsed["sort_order"] = "desc"
            text = re.sub(rf"\b{re.escape(token)}\b", " ", text, count=1, flags=re.IGNORECASE)
            break

    tokens = _tokenize_search_text(text)
    for token in tokens:
        if token.casefold() in _OLDEST_SORT_TOKENS:
            parsed["sort_by"] = "release_date"
            parsed["sort_order"] = "asc"
            text = re.sub(rf"\b{re.escape(token)}\b", " ", text, count=1, flags=re.IGNORECASE)
            break

    for token in tokens:
        offset = _RELATIVE_YEAR_OFFSETS.get(token)
        if offset is not None:
            parsed["year"] = _current_year() + offset
            text = re.sub(rf"\b{re.escape(token)}\b", " ", text, count=1)
            break

    tokens = _tokenize_search_text(text)
    quarter_token = next((token for token in tokens if _QUARTER_RE.fullmatch(token)), None)
    year_token = next((token for token in tokens if _FREE_TEXT_YEAR_RE.fullmatch(token)), None)
    if quarter_token and year_token:
        quarter_match = _QUARTER_RE.fullmatch(quarter_token)
        if quarter_match:
            quarter = int(quarter_match.group(1) or quarter_match.group(2))
            start, end = _QUARTER_DATE_RANGES[quarter]
            parsed["release_date_from"] = f"{year_token}-{start}"
            parsed["release_date_to"] = f"{year_token}-{end}"
            text = re.sub(rf"\b{re.escape(quarter_token)}\b", " ", text, count=1, flags=re.IGNORECASE)
            text = re.sub(rf"\b{re.escape(year_token)}\b", " ", text, count=1)

    month_match = _FREE_TEXT_YEAR_MONTH_RE.search(text)
    if month_match:
        year, month = int(month_match.group(1)), int(month_match.group(2))
        parsed["release_date_from"] = f"{year}-{month:02d}-01"
        parsed["release_date_to"] = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
        text = f"{text[:month_match.start()]} {text[month_match.end():]}"

    return parsed, _normalize_query_text(text)


def _extract_dates_from_free_text(query: str | None) -> tuple[dict[str, Any], str | None]:
    text = _normalize_query_text(query)
    if not text:
        return {}, None

    search_dates: dict[str, Any] = {}
    tokens = _tokenize_search_text(text)
    season_token = next((token for token in tokens if token.casefold() in _SEASON_DATE_RANGES), None)
    year_token = next((token for token in tokens if _FREE_TEXT_YEAR_RE.fullmatch(token)), None)
    if season_token and year_token:
        year = int(year_token)
        start, end = _SEASON_DATE_RANGES[season_token.casefold()]
        end_year = year + 1 if start > end else year
        search_dates["release_date_from"] = f"{year}-{start}"
        search_dates["release_date_to"] = f"{end_year}-{end}"
        text = re.sub(rf"\b{re.escape(season_token)}\b", " ", text, count=1, flags=re.IGNORECASE)
        text = re.sub(rf"\b{re.escape(year_token)}\b", " ", text, count=1)
        return search_dates, _normalize_query_text(text)

    def replace_date(match: re.Match[str]) -> str:
        year, month, day = match.groups()
        search_dates["release_date_from"] = f"{year}-{int(month):02d}-{int(day):02d}"
        search_dates["release_date_to"] = f"{year}-{int(month):02d}-{int(day):02d}"
        search_dates["year"] = int(year)
        return " "

    text = _FREE_TEXT_DATE_RE.sub(replace_date, text)

    if "year" not in search_dates:
        year_match = _FREE_TEXT_YEAR_RE.search(text)
        if year_match:
            search_dates["year"] = int(year_match.group(1))
            text = f"{text[:year_match.start()]} {text[year_match.end():]}"

    return search_dates, _normalize_query_text(text)


def _entity_name(entity: dict[str, Any]) -> str:
    for key in (
        "actress_name",
        "display_name",
        "name_ja",
        "name",
        "name_en",
        "name_romaji",
        "name_kana",
        "alias",
        "title",
    ):
        value = _normalize_query_text(entity.get(key))
        if value:
            return value
    return ""


def _entity_names(entity: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in (
        "actress_name",
        "display_name",
        "name_ja",
        "name",
        "name_en",
        "name_romaji",
        "name_kana",
        "alias",
        "title",
    ):
        value = _normalize_query_text(entity.get(key))
        if value and value not in names:
            names.append(value)
    return names


def _normal_key(value: Any) -> str:
    return re.sub(r"[\s_\-・.]+", "", str(value or "").casefold())


def _is_ordered_subsequence(needle: str, haystack: str) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    position = 0
    for char in haystack:
        if char == needle[position]:
            position += 1
            if position == len(needle):
                return True
    return False


def _compact_name_keys(name_tokens: list[str]) -> set[str]:
    keys = {token for token in name_tokens if token}
    latin_tokens = [token for token in name_tokens if re.fullmatch(r"[a-z0-9]+", token)]
    initials = "".join(token[0] for token in latin_tokens if token)
    if len(initials) >= 2:
        keys.add(initials)
    for token in latin_tokens:
        consonants = _LATIN_VOWELS_RE.sub("", token)
        if len(consonants) >= 2:
            keys.add(consonants)
    return keys


def _edit_distance_within(left: str, right: str, limit: int = 1) -> bool:
    if abs(len(left) - len(right)) > limit:
        return False
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        row_min = current[0]
        for j, right_char in enumerate(right, 1):
            cost = 0 if left_char == right_char else 1
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + cost,
            ))
            row_min = min(row_min, current[-1])
        if row_min > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _is_fuzzy_token_match(query_token: str, name_token: str) -> bool:
    if not query_token or not name_token:
        return False
    if query_token in name_token or name_token in query_token:
        return True
    if 2 <= len(query_token) <= 5 and len(name_token) >= len(query_token) + 1 and _is_ordered_subsequence(query_token, name_token):
        return True
    if len(query_token) >= 5 and len(name_token) >= 5 and _edit_distance_within(query_token, name_token, 1):
        return True
    return False


def _entity_matches_query(entity: dict[str, Any], query: str | None) -> bool:
    query_tokens = {_normal_key(token) for token in _tokenize_search_text(query)}
    query_tokens.discard("")
    if not query_tokens:
        return False
    for name in _entity_names(entity):
        normalized_name = _normal_key(name)
        if any(token and token in normalized_name for token in query_tokens):
            return True
        name_token_list = [_normal_key(token) for token in _tokenize_search_text(name)]
        name_tokens = set(name_token_list)
        if query_tokens.intersection(name_tokens):
            return True
        compact_keys = _compact_name_keys(name_token_list)
        if query_tokens.intersection(compact_keys):
            return True
        if any(_is_fuzzy_token_match(query_token, name_token) for query_token in query_tokens for name_token in name_tokens):
            return True
    return False


def _entity_items(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, dict):
        data = result.get("data")
        return data if isinstance(data, list) else []
    return result if isinstance(result, list) else []


async def _safe_entity_candidates(
    loader: Any,
    query: str,
    *,
    limit: int = 2,
    cache_bypass: bool = False,
) -> list[dict[str, Any]]:
    try:
        result = await loader(
            q=query,
            page=1,
            page_size=_METADATA_RECALL_ENTITY_PAGE_SIZE,
            cache_bypass=cache_bypass,
        )
    except TypeError:
        try:
            result = await loader(q=query, cache_bypass=cache_bypass)
        except TypeError:
            try:
                result = await loader(q=query)
            except Exception:
                return []
        except Exception:
            return []
    except Exception:
        return []
    matches = [
        item for item in _entity_items(result)
        if isinstance(item, dict) and _entity_matches_query(item, query)
    ]
    return matches[:limit]


def _semantic_category_candidates(query: str | None) -> list[str]:
    candidates: list[str] = []
    for token in _tokenize_search_text(query):
        mapped = _SEMANTIC_CATEGORY_ALIASES.get(token.casefold())
        if mapped and mapped not in candidates:
            candidates.append(mapped)
    return candidates[:3]


def _has_semantic_category_alias(query: str | None) -> bool:
    for token in _tokenize_search_text(query):
        mapped = _SEMANTIC_CATEGORY_ALIASES.get(token.casefold())
        if mapped and _normal_key(mapped) != _normal_key(token):
            return True
    return False


def _video_key(item: dict[str, Any]) -> str:
    for key in ("content_id", "dvd_id", "display_code", "canonical_code"):
        value = _normalize_query_text(item.get(key))
        if value:
            return _normal_key(value)
    return ""


def _preference_values(value: str | None) -> list[str]:
    text = _normalize_query_text(value)
    if not text:
        return []
    values: list[str] = []
    for part in re.split(r"[,;/|]+|\s{2,}", text):
        item = _normalize_query_text(part)
        if item and item not in values:
            values.append(item)
    if len(values) == 1 and " " in values[0] and not re.search(r"[\u3040-\u30ff\u3400-\u9fff]", values[0]):
        values = [token for token in values[0].split(" ") if token]
    return values[:4]


def _item_field_values(item: dict[str, Any], field: str) -> list[str]:
    values: list[str] = []
    direct = _normalize_query_text(item.get(field))
    if direct:
        values.append(direct)
    collection_name = {
        "actress_name": "actresses",
        "category_name": "categories",
    }.get(field)
    collection = item.get(collection_name) if collection_name else None
    if isinstance(collection, list):
        for entity in collection:
            if isinstance(entity, dict):
                for key in ("name_ja", "name", "actress_name", "display_name", "name_en", "name_romaji"):
                    value = _normalize_query_text(entity.get(key))
                    if value:
                        values.append(value)
            else:
                value = _normalize_query_text(entity)
                if value:
                    values.append(value)
    return values


def _apply_preference_ranking(
    result: dict[str, Any],
    preferences: dict[str, list[str]],
) -> dict[str, Any]:
    items = result.get("data") if isinstance(result, dict) else None
    if not isinstance(items, list) or not items or not any(preferences.values()):
        return result

    def preference_score(item: dict[str, Any]) -> int:
        score = 0
        for field, preferred_values in preferences.items():
            if not preferred_values:
                continue
            item_values = [_normal_key(value) for value in _item_field_values(item, field)]
            for preferred in preferred_values:
                preferred_key = _normal_key(preferred)
                if preferred_key and any(preferred_key in item_value or item_value in preferred_key for item_value in item_values):
                    score += _PREFERENCE_FIELD_WEIGHTS.get(field, 0)
                    break
        return score

    ranked = [
        (preference_score(item), index, item)
        for index, item in enumerate(items)
        if isinstance(item, dict)
    ]
    if not any(score for score, _, _ in ranked):
        return result
    next_result = dict(result)
    next_result["data"] = [
        item
        for score, _index, item in sorted(ranked, key=lambda row: (-row[0], row[1]))
    ]
    return next_result


def _merge_ranked_results(
    result: dict[str, Any],
    recalls: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    merged: dict[str, dict[str, Any]] = {}
    order: dict[str, int] = {}
    scores: dict[str, int] = {}

    for source_index, (field, response) in enumerate(recalls):
        items = response.get("data") if isinstance(response, dict) else None
        if not isinstance(items, list):
            continue
        weight = _SEARCH_FIELD_WEIGHTS.get(field, 0)
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            key = _video_key(item)
            if not key:
                continue
            if key not in merged:
                merged[key] = item
                order[key] = source_index * 1000 + item_index
            scores[key] = scores.get(key, 0) + weight

    if not merged:
        return result

    def sort_key(item: dict[str, Any]) -> tuple[int, str, int]:
        key = _video_key(item)
        release_date = str(item.get("release_date") or "")
        return (-scores.get(key, 0), release_date, order.get(key, 0))

    data = sorted(merged.values(), key=sort_key)
    next_result = dict(result)
    next_result["data"] = data
    next_result["total_count"] = len(data)
    next_result["total_pages"] = 1 if data else 0
    return next_result


def _search_has_structured_filters(kwargs: dict[str, Any]) -> bool:
    return any(
        kwargs.get(key)
        for key in (
            "content_id",
            "dvd_id",
            "maker_id",
            "maker_name",
            "series_id",
            "series_name",
            "actress_id",
            "actress_name",
            "category_id",
            "category_name",
            "label_id",
            "label_name",
            "site_id",
            "service_code",
        )
    )


def _base_recall_kwargs(search_kwargs: dict[str, Any]) -> dict[str, Any]:
    base = {
        key: value
        for key, value in search_kwargs.items()
        if key in {
            "service_code",
            "sort_by",
            "sort_order",
            "include_total",
            "page_size",
            "cache_bypass",
            "year",
            "year_from",
            "year_to",
            "release_date_from",
            "release_date_to",
        } and value is not None
    }
    base["page_size"] = max(1, min(int(base.get("page_size") or _METADATA_RECALL_RESULT_PAGE_SIZE), _METADATA_RECALL_RESULT_PAGE_SIZE))
    return base


def _should_use_metadata_recall(search_kwargs: dict[str, Any], q: str | None) -> bool:
    if search_kwargs.get("random") or int(search_kwargs.get("page") or 1) != 1:
        return False
    if _search_has_structured_filters({**search_kwargs, "q": None}):
        return False
    return len(_tokenize_search_text(q)) >= _METADATA_RECALL_MIN_TOKENS or _has_semantic_category_alias(q)


async def _smart_search_videos(
    client: Any,
    search_kwargs: dict[str, Any],
    *,
    include_diagnostics: bool = False,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "metadata_recall": False,
        "recall_fields": [],
        "semantic_categories": [],
        "recall_request_count": 0,
        "recall_request_limit": _METADATA_RECALL_REQUEST_LIMIT,
    }

    def with_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
        if not include_diagnostics:
            return result
        next_result = dict(result)
        next_result["search_diagnostics"] = diagnostics
        return next_result

    q = _normalize_query_text(search_kwargs.get("q"))
    if not q or not _should_use_metadata_recall(search_kwargs, q):
        return with_diagnostics(await client.search_videos(**search_kwargs))

    date_filters, remaining_q = _extract_dates_from_free_text(q)
    q_for_recall = remaining_q or q
    semantic_categories = _semantic_category_candidates(q_for_recall)
    if len(_tokenize_search_text(q_for_recall)) < _METADATA_RECALL_MIN_TOKENS and not semantic_categories:
        return with_diagnostics(await client.search_videos(**search_kwargs))
    base_kwargs = {
        **search_kwargs,
        "q": q_for_recall,
        **date_filters,
        "page": 1,
    }
    diagnostics["metadata_recall"] = True

    recalls: list[tuple[str, dict[str, Any]]] = []
    primary = await client.search_videos(**base_kwargs)
    recalls.append(("q", primary))

    entity_candidates = await asyncio.gather(
        _safe_entity_candidates(client.list_actresses, q_for_recall, limit=2, cache_bypass=bool(search_kwargs.get("cache_bypass"))),
        _safe_entity_candidates(client.list_makers, q_for_recall, limit=2, cache_bypass=bool(search_kwargs.get("cache_bypass"))),
        _safe_entity_candidates(client.list_series, q_for_recall, limit=2, cache_bypass=bool(search_kwargs.get("cache_bypass"))),
        _safe_entity_candidates(client.list_categories, q_for_recall, limit=2, cache_bypass=bool(search_kwargs.get("cache_bypass"))),
        _safe_entity_candidates(client.list_labels, q_for_recall, limit=1, cache_bypass=bool(search_kwargs.get("cache_bypass"))),
    )
    actresses, makers, series, categories, labels = entity_candidates
    category_names = [_entity_name(item) for item in categories]
    for semantic_name in semantic_categories:
        if semantic_name not in category_names:
            category_names.append(semantic_name)
    diagnostics["semantic_categories"] = category_names[:3]

    base = _base_recall_kwargs(base_kwargs)
    base["page"] = 1
    recall_requests: list[tuple[str, dict[str, Any]]] = []
    for entity in actresses:
        name = _entity_name(entity)
        if name:
            recall_requests.append(("actress_name", {**base, "q": None, "actress_name": name}))
    for entity in makers:
        name = _entity_name(entity)
        if name:
            recall_requests.append(("maker_name", {**base, "q": None, "maker_name": name}))
    for entity in series:
        name = _entity_name(entity)
        if name:
            recall_requests.append(("series_name", {**base, "q": None, "series_name": name}))
    for name in category_names[:3]:
        if name:
            recall_requests.append(("category_name", {**base, "q": None, "category_name": name}))
    for entity in labels:
        name = _entity_name(entity)
        if name:
            recall_requests.append(("label_name", {**base, "q": None, "label_name": name}))
    if date_filters.get("year"):
        recall_requests.append(("year", {**base, "q": None, "year": date_filters["year"]}))

    recall_requests = recall_requests[:_METADATA_RECALL_REQUEST_LIMIT]
    diagnostics["recall_request_count"] = len(recall_requests)
    diagnostics["recall_fields"] = [field for field, _kwargs in recall_requests]

    if recall_requests:
        responses = await asyncio.gather(
            *(client.search_videos(**kwargs) for _, kwargs in recall_requests),
            return_exceptions=True,
        )
        for (field, _kwargs), response in zip(recall_requests, responses):
            if isinstance(response, dict):
                recalls.append((field, response))

    return with_diagnostics(_merge_ranked_results(primary, recalls))


async def _apply_translation_to_video(data: dict, *, allow_network: bool = True) -> dict:
    """对单条影片数据应用翻译"""
    content_id = data.get("content_id") or data.get("dvd_id", "").replace("-", "").replace("_", "").lower()
    if not content_id:
        return data
    return await get_translator_service().translate_video(content_id, data, allow_network=allow_network)


async def _apply_translation_to_videos(items: list[dict], *, allow_network: bool = False) -> list[dict]:
    return await get_translator_service().translate_videos(items, allow_network=allow_network)


_CANONICAL_CODE_RE = re.compile(r"^([A-Z]+)-?([0-9]+)$")


def _exact_code_variant_candidates(code: str | None) -> tuple[list[str], list[str]]:
    raw = str(code or "").strip().upper()
    match = _CANONICAL_CODE_RE.match(raw)
    if not match:
        return [], []
    prefix, digits = match.groups()
    if len(prefix) < 3:
        return [], []
    number = str(int(digits))
    padded = number.zfill(max(5, len(digits)))
    dashed = f"{prefix}-{number}"
    return [
        f"TK{dashed}",
        f"{dashed}BOD",
        f"{dashed}DOD",
        f"{dashed}RDOD",
        f"4{prefix}{number}",
    ], [f"{prefix.lower()}{padded}"]


async def _expand_exact_code_variants(
    client: Any,
    result: dict[str, Any],
    *,
    content_id: str | None,
    dvd_id: str | None,
    cache_bypass: bool,
) -> dict[str, Any]:
    items = result.get("data")
    if not isinstance(items, list) or len(items) != 1:
        return result
    search_code = content_id or dvd_id
    dvd_candidates, digital_candidates = _exact_code_variant_candidates(search_code)
    if not dvd_candidates and not digital_candidates:
        return result

    seen = {str(items[0].get("content_id") or items[0].get("dvd_id") or "").lower()}
    expanded = list(items)

    def add_item(item: dict[str, Any]) -> None:
        key = str(item.get("content_id") or item.get("dvd_id") or "").lower()
        if not key or key in seen:
            return
        seen.add(key)
        expanded.append(item)

    if dvd_candidates:
        try:
            found_by_dvd = await client.batch_lookup_by_dvd_id(dvd_candidates)
        except Exception as exc:
            logger.warning("Failed to batch lookup exact code variants for %s: %s", search_code, exc)
        else:
            if isinstance(found_by_dvd, dict):
                for candidate in dvd_candidates:
                    item = found_by_dvd.get(candidate)
                    if isinstance(item, dict):
                        add_item(item)

    if digital_candidates:
        try:
            found_digital = await client.batch_get_videos(digital_candidates)
        except Exception as exc:
            logger.warning("Failed to batch get digital exact code variants for %s: %s", search_code, exc)
        else:
            if isinstance(found_digital, list):
                for item in found_digital:
                    if isinstance(item, dict):
                        add_item(item)

    if len(expanded) > len(items):
        result = dict(result)
        result["data"] = expanded
    return result

@router.get("/search")
async def search_videos(
    q: Optional[str] = Query(None),
    content_id: Optional[str] = Query(None),
    dvd_id: Optional[str] = Query(None),
    maker_id: Optional[int] = Query(None),
    maker_name: Optional[str] = Query(None),
    series_id: Optional[int] = Query(None),
    series_name: Optional[str] = Query(None),
    actress_id: Optional[int] = Query(None),
    actress_name: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    category_name: Optional[str] = Query(None),
    label_id: Optional[int] = Query(None),
    label_name: Optional[str] = Query(None),
    site_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None, description="发行年份"),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    runtime_min: Optional[int] = Query(None),
    runtime_max: Optional[int] = Query(None),
    release_date_from: Optional[str] = Query(None),
    release_date_to: Optional[str] = Query(None),
    service_code: Optional[str] = Query(None, description="影片类型：digital/mono/rental/ebook"),
    sort_by: Optional[str] = Query(None, description="排序字段，如 release_date"),
    sort_order: Optional[str] = Query(None, description="asc 或 desc"),
    random: Optional[str] = Query(None, description="随机排序"),
    include_total: Optional[bool] = Query(None),
    variant_mode: str = Query("grouped", pattern="^(grouped|flat)$"),
    variant_scope: str = Query("page", pattern="^(page|indexed)$"),
    include_variant_explanations: bool = Query(False),
    include_search_diagnostics: bool = Query(False),
    preferred_actresses: Optional[str] = Query(None),
    preferred_makers: Optional[str] = Query(None),
    preferred_series: Optional[str] = Query(None),
    preferred_categories: Optional[str] = Query(None),
    cache_control: str | None = Query(None, alias="cache"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    _include_total = None if isinstance(include_total, QueryParam) else include_total
    _variant_mode = "grouped" if isinstance(variant_mode, QueryParam) else variant_mode
    _variant_scope = "page" if isinstance(variant_scope, QueryParam) else variant_scope
    _include_variant_explanations = False if isinstance(include_variant_explanations, QueryParam) else bool(include_variant_explanations)
    _include_search_diagnostics = False if isinstance(include_search_diagnostics, QueryParam) else bool(include_search_diagnostics)
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
    smart_inputs = _smart_search_inputs(q=q, content_id=content_id, dvd_id=dvd_id)
    operator_cache_filters, operator_cache_q = _parse_compact_query_operators(smart_inputs["q"])
    natural_cache_filters, natural_cache_q = _parse_natural_query_filters(operator_cache_q)
    cache_params = {
        "q": natural_cache_q,
        "content_id": smart_inputs["content_id"],
        "dvd_id": smart_inputs["dvd_id"],
        "maker_id": maker_id,
        "maker_name": maker_name or operator_cache_filters.get("maker_name"),
        "series_id": series_id,
        "series_name": series_name or operator_cache_filters.get("series_name"),
        "actress_id": actress_id,
        "actress_name": actress_name or operator_cache_filters.get("actress_name"),
        "category_id": category_id,
        "category_name": category_name or operator_cache_filters.get("category_name"),
        "label_id": label_id,
        "label_name": label_name or operator_cache_filters.get("label_name"),
        "site_id": site_id,
        "year": year or operator_cache_filters.get("year") or natural_cache_filters.get("year"),
        "year_from": year_from or operator_cache_filters.get("year_from") or natural_cache_filters.get("year_from"),
        "year_to": year_to or operator_cache_filters.get("year_to") or natural_cache_filters.get("year_to"),
        "runtime_min": runtime_min,
        "runtime_max": runtime_max,
        "release_date_from": release_date_from or operator_cache_filters.get("release_date_from") or natural_cache_filters.get("release_date_from"),
        "release_date_to": release_date_to or operator_cache_filters.get("release_date_to") or natural_cache_filters.get("release_date_to"),
        "service_code": service_code,
        "sort_by": sort_by or natural_cache_filters.get("sort_by"),
        "sort_order": sort_order or natural_cache_filters.get("sort_order"),
        "include_total": _include_total,
        "variant_mode": _variant_mode,
        "variant_scope": _variant_scope,
        "include_variant_explanations": _include_variant_explanations,
        "include_search_diagnostics": _include_search_diagnostics,
        "preferred_actresses": preferred_actresses,
        "preferred_makers": preferred_makers,
        "preferred_series": preferred_series,
        "preferred_categories": preferred_categories,
        "page": page,
        "page_size": page_size,
    }

    async def produce():
        client = get_info_client()
        operator_filters, operator_q = _parse_compact_query_operators(smart_inputs["q"])
        natural_filters, natural_q = _parse_natural_query_filters(operator_q)
        effective_smart_inputs = {
            **smart_inputs,
            "q": natural_q,
        }
        search_kwargs = _apply_smart_inputs(
            {
                "q": q,
                "content_id": content_id,
                "dvd_id": dvd_id,
                "maker_id": maker_id,
                "maker_name": maker_name,
                "series_id": series_id,
                "series_name": series_name,
                "actress_id": actress_id,
                "actress_name": actress_name,
                "category_id": category_id,
                "category_name": category_name,
                "label_id": label_id,
                "label_name": label_name,
                "site_id": site_id,
                "year": year,
                "year_from": year_from,
                "year_to": year_to,
                "runtime_min": runtime_min,
                "runtime_max": runtime_max,
                "release_date_from": release_date_from,
                "release_date_to": release_date_to,
                "service_code": service_code,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "random": random,
                "include_total": _include_total,
                "page": page,
                "page_size": page_size,
            },
            effective_smart_inputs,
        )
        for key, value in {**operator_filters, **natural_filters}.items():
            if search_kwargs.get(key) in (None, ""):
                search_kwargs[key] = value
        if cache_bypass:
            search_kwargs["cache_bypass"] = True
        result = await _smart_search_videos(client, search_kwargs, include_diagnostics=_include_search_diagnostics)
        if result.get("data"):
            result = _apply_preference_ranking(
                result,
                {
                    "actress_name": _preference_values(preferred_actresses),
                    "maker_name": _preference_values(preferred_makers),
                    "series_name": _preference_values(preferred_series),
                    "category_name": _preference_values(preferred_categories),
                },
            )
            if _variant_mode == "grouped" and (smart_inputs["content_id"] or smart_inputs["dvd_id"]):
                result = await _expand_exact_code_variants(
                    client,
                    result,
                    content_id=smart_inputs["content_id"],
                    dvd_id=smart_inputs["dvd_id"],
                    cache_bypass=cache_bypass,
                )
            result["data"] = await _apply_translation_to_videos(result["data"], allow_network=False)
            result["data"] = enrich_video_variants(
                result["data"],
                variant_mode=_variant_mode,
                include_explanations=_include_variant_explanations,
            )
            if _variant_mode == "grouped" and _variant_scope == "indexed" and not (smart_inputs["content_id"] or smart_inputs["dvd_id"]):
                result["data"] = apply_indexed_variant_groups(
                    result["data"],
                    include_explanations=_include_variant_explanations,
                )
        return result

    if random:
        if _include_total is False:
            random_cache_params = dict(cache_params)
            random_cache_params["random"] = random
            return await cache.get_or_set_response(
                _RANDOM_CACHE_NAMESPACE,
                random_cache_params,
                produce,
                ttl=_RANDOM_CACHE_TTL,
                bypass=cache_bypass,
            )
        return await produce()
    return await cache.get_or_set_response(
        _SEARCH_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_SEARCH_CACHE_TTL,
        bypass=cache_bypass,
    )

@router.get("")
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_total: bool = Query(False),
    cache_control: str | None = Query(None, alias="cache"),
) -> Dict[str, Any]:
    _include_total = False if isinstance(include_total, QueryParam) else bool(include_total)
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
    cache_params = {"page": page, "page_size": page_size, "include_total": _include_total}

    async def produce():
        client = get_info_client()
        if cache_bypass:
            result = await client.list_videos(
                page=page,
                page_size=page_size,
                include_total=_include_total,
                cache_bypass=True,
            )
        else:
            result = await client.list_videos(page=page, page_size=page_size, include_total=_include_total)
        if result.get("data"):
            result["data"] = await _apply_translation_to_videos(result["data"], allow_network=False)
        return result

    return await cache.get_or_set_response(
        _LIST_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_LIST_CACHE_TTL,
        bypass=cache_bypass,
    )

@router.get("/{content_id}")
async def get_video(
    content_id: str,
    service_code: Optional[str] = Query(None),
    cache_control: str | None = Query(None, alias="cache"),
) -> Dict[str, Any]:
    _service_code = None if isinstance(service_code, QueryParam) else service_code
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
    cache_params = {
        "content_id": _content_cache_id(content_id),
        "service_code": _service_code,
    }

    async def produce():
        client = get_info_client()
        if cache_bypass:
            data = await client.get_video(content_id, service_code=_service_code, cache_bypass=True)
        else:
            data = await client.get_video(content_id, service_code=_service_code)
        return await _apply_translation_to_video(data, allow_network=False)

    return await cache.get_or_set_response(
        _DETAIL_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_DETAIL_CACHE_TTL,
        bypass=cache_bypass,
    )
