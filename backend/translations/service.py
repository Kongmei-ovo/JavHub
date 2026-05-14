from __future__ import annotations

import json
import logging
from typing import Any

from config import config
from database import (
    get_cached_translation,
    get_translation,
    upsert_cached_translation,
)
from translations.providers import (
    DeepLProvider,
    GoogleFreeProvider,
    MappingProvider,
    MicrosoftTranslatorProvider,
    OpenAICompatibleProvider,
    TranslationProvider,
    TranslationRequest,
)

logger = logging.getLogger(__name__)


def translate_item(original: str, mapping: dict[str, str] | None) -> str:
    if not original or not mapping:
        return original
    return mapping.get(original, original)


def _entity_scope(entity_type: str, entity_id: Any | None, fallback: str = "") -> str:
    if entity_id is not None and entity_id != "":
        return f"{entity_type}:{entity_id}"
    return f"{entity_type}:name:{fallback}" if fallback else entity_type


def _first_text(entity: dict, keys: list[str]) -> tuple[str | None, str | None]:
    for key in keys:
        value = entity.get(key)
        if isinstance(value, str) and value.strip():
            return key, value
    return None, None


def _json_array(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str):
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _dump_json_array(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _normalize_content_id(value: Any) -> str:
    return str(value or "").replace("-", "").replace("_", "").lower()


def _content_translation(content_id: str) -> dict | None:
    direct = get_translation(content_id)
    if direct:
        return direct
    normalized = _normalize_content_id(content_id)
    if normalized and normalized != content_id:
        return get_translation(normalized)
    return None


class TranslatorService:
    LOCAL_PROVIDERS = {"cache", "mapping"}

    def __init__(self, settings: dict[str, Any] | None = None, *, reuse_clients: bool = False):
        self.settings = settings if settings is not None else config.translation
        self._uses_injected_settings = settings is not None
        self.mapping_provider = MappingProvider()
        self.reuse_clients = reuse_clients
        self._provider_cache: dict[str, TranslationProvider] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.settings.get("enabled", True))

    @property
    def target_language(self) -> str:
        return str(self.settings.get("target_language") or "zh-CN")

    @property
    def provider_order(self) -> list[str]:
        order = self.settings.get("provider_order")
        if not isinstance(order, list):
            return ["cache", "mapping", "openai_compatible"]
        return [str(item) for item in order if str(item).strip()]

    def _provider(self, name: str) -> TranslationProvider | None:
        if self.reuse_clients and name in self._provider_cache:
            return self._provider_cache[name]
        if name == "mapping":
            provider = self.mapping_provider
        elif name == "google_free":
            provider = GoogleFreeProvider(self.settings.get("google_free", {}) or {}, reuse_client=self.reuse_clients)
        elif name == "deepl":
            provider = DeepLProvider(self.settings.get("deepl", {}) or {})
        elif name == "microsoft":
            provider = MicrosoftTranslatorProvider(self.settings.get("microsoft", {}) or {})
        elif name == "openai_compatible":
            local_settings = self.settings.get("openai_compatible", {}) or {}
            if self._uses_injected_settings and any(local_settings.get(key) for key in ("base_url", "api_key", "model")):
                provider = OpenAICompatibleProvider(local_settings)
            else:
                provider = OpenAICompatibleProvider(config.openai_compatible)
        else:
            return None
        if self.reuse_clients:
            self._provider_cache[name] = provider
        return provider

    async def close(self) -> None:
        for provider in self._provider_cache.values():
            close = getattr(provider, "aclose", None)
            if close:
                await close()
        self._provider_cache.clear()

    async def translate_text(
        self,
        text: str | None,
        *,
        scope: str,
        mapping: dict[str, str] | None = None,
        context: str | None = None,
        use_ai: bool = True,
        persist_ai: bool = True,
        provider_order: list[str] | None = None,
        allow_network: bool = True,
        return_original: bool = True,
    ) -> str | None:
        if not text:
            return text
        source = str(text).strip()
        if not source or not self.enabled:
            return text

        request = TranslationRequest(
            text=source,
            scope=scope,
            target_language=self.target_language,
            context=context,
            mapping=mapping,
        )

        for provider_name in provider_order or self.provider_order:
            if provider_name == "cache":
                cached = get_cached_translation(scope, source)
                if cached and cached.get("translated_text"):
                    return cached["translated_text"]
                continue

            if not allow_network and provider_name not in self.LOCAL_PROVIDERS:
                continue

            if provider_name == "openai_compatible" and not use_ai:
                continue

            provider = self._provider(provider_name)
            if not provider or not provider.supports(request):
                continue
            result = await provider.translate(request)
            if not result or not result.translated_text:
                continue
            translated = result.translated_text.strip()
            if result.cacheable and persist_ai and translated:
                upsert_cached_translation(scope, source, translated, result.provider, result.model)
            return translated

        return text if return_original else None

    async def translate_entities(
        self,
        items: list[dict],
        *,
        entity_type: str,
        keys: list[str],
        use_ai: bool = False,
        allow_network: bool = True,
    ) -> list[dict]:
        for item in items:
            if not isinstance(item, dict):
                continue
            key, original = _first_text(item, keys)
            if not key or not original:
                continue
            entity_id = item.get("id")
            trans = get_translation(_entity_scope(entity_type, entity_id))
            mapping = trans.get(entity_type, {}) if trans else {}
            translated = await self.translate_text(
                original,
                scope=_entity_scope(entity_type, entity_id, original),
                mapping=mapping,
                context=f"{entity_type} name",
                use_ai=use_ai,
                persist_ai=use_ai,
                allow_network=allow_network,
            )
            if translated and translated != original:
                item[f"{key}_translated"] = translated
        return items

    async def translate_video(
        self,
        content_id: str,
        data: dict,
        *,
        use_ai: bool = False,
        allow_network: bool = True,
    ) -> dict:
        if not content_id or not data:
            return data
        result = dict(data)
        content_mapping = _content_translation(content_id)

        if isinstance(result.get("actresses"), list):
            await self.translate_entities(
                result["actresses"],
                entity_type="actress",
                keys=["name_ja", "name_en", "name_kanji", "name_romaji", "name"],
                use_ai=use_ai,
                allow_network=allow_network,
            )

        if isinstance(result.get("categories"), list):
            for cat in result["categories"]:
                if not isinstance(cat, dict):
                    continue
                key, original = _first_text(cat, ["name_ja", "name_en", "name"])
                if not key or not original:
                    continue
                cat_id = cat.get("id")
                trans = get_translation(_entity_scope("category", cat_id))
                cat_map = trans.get("category", {}) if trans else {}
                if not cat_map and content_mapping:
                    cat_map = content_mapping.get("category", {})
                translated = await self.translate_text(
                    original,
                    scope=_entity_scope("category", cat_id, original),
                    mapping=cat_map,
                    context="category name",
                    use_ai=use_ai,
                    persist_ai=use_ai,
                    allow_network=allow_network,
                )
                if translated and translated != original:
                    cat[f"{key}_translated"] = translated

        for entity_type, keys in (
            ("series", ["name"]),
            ("maker", ["name_ja", "name_en", "name"]),
            ("label", ["name_ja", "name_en", "name"]),
        ):
            entity = result.get(entity_type)
            if not isinstance(entity, dict) or not entity:
                continue
            key, original = _first_text(entity, keys)
            if not key or not original:
                continue
            entity_id = entity.get("id")
            trans = get_translation(_entity_scope(entity_type, entity_id))
            mapping = trans.get(entity_type, {}) if trans else {}
            if not mapping and content_mapping:
                mapping = content_mapping.get(entity_type, {})
            translated = await self.translate_text(
                original,
                scope=_entity_scope(entity_type, entity_id, original),
                mapping=mapping,
                context=f"{entity_type} name",
                use_ai=use_ai,
                persist_ai=use_ai,
                allow_network=allow_network,
            )
            if translated and translated != original:
                entity[f"{key}_translated"] = translated

        title_map = content_mapping.get("title", {}) if content_mapping else {}
        for title_key in ["title_en", "title_ja"]:
            original = result.get(title_key)
            if not original:
                continue
            translated = await self.translate_text(
                original,
                scope=f"title:{content_id}:{title_key}",
                mapping=title_map,
                context="video title",
                use_ai=use_ai,
                persist_ai=use_ai,
                allow_network=allow_network,
            )
            if translated and translated != original:
                result[f"{title_key}_translated"] = translated

        if result.get("summary"):
            summary = result.get("summary")
            translated = await self.translate_text(
                summary,
                scope=f"summary:{content_id}",
                context="video summary",
                use_ai=True,
                persist_ai=True,
                allow_network=allow_network,
            )
            if translated and translated != summary:
                result["summary_translated"] = translated

        return result

    async def translate_metadata(self, content_id: str, data: dict) -> dict:
        if not content_id or not isinstance(data, dict) or not data.get("summary"):
            return data
        result = dict(data)
        try:
            translated = await self.translate_text(
                result.get("summary"),
                scope=f"summary:{content_id}",
                context="video summary",
                use_ai=True,
                persist_ai=True,
            )
        except Exception as exc:
            logger.warning("Metadata translation failed for %s: %s", content_id, exc)
            return result
        if translated and translated != result.get("summary"):
            result["summary_translated"] = translated
        return result

    async def translate_supplement_sources(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        result = dict(data)
        fields = []
        for field in result.get("chosen_fields", []) or []:
            if not isinstance(field, dict):
                fields.append(field)
                continue
            fields.append(await self._translate_supplement_field(dict(field)))
        result["chosen_fields"] = fields
        return result

    async def _translate_supplement_field(self, field: dict) -> dict:
        name = field.get("field_name")
        value = field.get("field_value")
        if not isinstance(name, str) or not isinstance(value, str) or not value.strip():
            return field

        single_context = {
            "title": "video title",
            "summary": "video summary",
            "description": "video summary",
            "maker_name": "maker name",
            "label_name": "label name",
            "series_name": "series name",
        }
        array_context = {
            "category_names": "category name",
            "actor_names": "actress name",
        }

        if name in single_context:
            if value.strip() == "----":
                return field
            translated = await self.translate_text(
                value,
                scope=f"supplement:{name}:{value}",
                context=single_context[name],
                use_ai=True,
                persist_ai=True,
            )
            if translated and translated != value:
                field["field_value_translated"] = translated
            return field

        if name in array_context:
            translated_values = []
            changed = False
            for item in _json_array(value):
                translated = await self.translate_text(
                    item,
                    scope=f"supplement:{name}:{item}",
                    context=array_context[name],
                    use_ai=True,
                    persist_ai=True,
                )
                translated_values.append(translated or item)
                changed = changed or bool(translated and translated != item)
            if translated_values and changed:
                field["field_value_translated"] = _dump_json_array(translated_values)
            return field

        return field


def get_translator_service() -> TranslatorService:
    return TranslatorService()


async def apply_translation(content_id: str, data: dict) -> dict:
    return await get_translator_service().translate_video(content_id, data, use_ai=False)
