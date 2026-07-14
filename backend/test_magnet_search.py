from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, call, patch

from sources.registry import SourceRegistry


class StaticSource:
    def __init__(
        self,
        name: str,
        rows: list[dict] | None = None,
        error: Exception | None = None,
        calls: list[tuple[str, str]] | None = None,
        api_key: str = "",
    ) -> None:
        self.name = name
        self.rows = rows or []
        self.error = error
        self.calls = calls
        self.api_key = api_key

    async def search(self, keyword: str) -> list[dict]:
        if self.calls is not None:
            self.calls.append((self.name, keyword))
        if self.error:
            raise self.error
        return self.rows


class _Barrier:
    def __init__(self, parties: int) -> None:
        self.parties = parties
        self.arrived = 0
        self.ready = asyncio.Event()

    async def wait(self) -> None:
        self.arrived += 1
        if self.arrived >= self.parties:
            self.ready.set()
        await self.ready.wait()


class BarrierSource(StaticSource):
    def __init__(self, name: str, barrier: _Barrier) -> None:
        super().__init__(name, rows=[{"magnet": f"magnet:?xt=urn:btih:{name}"}])
        self.barrier = barrier

    async def search(self, keyword: str) -> list[dict]:
        await self.barrier.wait()
        return [{"title": keyword, "magnet": f"magnet:?xt=urn:btih:{self.name}"}]


class MagnetSearchTest(unittest.IsolatedAsyncioTestCase):
    def test_shared_redactor_covers_assignments_headers_and_url_credentials(self):
        from services.secret_redactor import redact_sensitive_text

        message = "\n".join(
            [
                "api_key=api-one apikey=api-two jackett_apikey=api-three",
                "passkey=pass-one password=pass-two secret=secret-one token=token-one",
                "Authorization: Bearer bearer-secret",
                "Cookie: session=cookie-secret; Path=/",
                (
                    "GET https://url-user:url-password@indexer.test/download"
                    "?passkey=url-query-secret&safe=1"
                ),
                "opaque literal-known-secret",
            ]
        )

        sanitized = redact_sensitive_text(
            message,
            secrets=("literal-known-secret",),
        )

        for secret in (
            "api-one",
            "api-two",
            "api-three",
            "pass-one",
            "pass-two",
            "secret-one",
            "token-one",
            "bearer-secret",
            "cookie-secret",
            "url-user",
            "url-password",
            "url-query-secret",
            "literal-known-secret",
        ):
            self.assertNotIn(secret, sanitized)
        self.assertNotIn("Bearer", sanitized)
        self.assertIn("[redacted]", sanitized)

    def test_shared_redactor_covers_generic_assignments_and_nested_url_queries(self):
        from services.secret_redactor import redact_sensitive_text

        message = (
            "key=plain-key auth=plain-auth access_token=plain-token "
            "https://outer.test/fetch?url="
            "https%3A%2F%2Ftracker.test%2Fdownload%3Fpasskey%3Dnested-passkey"
        )

        sanitized = redact_sensitive_text(message)

        for secret in ("plain-key", "plain-auth", "plain-token", "nested-passkey"):
            self.assertNotIn(secret, sanitized)

    async def test_auto_search_keeps_success_when_one_source_fails_and_dedupes_hash(self):
        from services.magnet_search import search_magnets

        sources = {
            "broken": StaticSource("broken", error=RuntimeError("timeout")),
            "good": StaticSource(
                "good",
                rows=[
                    {
                        "title": "MIAA-784 1080p",
                        "magnet": "magnet:?xt=urn:btih:ABC",
                        "seeders": 20,
                    },
                    {
                        "title": "MIAA-784 duplicate",
                        "magnet": "magnet:?xt=urn:btih:abc",
                        "seeders": 1,
                    },
                ],
            ),
        }
        with patch.object(SourceRegistry, "_sources", sources), patch.object(
            SourceRegistry, "_priority", ["broken", "good"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ):
            result = await search_magnets("MIAA-784", source_names=None)

        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["source"], "good")
        self.assertEqual([row["source"] for row in result["attempts"]], ["broken", "good"])
        self.assertEqual([row["source"] for row in result["errors"]], ["broken"])

    async def test_selected_search_calls_only_requested_runtime_name(self):
        from services.magnet_search import search_magnets

        calls: list[tuple[str, str]] = []
        sources = {
            "one": StaticSource("one", calls=calls),
            "two": StaticSource("two", calls=calls),
        }
        with patch.object(SourceRegistry, "_sources", sources), patch.object(
            SourceRegistry, "_priority", ["one", "two"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ):
            result = await search_magnets("MIAA-784", source_names=["two"])

        self.assertEqual(calls, [("two", "MIAA-784")])
        self.assertEqual([row["source"] for row in result["attempts"]], ["two"])

    async def test_success_items_remove_secret_uris_across_public_result_shapes(self):
        import json

        from services.magnet_search import search_magnets_for_item

        secrets = ("magnet-secret", "tracker-secret", "userinfo-secret", "url-secret")
        source = StaticSource(
            "indexer",
            rows=[
                {
                    "title": "MIAA-784 1080p",
                    "magnet": (
                        "magnet:?xt=urn:btih:SAFE784&apikey=magnet-secret"
                        "&tr=https%3A%2F%2Ftracker.test%2Fannounce%3Fpasskey%3Dtracker-secret"
                    ),
                    "download_url": (
                        "https://user:userinfo-secret@indexer.test/download"
                        "?jackett_apikey=url-secret"
                    ),
                    "torrent_url": (
                        "https://user:userinfo-secret@indexer.test/download"
                        "?jackett_apikey=url-secret"
                    ),
                },
                {
                    "title": "MIAA-784 unsafe only",
                    "download_url": "https://indexer.test/download?passkey=url-secret",
                },
            ],
        )
        with patch.object(SourceRegistry, "_sources", {"indexer": source}), patch.object(
            SourceRegistry, "_priority", ["indexer"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ):
            result = await search_magnets_for_item({"dvd_id": "MIAA-784"})

        serialized = json.dumps(result, ensure_ascii=False)
        for secret in secrets:
            self.assertNotIn(secret, serialized)
        self.assertEqual(len(result["items"]), 1)
        self.assertIn("urn:btih:SAFE784", result["best"]["magnet"])
        self.assertNotIn("download_url", result["best"])
        self.assertNotIn("torrent_url", result["best"])

    async def test_provider_extensions_are_canonicalized_to_json_safe_fields(self):
        import json

        from services.magnet_search import search_magnets_for_item

        source = StaticSource(
            "indexer",
            rows=[
                {
                    "title": "MIAA-784 1080p",
                    "magnet": "magnet:?xt=urn:btih:JSONSAFE",
                    "size": "2.0GB",
                    "resolution": "1080p",
                    "seeders": 12,
                    "binary": b"torrent bytes",
                    "provider_timestamp": datetime(
                        2026, 7, 14, tzinfo=timezone.utc
                    ),
                    "unexpected_extension": "must-drop",
                    "metadata": {"nested": object()},
                }
            ],
        )
        with patch.object(SourceRegistry, "_sources", {"indexer": source}), patch.object(
            SourceRegistry, "_priority", ["indexer"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ):
            result = await search_magnets_for_item({"dvd_id": "MIAA-784"})

        json.dumps(result, ensure_ascii=False)
        allowed = {
            "magnet",
            "torrent_url",
            "download_url",
            "title",
            "name",
            "size",
            "quality",
            "resolution",
            "hd",
            "subtitle",
            "source",
            "seeders",
            "leechers",
            "peers",
            "info_hash",
        }
        self.assertLessEqual(set(result["items"][0]), allowed)
        self.assertLessEqual(set(result["best"]) - {"reason_breakdown"}, allowed)
        self.assertNotIn("binary", result["candidates"][0]["item"])
        self.assertNotIn("unexpected_extension", result["candidates"][0]["item"])

    async def test_concurrent_selected_searches_return_only_their_direct_attempts(self):
        barrier = _Barrier(2)
        sources = {
            "one": BarrierSource("one", barrier),
            "two": BarrierSource("two", barrier),
        }
        with patch.object(SourceRegistry, "_sources", sources), patch.object(
            SourceRegistry, "_priority", ["one", "two"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ):
            first, second = await asyncio.gather(
                SourceRegistry.search_selected("FIRST-001", ["one"]),
                SourceRegistry.search_selected("SECOND-002", ["two"]),
            )

        first_rows, first_attempts = first
        second_rows, second_attempts = second
        self.assertEqual(first_rows[0]["source"], "one")
        self.assertEqual(second_rows[0]["source"], "two")
        self.assertEqual(
            [(row["source"], row["keyword"]) for row in first_attempts],
            [("one", "FIRST-001")],
        )
        self.assertEqual(
            [(row["source"], row["keyword"]) for row in second_attempts],
            [("two", "SECOND-002")],
        )

    async def test_attempt_errors_are_sanitized_before_return_and_health_history(self):
        from services.magnet_search import search_magnets

        api_key = "top-secret-key"
        source = StaticSource(
            "broken",
            error=RuntimeError(
                f"request failed: https://indexer.test/api?apikey={api_key}&q=x; key={api_key}"
            ),
            api_key=api_key,
        )
        with patch.object(SourceRegistry, "_sources", {"broken": source}), patch.object(
            SourceRegistry, "_priority", ["broken"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ) as record:
            result = await search_magnets("MIAA-784")

            history = SourceRegistry.recent_attempts()

        self.assertNotIn(api_key, result["errors"][0]["error"])
        self.assertNotIn(api_key, history[0]["error"])
        self.assertNotIn(api_key, record.call_args.kwargs["error"])

    async def test_complex_error_secrets_are_removed_from_local_history_and_db_attempts(self):
        from services.magnet_search import search_magnets

        api_key = "configured-api-secret"
        leaked = (
            api_key,
            "pass-secret",
            "password-secret",
            "bearer-secret",
            "cookie-secret",
            "url-user",
            "url-password",
        )
        error = RuntimeError(
            "\n".join(
                [
                    f"api_key={api_key} passkey=pass-secret password=password-secret",
                    "Authorization: Bearer bearer-secret",
                    "Cookie: sid=cookie-secret; Path=/",
                    (
                        "GET https://url-user:url-password@indexer.test/api"
                        "?token=query-secret"
                    ),
                ]
            )
        )
        source = StaticSource("broken", error=error, api_key=api_key)
        with patch.object(SourceRegistry, "_sources", {"broken": source}), patch.object(
            SourceRegistry, "_priority", ["broken"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ) as record:
            result = await search_magnets("MIAA-784")
            history = SourceRegistry.recent_attempts()

        surfaces = (
            result["attempts"][0]["error"],
            result["errors"][0]["error"],
            history[0]["error"],
            record.call_args.kwargs["error"],
        )
        for surface in surfaces:
            for secret in (*leaked, "query-secret"):
                self.assertNotIn(secret, surface)

    def test_identity_prefers_explicit_hash_then_btih_then_normalized_uri(self):
        from services.magnet_search import magnet_identity

        self.assertEqual(
            magnet_identity(
                {
                    "info_hash": "AbC",
                    "magnet": "magnet:?xt=urn:btih:DIFFERENT",
                }
            ),
            magnet_identity({"info_hash": "abc", "magnet": "magnet:?xt=urn:btih:OTHER"}),
        )
        self.assertEqual(
            magnet_identity({"magnet": "magnet:?xt=urn:btih:ABC&dn=One"}),
            magnet_identity({"magnet": "MAGNET:?dn=Two&xt=URN:BTIH:abc"}),
        )
        self.assertEqual(
            magnet_identity({"magnet": "magnet:?dn=One+File&tr=https%3A%2F%2Ft.test"}),
            magnet_identity({"magnet": "MAGNET:?tr=https%3A%2F%2Ft.test&dn=One%20File"}),
        )

    async def test_item_search_discards_earlier_unverified_when_later_keyword_verifies(self):
        from services.magnet_search import search_magnets_for_item

        unverified = {
            "title": "Unrelated 中文字幕 1080p",
            "magnet": "magnet:?xt=urn:btih:UNVERIFIED",
            "subtitle": True,
            "resolution": "1080p",
        }
        verified = {
            "title": "RAW-002 720p",
            "magnet": "magnet:?xt=urn:btih:VERIFIED",
            "resolution": "720p",
        }
        batches = [
            {"items": [unverified], "attempts": [{"source": "one", "ok": True}], "errors": []},
            {"items": [verified], "attempts": [{"source": "two", "ok": True}], "errors": []},
        ]
        with patch(
            "services.magnet_search.search_codes_for_item",
            return_value=["DISPLAY-001", "RAW-002", "NEVER-003"],
        ), patch(
            "services.magnet_search._search_magnets",
            new=AsyncMock(side_effect=batches),
        ) as search:
            result = await search_magnets_for_item(
                {"dvd_id": "DISPLAY-001"}, source_names=["selected"]
            )

        self.assertEqual(search.await_args_list, [
            call("DISPLAY-001", source_names=["selected"], deduplicate=False),
            call("RAW-002", source_names=["selected"], deduplicate=False),
        ])
        self.assertEqual([row["magnet"] for row in result["items"]], [verified["magnet"]])
        self.assertEqual(result["best"]["magnet"], verified["magnet"])
        self.assertEqual([row["magnet"] for row in result["alternatives"]], [verified["magnet"]])
        self.assertEqual(len(result["attempts"]), 2)

    async def test_item_search_stops_after_first_keyword_with_verified_hit(self):
        from services.magnet_search import search_magnets_for_item

        first = {
            "title": "DISPLAY-001 1080p",
            "magnet": "magnet:?xt=urn:btih:FIRST",
            "resolution": "1080p",
        }
        search = AsyncMock(return_value={"items": [first], "attempts": [], "errors": []})
        with patch(
            "services.magnet_search.search_codes_for_item",
            return_value=["DISPLAY-001", "RAW-002"],
        ), patch("services.magnet_search._search_magnets", new=search):
            result = await search_magnets_for_item({"dvd_id": "DISPLAY-001"})

        search.assert_awaited_once_with(
            "DISPLAY-001", source_names=None, deduplicate=False
        )
        self.assertEqual(result["best"]["magnet"], first["magnet"])

    async def test_item_verification_happens_before_same_hash_deduplication(self):
        from services.magnet_search import search_magnets_for_item

        unverified_higher_score = {
            "title": "Unrelated 中文字幕 1080p",
            "magnet": "magnet:?xt=urn:btih:SAME",
            "subtitle": True,
            "resolution": "1080p",
        }
        verified_lower_score = {
            "title": "CODE-001 720p",
            "magnet": "magnet:?xt=urn:btih:same",
            "resolution": "720p",
        }
        source = StaticSource(
            "indexer",
            rows=[unverified_higher_score, verified_lower_score],
        )
        with patch.object(SourceRegistry, "_sources", {"indexer": source}), patch.object(
            SourceRegistry, "_priority", ["indexer"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ):
            result = await search_magnets_for_item({"dvd_id": "CODE-001"})

        self.assertEqual(result["best"]["title"], verified_lower_score["title"])
        self.assertEqual([row["title"] for row in result["items"]], [verified_lower_score["title"]])

    async def test_item_search_uses_ranked_deduped_unverified_fallback_and_seeder_tiebreak(self):
        from services.magnet_search import search_magnets_for_item

        duplicate_weaker = {
            "title": "Unrelated 720p",
            "magnet": "magnet:?xt=urn:btih:ABC",
            "resolution": "720p",
            "seeders": 500,
        }
        duplicate_stronger = {
            "title": "Still unrelated 中文字幕 1080p",
            "magnet": "magnet:?xt=urn:btih:abc",
            "subtitle": True,
            "resolution": "1080p",
            "seeders": 1,
        }
        tied_low_seeders = {
            "title": "Other 中文字幕 1080p",
            "magnet": "magnet:?xt=urn:btih:DEF",
            "subtitle": True,
            "resolution": "1080p",
            "seeders": 2,
        }
        tied_high_seeders = {
            "title": "Another 中文字幕 1080p",
            "magnet": "magnet:?xt=urn:btih:GHI",
            "subtitle": True,
            "resolution": "1080p",
            "seeders": 20,
        }
        batches = [
            {"items": [duplicate_weaker, tied_low_seeders], "attempts": [], "errors": []},
            {"items": [duplicate_stronger, tied_high_seeders], "attempts": [], "errors": []},
        ]
        with patch(
            "services.magnet_search.search_codes_for_item",
            return_value=["CODE-001", "RAW-002"],
        ), patch(
            "services.magnet_search._search_magnets",
            new=AsyncMock(side_effect=batches),
        ):
            result = await search_magnets_for_item({"dvd_id": "CODE-001"})

        self.assertEqual(
            [row["magnet"] for row in result["items"]],
            [
                tied_high_seeders["magnet"],
                tied_low_seeders["magnet"],
                duplicate_stronger["magnet"],
            ],
        )
        self.assertEqual(result["best"]["magnet"], tied_high_seeders["magnet"])
        self.assertEqual(len(result["alternatives"]), 3)

    def test_shared_score_preserves_exact_breakdown_and_total_formula(self):
        from services.magnet_search import magnet_score

        score = magnet_score(
            {
                "title": "SIVR-438 字幕 1080p",
                "size": "4.2GB",
                "hd": True,
                "subtitle": True,
                "resolution": "1080p",
                "quality": "HD",
            }
        )

        self.assertEqual(
            list(score),
            ["subtitle", "hd", "resolution", "size_mb", "health", "size_fit", "total"],
        )
        self.assertEqual(score["subtitle"], 1)
        self.assertEqual(score["hd"], 1)
        self.assertEqual(score["resolution"], 4)
        self.assertEqual(score["size_mb"], 4.2 * 1024)
        self.assertEqual(score["health"], 0.5)
        self.assertEqual(score["size_fit"], 1.0)
        self.assertAlmostEqual(score["total"], 1000 + 400 + 5 + 1)


if __name__ == "__main__":
    unittest.main()
