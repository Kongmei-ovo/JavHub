from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from config import config

AI_PROVIDERS = {"openai_compatible", "gemini", "ollama"}


@dataclass(frozen=True)
class AIChatResult:
    content: str
    provider: str
    model: str


def _provider_name(settings: dict[str, Any]) -> str:
    provider = str((settings or {}).get("provider") or "openai_compatible").strip()
    return provider if provider in AI_PROVIDERS else "openai_compatible"


def _timeout(settings: dict[str, Any], default: float = 30.0) -> float:
    try:
        return float(settings.get("timeout", default) or default)
    except Exception:
        return default


def _join_messages(messages: list[dict[str, Any]]) -> str:
    parts = []
    for message in messages:
        role = str(message.get("role") or "user").strip() or "user"
        content = str(message.get("content") or "").strip()
        if content:
            parts.append(f"{role}: {content}")
    return "\n\n".join(parts)


class BaseAIClient:
    provider = ""

    def __init__(self, settings: dict[str, Any], *, http_client_cls=None):
        self.settings = settings or {}
        self.http_client_cls = http_client_cls or httpx.AsyncClient

    @property
    def model(self) -> str:
        return str(self.settings.get("model") or "").strip()

    @property
    def timeout(self) -> float:
        return _timeout(self.settings)

    def _base_url(self, default: str) -> str:
        return str(self.settings.get("base_url") or default).rstrip("/")

    def _api_key(self) -> str:
        return str(self.settings.get("api_key") or "")

    def _require_model(self) -> str:
        model = self.model
        if not model:
            raise RuntimeError("请先选择 AI 模型")
        return model

    async def chat(self, messages: list[dict[str, Any]], *, json_mode: bool = False, temperature: float = 0.2) -> AIChatResult:
        raise NotImplementedError

    async def list_models(self) -> dict[str, Any]:
        raise NotImplementedError

    async def test(self) -> dict[str, Any]:
        started = time.perf_counter()
        result = await self.chat([
            {"role": "system", "content": "Return only the exact text: ok"},
            {"role": "user", "content": "health check"},
        ], temperature=0)
        return {
            "success": True,
            "provider": result.provider,
            "model": result.model,
            "reply": result.content,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }


class OpenAICompatibleClient(BaseAIClient):
    provider = "openai_compatible"

    @property
    def model(self) -> str:
        return str(self.settings.get("model") or "gpt-4o-mini").strip()

    async def chat(self, messages: list[dict[str, Any]], *, json_mode: bool = False, temperature: float = 0.2) -> AIChatResult:
        model = self._require_model()
        base_url = self._base_url("https://api.openai.com/v1")
        api_key = self._api_key()
        if not base_url or not api_key:
            raise RuntimeError("请先填写 AI API 地址和 API Key")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with self.http_client_cls(timeout=self.timeout, trust_env=False) as client:
            response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            content = str(data["choices"][0]["message"]["content"]).strip()
        except Exception as exc:
            raise RuntimeError("AI 返回格式异常") from exc
        return AIChatResult(content=content, provider=self.provider, model=model)

    async def list_models(self) -> dict[str, Any]:
        base_url = self._base_url("https://api.openai.com/v1")
        api_key = self._api_key()
        if not base_url or not api_key:
            raise RuntimeError("请先填写 AI API 地址和 API Key")
        headers = {"Authorization": f"Bearer {api_key}"}
        async with self.http_client_cls(timeout=self.timeout, trust_env=False) as client:
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            data = response.json()
        models = []
        for item in data.get("data", []) if isinstance(data, dict) else []:
            model_id = str(item.get("id") or "").strip() if isinstance(item, dict) else ""
            if model_id:
                models.append({"id": model_id, "name": model_id})
        return {"provider": self.provider, "models": models}


class GeminiClient(BaseAIClient):
    provider = "gemini"

    @property
    def model(self) -> str:
        return str(self.settings.get("model") or "gemini-2.0-flash").strip()

    async def chat(self, messages: list[dict[str, Any]], *, json_mode: bool = False, temperature: float = 0.2) -> AIChatResult:
        model = self._require_model()
        base_url = self._base_url("https://generativelanguage.googleapis.com/v1beta")
        api_key = self._api_key()
        if not base_url or not api_key:
            raise RuntimeError("请先填写 Gemini API 地址和 API Key")
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": _join_messages(messages)}]}],
            "generationConfig": {"temperature": temperature},
        }
        if json_mode:
            payload["generationConfig"]["response_mime_type"] = "application/json"
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        async with self.http_client_cls(timeout=self.timeout, trust_env=False) as client:
            response = await client.post(f"{base_url}/models/{model}:generateContent", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            content = "".join(
                str(part.get("text") or "")
                for part in data["candidates"][0]["content"].get("parts", [])
                if isinstance(part, dict)
            ).strip()
        except Exception as exc:
            raise RuntimeError("Gemini 返回格式异常") from exc
        return AIChatResult(content=content, provider=self.provider, model=model)

    async def list_models(self) -> dict[str, Any]:
        base_url = self._base_url("https://generativelanguage.googleapis.com/v1beta")
        api_key = self._api_key()
        if not base_url or not api_key:
            raise RuntimeError("请先填写 Gemini API 地址和 API Key")
        headers = {"x-goog-api-key": api_key}
        async with self.http_client_cls(timeout=self.timeout, trust_env=False) as client:
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            data = response.json()
        models = []
        for item in data.get("models", []) if isinstance(data, dict) else []:
            if not isinstance(item, dict):
                continue
            methods = item.get("supportedGenerationMethods") or []
            if methods and "generateContent" not in methods:
                continue
            raw_name = str(item.get("name") or "").strip()
            model_id = raw_name.removeprefix("models/")
            if model_id:
                models.append({"id": model_id, "name": model_id})
        return {"provider": self.provider, "models": models}


class OllamaClient(BaseAIClient):
    provider = "ollama"

    async def chat(self, messages: list[dict[str, Any]], *, json_mode: bool = False, temperature: float = 0.2) -> AIChatResult:
        model = self._require_model()
        base_url = self._base_url("http://localhost:11434")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        async with self.http_client_cls(timeout=self.timeout, trust_env=False) as client:
            response = await client.post(f"{base_url}/api/chat", json=payload, headers={})
            response.raise_for_status()
            data = response.json()
        try:
            content = str(data["message"]["content"]).strip()
        except Exception as exc:
            raise RuntimeError("Ollama 返回格式异常") from exc
        return AIChatResult(content=content, provider=self.provider, model=model)

    async def list_models(self) -> dict[str, Any]:
        base_url = self._base_url("http://localhost:11434")
        async with self.http_client_cls(timeout=self.timeout, trust_env=False) as client:
            response = await client.get(f"{base_url}/api/tags", headers={})
            response.raise_for_status()
            data = response.json()
        models = []
        for item in data.get("models", []) if isinstance(data, dict) else []:
            model_id = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
            if model_id:
                models.append({"id": model_id, "name": model_id})
        return {"provider": self.provider, "models": models}


def build_ai_client(settings: dict[str, Any] | None = None, *, http_client_cls=None) -> BaseAIClient:
    ai_settings = settings or config.ai
    provider = _provider_name(ai_settings)
    provider_settings = ai_settings.get(provider, {}) if isinstance(ai_settings.get(provider), dict) else {}
    if provider == "gemini":
        return GeminiClient(provider_settings, http_client_cls=http_client_cls)
    if provider == "ollama":
        return OllamaClient(provider_settings, http_client_cls=http_client_cls)
    return OpenAICompatibleClient(provider_settings, http_client_cls=http_client_cls)


def get_ai_client() -> BaseAIClient:
    return build_ai_client(config.ai)
