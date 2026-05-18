from __future__ import annotations

import unittest


class AiProviderServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_openai_compatible_chat_and_models_use_standard_paths(self):
        from services.ai import build_ai_client

        class FakeResponse:
            text = ""

            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        class FakeAsyncClient:
            calls = []

            def __init__(self, *args, **kwargs):
                FakeAsyncClient.calls.append(("init", kwargs))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, url, json=None, headers=None):
                FakeAsyncClient.calls.append(("post", url, json, headers))
                return FakeResponse({"choices": [{"message": {"content": "ok"}}]})

            async def get(self, url, headers=None):
                FakeAsyncClient.calls.append(("get", url, headers))
                return FakeResponse({"data": [{"id": "gpt-test"}, {"id": "embed-test"}]})

        client = build_ai_client({
            "provider": "openai_compatible",
            "openai_compatible": {
                "base_url": "https://openai.example/v1",
                "api_key": "token",
                "model": "gpt-test",
                "timeout": 7,
            },
        }, http_client_cls=FakeAsyncClient)

        reply = await client.chat([{"role": "user", "content": "hello"}])
        models = await client.list_models()

        self.assertEqual(reply.content, "ok")
        self.assertEqual(reply.provider, "openai_compatible")
        self.assertEqual(reply.model, "gpt-test")
        self.assertEqual(models["models"][0]["id"], "gpt-test")
        self.assertEqual(FakeAsyncClient.calls[0], ("init", {"timeout": 7.0, "trust_env": False}))
        self.assertEqual(FakeAsyncClient.calls[1][1], "https://openai.example/v1/chat/completions")
        self.assertEqual(FakeAsyncClient.calls[1][2]["model"], "gpt-test")
        self.assertEqual(FakeAsyncClient.calls[1][3]["Authorization"], "Bearer token")
        get_calls = [call for call in FakeAsyncClient.calls if call[0] == "get"]
        self.assertEqual(get_calls[0][1], "https://openai.example/v1/models")

    async def test_gemini_chat_and_models_use_native_google_shapes(self):
        from services.ai import build_ai_client

        class FakeResponse:
            text = ""

            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        class FakeAsyncClient:
            calls = []

            def __init__(self, *args, **kwargs):
                FakeAsyncClient.calls.append(("init", kwargs))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, url, json=None, headers=None):
                FakeAsyncClient.calls.append(("post", url, json, headers))
                return FakeResponse({"candidates": [{"content": {"parts": [{"text": "好的"}]}}]})

            async def get(self, url, headers=None):
                FakeAsyncClient.calls.append(("get", url, headers))
                return FakeResponse({"models": [
                    {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
                ]})

        client = build_ai_client({
            "provider": "gemini",
            "gemini": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": "gem-token",
                "model": "gemini-2.0-flash",
                "timeout": 9,
            },
        }, http_client_cls=FakeAsyncClient)

        reply = await client.chat([
            {"role": "system", "content": "return json"},
            {"role": "user", "content": "hello"},
        ], json_mode=True)
        models = await client.list_models()

        self.assertEqual(reply.content, "好的")
        self.assertEqual(reply.provider, "gemini")
        self.assertEqual(reply.model, "gemini-2.0-flash")
        self.assertEqual(models["models"], [{"id": "gemini-2.0-flash", "name": "gemini-2.0-flash"}])
        self.assertEqual(FakeAsyncClient.calls[1][1], "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent")
        self.assertEqual(FakeAsyncClient.calls[1][2]["generationConfig"]["response_mime_type"], "application/json")
        self.assertEqual(FakeAsyncClient.calls[1][3]["x-goog-api-key"], "gem-token")
        get_calls = [call for call in FakeAsyncClient.calls if call[0] == "get"]
        self.assertEqual(get_calls[0][1], "https://generativelanguage.googleapis.com/v1beta/models")

    async def test_ollama_chat_and_models_use_local_native_shapes(self):
        from services.ai import build_ai_client

        class FakeResponse:
            text = ""

            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        class FakeAsyncClient:
            calls = []

            def __init__(self, *args, **kwargs):
                FakeAsyncClient.calls.append(("init", kwargs))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, url, json=None, headers=None):
                FakeAsyncClient.calls.append(("post", url, json, headers))
                return FakeResponse({"message": {"content": "{\"ok\":true}"}})

            async def get(self, url, headers=None):
                FakeAsyncClient.calls.append(("get", url, headers))
                return FakeResponse({"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2:latest"}]})

        client = build_ai_client({
            "provider": "ollama",
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "qwen2.5:7b",
                "timeout": 11,
            },
        }, http_client_cls=FakeAsyncClient)

        reply = await client.chat([{"role": "user", "content": "json"}], json_mode=True)
        models = await client.list_models()

        self.assertEqual(reply.content, "{\"ok\":true}")
        self.assertEqual(reply.provider, "ollama")
        self.assertEqual(reply.model, "qwen2.5:7b")
        self.assertEqual(models["models"][0]["id"], "qwen2.5:7b")
        self.assertEqual(FakeAsyncClient.calls[1][1], "http://localhost:11434/api/chat")
        self.assertEqual(FakeAsyncClient.calls[1][2]["format"], "json")
        self.assertEqual(FakeAsyncClient.calls[1][2]["stream"], False)
        get_calls = [call for call in FakeAsyncClient.calls if call[0] == "get"]
        self.assertEqual(get_calls[0][1], "http://localhost:11434/api/tags")


if __name__ == "__main__":
    unittest.main()
