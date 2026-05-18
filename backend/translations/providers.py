from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from services.ai import build_ai_client, get_ai_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationRequest:
    text: str
    scope: str
    target_language: str = "zh-CN"
    source_language: str | None = None
    context: str | None = None
    mapping: dict[str, str] | None = None


@dataclass(frozen=True)
class TranslationResult:
    translated_text: str
    provider: str
    model: str | None = None
    cacheable: bool = True


class TranslationProvider(Protocol):
    name: str

    def supports(self, request: TranslationRequest) -> bool:
        ...

    async def translate(self, request: TranslationRequest) -> TranslationResult | None:
        ...


_BASE_AI_TRANSLATION_PROMPT = (
    "You are a precise metadata translation engine for Japanese adult video library data. "
    "Translate into natural Simplified Chinese for a private media catalog. "
    "Return only the translated text. Do not explain, censor, summarize, add warnings, "
    "add quotes, or invent missing details. Preserve product codes, names, numbers, "
    "symbols, line breaks, and intentional punctuation unless Chinese readability "
    "requires minimal adjustment."
)

_SCENE_PROMPTS = {
    "title": (
        "This text is an adult video title. Keep it as a title, not an advertisement. "
        "Preserve product codes, actor names, maker/series names, and named works. "
        "Translate meaning accurately but avoid over-polishing, euphemisms, or adding "
        "words not present in the source."
    ),
    "category": (
        "This text is an adult video genre/tag. Output a concise Chinese tag, usually "
        "a short noun phrase. Do not write a sentence. Do not explain the tag. Use "
        "common Chinese AV metadata terminology when clear."
    ),
    "actress": (
        "This text is a performer name. Preserve the name unless there is an obvious "
        "established Chinese form. Do not invent phonetic transliterations for "
        "uncertain Japanese names."
    ),
    "brand": (
        "This text is a series, maker, or label name. Preserve brand, studio, series, "
        "and label proper names. Translate only obvious ordinary words when doing so "
        "improves Chinese readability."
    ),
    "summary": (
        "This text is an adult video summary/description. Translate all meaning "
        "faithfully in the same order. Keep names, product codes, and concrete "
        "details. Do not censor explicit terms, do not summarize, and do not add "
        "commentary."
    ),
    "metadata": (
        "This text is an adult video metadata field. Translate the field value "
        "faithfully and concisely. Return only the translated text."
    ),
}


def _request_scene(request: TranslationRequest) -> str:
    context = str(request.context or "").strip().lower()
    scope = str(request.scope or "").strip().lower()
    combined = f"{context} {scope}"
    if "video title" in context or scope.startswith("title:") or scope.startswith("supplement:title:"):
        return "title"
    if "category name" in context or scope.startswith("category:") or scope.startswith("supplement:category_names:"):
        return "category"
    if "actress name" in context or "actor_names" in scope or scope.startswith("actress:"):
        return "actress"
    if any(item in context for item in ("series name", "maker name", "label name")):
        return "brand"
    if scope.startswith(("series:", "maker:", "label:")):
        return "brand"
    if (
        "video summary" in context
        or "description" in context
        or scope.startswith("summary:")
        or scope.startswith("supplement:summary:")
        or scope.startswith("supplement:description:")
    ):
        return "summary"
    if "title" in combined:
        return "title"
    if "category" in combined or "genre" in combined or "tag" in combined:
        return "category"
    return "metadata"


def _translation_prompts(request: TranslationRequest) -> tuple[str, str]:
    scene = _request_scene(request)
    system_prompt = f"{_BASE_AI_TRANSLATION_PROMPT} {_SCENE_PROMPTS[scene]}"
    user_prompt = (
        f"Target language: {request.target_language}\n"
        f"Metadata context: {request.context or request.scope or scene}\n"
        "Source text:\n"
        f"{request.text}"
    )
    return system_prompt, user_prompt


class MappingProvider:
    name = "mapping"

    def supports(self, request: TranslationRequest) -> bool:
        return bool(request.mapping and request.text in request.mapping)

    async def translate(self, request: TranslationRequest) -> TranslationResult | None:
        if not self.supports(request):
            return None
        return TranslationResult(
            translated_text=request.mapping[request.text],  # type: ignore[index]
            provider=self.name,
            cacheable=False,
        )


class AIProvider:
    name = "ai"

    def __init__(self, settings: dict[str, Any]):
        self.settings = settings or {}

    @property
    def model(self) -> str:
        provider = str(self.settings.get("provider") or "")
        provider_cfg = self.settings.get(provider, {}) if provider else {}
        if isinstance(provider_cfg, dict):
            return str(provider_cfg.get("model") or "")
        return ""

    def supports(self, request: TranslationRequest) -> bool:
        return bool(request.text)

    async def translate(self, request: TranslationRequest) -> TranslationResult | None:
        if not self.supports(request):
            return None

        system_prompt, user_prompt = _translation_prompts(request)

        try:
            client = build_ai_client(self.settings) if self.settings else get_ai_client()
            result = await client.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            logger.warning("AI translation failed for scope=%s: %s", request.scope, exc)
            return None

        translated = result.content.strip()
        if not translated:
            return None
        return TranslationResult(translated_text=translated, provider=result.provider, model=result.model)


class OpenAICompatibleProvider(AIProvider):
    name = "openai_compatible"

    def __init__(self, settings: dict[str, Any]):
        if settings and "provider" not in settings:
            settings = {"provider": "openai_compatible", "openai_compatible": settings}
        super().__init__(settings)

    async def translate(self, request: TranslationRequest) -> TranslationResult | None:
        result = await super().translate(request)
        if not result:
            return None
        return TranslationResult(
            translated_text=result.translated_text,
            provider=self.name if result.provider == "openai_compatible" else result.provider,
            model=result.model,
            cacheable=result.cacheable,
        )


class GoogleFreeProvider:
    name = "google_free"

    def __init__(self, settings: dict[str, Any], *, reuse_client: bool = False):
        self.settings = settings or {}
        self.reuse_client = reuse_client
        self._client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def supports(self, request: TranslationRequest) -> bool:
        return bool(request.text and self.settings.get("enabled", True))

    async def translate(self, request: TranslationRequest) -> TranslationResult | None:
        if not self.supports(request):
            return None
        base_url = str(self.settings.get("base_url") or "https://translate.googleapis.com/translate_a/single")
        try:
            timeout = float(self.settings.get("timeout", 10))
        except Exception:
            timeout = 10.0
        params = {
            "client": "gtx",
            "sl": request.source_language or "auto",
            "tl": _target_lang(request.target_language),
            "dt": "t",
            "q": request.text,
        }
        try:
            if self.reuse_client:
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=timeout, trust_env=False)
                response = await self._client.get(base_url, params=params)
            else:
                async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                    response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("Google free translation failed for scope=%s: %s", request.scope, exc)
            return None
        try:
            translated = "".join(part[0] for part in data[0] if part and part[0]).strip()
        except Exception:
            logger.warning("Google free translation returned unexpected response for scope=%s", request.scope)
            return None
        if not translated:
            return None
        return TranslationResult(translated_text=translated, provider=self.name)

    async def translate_many(self, requests: list[TranslationRequest]) -> list[TranslationResult | None]:
        supported = [request for request in requests if self.supports(request)]
        if len(supported) != len(requests):
            return [None for _ in requests]
        if not requests:
            return []
        if len(requests) == 1:
            return [await self.translate(requests[0])]

        base_url = str(self.settings.get("base_url") or "https://translate.googleapis.com/translate_a/single")
        try:
            timeout = float(self.settings.get("timeout", 10))
        except Exception:
            timeout = 10.0
        joined = "\n".join(_one_line(request.text) for request in requests)
        params = {
            "client": "gtx",
            "sl": requests[0].source_language or "auto",
            "tl": _target_lang(requests[0].target_language),
            "dt": "t",
            "q": joined,
        }
        try:
            if self.reuse_client:
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=timeout, trust_env=False)
                response = await self._client.get(base_url, params=params)
            else:
                async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                    response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            translated = "".join(part[0] for part in data[0] if part and part[0]).strip()
        except Exception as exc:
            logger.warning("Google free batch translation failed for %s items: %s", len(requests), exc)
            return await self._translate_many_split(requests)

        lines = translated.splitlines()
        if len(lines) != len(requests):
            logger.warning(
                "Google free batch translation returned %s lines for %s requests",
                len(lines),
                len(requests),
            )
            return await self._translate_many_split(requests)
        return [
            TranslationResult(translated_text=line.strip(), provider=self.name) if line.strip() else None
            for line in lines
        ]

    async def _translate_many_split(self, requests: list[TranslationRequest]) -> list[TranslationResult | None]:
        if len(requests) <= 1:
            return [await self.translate(requests[0])] if requests else []
        middle = max(1, len(requests) // 2)
        left, right = await asyncio.gather(
            self.translate_many(requests[:middle]),
            self.translate_many(requests[middle:]),
        )
        return [*left, *right]


class DeepLProvider:
    name = "deepl"

    def __init__(self, settings: dict[str, Any]):
        self.settings = settings or {}

    def supports(self, request: TranslationRequest) -> bool:
        return bool(request.text and self.settings.get("enabled") and self.settings.get("api_key"))

    async def translate(self, request: TranslationRequest) -> TranslationResult | None:
        if not self.supports(request):
            return None
        free_api = bool(self.settings.get("free_api", True))
        base_url = str(
            self.settings.get("base_url")
            or ("https://api-free.deepl.com/v2/translate" if free_api else "https://api.deepl.com/v2/translate")
        )
        try:
            timeout = float(self.settings.get("timeout", 15))
        except Exception:
            timeout = 15.0
        data = {
            "auth_key": str(self.settings.get("api_key") or ""),
            "text": request.text,
            "target_lang": _deepl_target_lang(request.target_language),
        }
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(base_url, data=data)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("DeepL translation failed for scope=%s: %s", request.scope, exc)
            return None
        try:
            translated = payload["translations"][0]["text"].strip()
        except Exception:
            logger.warning("DeepL translation returned unexpected response for scope=%s", request.scope)
            return None
        return TranslationResult(translated_text=translated, provider=self.name, model="deepl")


class MicrosoftTranslatorProvider:
    name = "microsoft"

    def __init__(self, settings: dict[str, Any]):
        self.settings = settings or {}

    def supports(self, request: TranslationRequest) -> bool:
        return bool(request.text and self.settings.get("enabled") and self.settings.get("api_key"))

    async def translate(self, request: TranslationRequest) -> TranslationResult | None:
        if not self.supports(request):
            return None
        endpoint = str(self.settings.get("endpoint") or "https://api.cognitive.microsofttranslator.com").rstrip("/")
        region = str(self.settings.get("region") or "")
        try:
            timeout = float(self.settings.get("timeout", 15))
        except Exception:
            timeout = 15.0
        headers = {
            "Ocp-Apim-Subscription-Key": str(self.settings.get("api_key") or ""),
            "Content-Type": "application/json",
        }
        if region:
            headers["Ocp-Apim-Subscription-Region"] = region
        params = {"api-version": "3.0", "to": _target_lang(request.target_language)}
        body = [{"text": request.text}]
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(f"{endpoint}/translate", params=params, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("Microsoft translation failed for scope=%s: %s", request.scope, exc)
            return None
        try:
            translated = payload[0]["translations"][0]["text"].strip()
        except Exception:
            logger.warning("Microsoft translation returned unexpected response for scope=%s", request.scope)
            return None
        return TranslationResult(translated_text=translated, provider=self.name, model="microsoft-translator")


def _target_lang(value: str) -> str:
    normalized = (value or "zh-CN").replace("_", "-").lower()
    if normalized in {"zh-cn", "zh-hans", "zh"}:
        return "zh-CN"
    if normalized in {"zh-tw", "zh-hant"}:
        return "zh-TW"
    return normalized


def _one_line(value: str) -> str:
    return " ".join(str(value or "").replace("\r", "\n").splitlines()).strip()


def _deepl_target_lang(value: str) -> str:
    normalized = _target_lang(value).upper()
    if normalized == "ZH-CN":
        return "ZH-HANS"
    if normalized == "ZH-TW":
        return "ZH-HANT"
    return normalized
