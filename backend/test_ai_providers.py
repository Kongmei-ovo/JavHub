from __future__ import annotations

import unittest

from test_support.httpx import FakeHTTPResponse, RecordingAsyncClient


class AiProviderServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_openai_compatible_chat_and_models_use_standard_paths(self):
        from services.ai import build_ai_client

        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"choices": [{"message": {"content": "ok"}}]}))
        RecordingAsyncClient.add_response("get", FakeHTTPResponse({"data": [{"id": "gpt-test"}, {"id": "embed-test"}]}))

        client = build_ai_client({
            "provider": "openai_compatible",
            "openai_compatible": {
                "base_url": "https://openai.example/v1",
                "api_key": "token",
                "model": "gpt-test",
                "timeout": 7,
            },
        }, http_client_cls=RecordingAsyncClient)

        reply = await client.chat([{"role": "user", "content": "hello"}])
        models = await client.list_models()

        self.assertEqual(reply.content, "ok")
        self.assertEqual(reply.provider, "openai_compatible")
        self.assertEqual(reply.model, "gpt-test")
        self.assertEqual(models["models"][0]["id"], "gpt-test")
        init_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "__init__"]
        self.assertEqual(init_calls[0]["kwargs"], {"timeout": 7.0, "trust_env": False})
        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertEqual(post_calls[0]["url"], "https://openai.example/v1/chat/completions")
        self.assertEqual(post_calls[0]["kwargs"]["json"]["model"], "gpt-test")
        self.assertEqual(post_calls[0]["kwargs"]["headers"]["Authorization"], "Bearer token")
        get_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "get"]
        self.assertEqual(get_calls[0]["url"], "https://openai.example/v1/models")

    async def test_gemini_chat_and_models_use_native_google_shapes(self):
        from services.ai import build_ai_client

        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response(
            "post",
            FakeHTTPResponse({"candidates": [{"content": {"parts": [{"text": "好的"}]}}]}),
        )
        RecordingAsyncClient.add_response(
            "get",
            FakeHTTPResponse({"models": [
                {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
            ]}),
        )

        client = build_ai_client({
            "provider": "gemini",
            "gemini": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": "gem-token",
                "model": "gemini-2.0-flash",
                "timeout": 9,
            },
        }, http_client_cls=RecordingAsyncClient)

        reply = await client.chat([
            {"role": "system", "content": "return json"},
            {"role": "user", "content": "hello"},
        ], json_mode=True)
        models = await client.list_models()

        self.assertEqual(reply.content, "好的")
        self.assertEqual(reply.provider, "gemini")
        self.assertEqual(reply.model, "gemini-2.0-flash")
        self.assertEqual(models["models"], [{"id": "gemini-2.0-flash", "name": "gemini-2.0-flash"}])
        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertEqual(post_calls[0]["url"], "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent")
        self.assertEqual(post_calls[0]["kwargs"]["json"]["generationConfig"]["response_mime_type"], "application/json")
        self.assertEqual(post_calls[0]["kwargs"]["headers"]["x-goog-api-key"], "gem-token")
        get_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "get"]
        self.assertEqual(get_calls[0]["url"], "https://generativelanguage.googleapis.com/v1beta/models")

    async def test_ollama_chat_and_models_use_local_native_shapes(self):
        from services.ai import build_ai_client

        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"message": {"content": "{\"ok\":true}"}}))
        RecordingAsyncClient.add_response(
            "get",
            FakeHTTPResponse({"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2:latest"}]}),
        )

        client = build_ai_client({
            "provider": "ollama",
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "qwen2.5:7b",
                "timeout": 11,
            },
        }, http_client_cls=RecordingAsyncClient)

        reply = await client.chat([{"role": "user", "content": "json"}], json_mode=True)
        models = await client.list_models()

        self.assertEqual(reply.content, "{\"ok\":true}")
        self.assertEqual(reply.provider, "ollama")
        self.assertEqual(reply.model, "qwen2.5:7b")
        self.assertEqual(models["models"][0]["id"], "qwen2.5:7b")
        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertEqual(post_calls[0]["url"], "http://localhost:11434/api/chat")
        self.assertEqual(post_calls[0]["kwargs"]["json"]["format"], "json")
        self.assertEqual(post_calls[0]["kwargs"]["json"]["stream"], False)
        get_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "get"]
        self.assertEqual(get_calls[0]["url"], "http://localhost:11434/api/tags")


if __name__ == "__main__":
    unittest.main()
