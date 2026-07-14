from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from sources.torznab_source import TorznabSource
from test_support.httpx import FakeHTTPResponse, RecordingAsyncClient


class _WorkingSource:
    name = "working"

    async def search(self, keyword: str) -> list[dict]:
        return [
            {
                "title": f"{keyword} 1080p",
                "magnet": "magnet:?xt=urn:btih:WORKING",
            }
        ]


class TorznabSourceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        RecordingAsyncClient.reset()

    def queue_response(self, text: str, *, status_code: int = 200):
        RecordingAsyncClient.add_response("get", FakeHTTPResponse(text=text, status_code=status_code))

    def patch_client(self):
        return patch("sources.torznab_source.httpx.AsyncClient", RecordingAsyncClient)

    async def test_disabled_source_returns_empty_results(self):
        source = TorznabSource(base_url="http://indexer.test", api_key="secret", enabled=False)

        results = await source.search("SIVR-438")

        self.assertEqual(results, [])
        self.assertFalse(source.is_implemented())

    async def test_blank_config_or_keyword_returns_empty_without_http_request(self):
        missing_config = TorznabSource(enabled=True)
        configured = TorznabSource(
            base_url="http://indexer.test",
            api_key="secret",
            enabled=True,
        )

        with self.patch_client():
            self.assertEqual(await missing_config.search("SIVR-438"), [])
            self.assertEqual(await configured.search("   "), [])

        self.assertFalse(
            any(call["method"] == "get" for call in RecordingAsyncClient.calls)
        )

    async def test_parses_magneturl_attr_seeders_and_size(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <item>
      <title>SIVR-438 1080p 字幕</title>
      <link>https://indexer.test/download/1</link>
      <torznab:attr name="magneturl" value="magnet:?xt=urn:btih:ABC123" />
      <torznab:attr name="seeders" value="42" />
      <torznab:attr name="leechers" value="8" />
      <torznab:attr name="peers" value="50" />
      <torznab:attr name="size" value="2147483648" />
    </item>
  </channel>
</rss>""")
        source = TorznabSource(base_url="http://indexer.test", api_key="secret", enabled=True)

        with self.patch_client():
            results = await source.search("SIVR-438")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["magnet"], "magnet:?xt=urn:btih:ABC123")
        self.assertEqual(results[0]["download_url"], "https://indexer.test/download/1")
        self.assertEqual(results[0]["seeders"], 42)
        self.assertEqual(results[0]["leechers"], 8)
        self.assertEqual(results[0]["peers"], 50)
        self.assertEqual(results[0]["size"], "2.0GB")
        self.assertEqual(results[0]["resolution"], "1080p")
        self.assertTrue(results[0]["hd"])
        self.assertTrue(results[0]["subtitle"])
        self.assertEqual(results[0]["source"], "torznab")

    async def test_parses_jackett_magnet_enclosure(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss>
  <channel>
    <item>
      <title>ABP-588 720p</title>
      <enclosure url="magnet:?xt=urn:btih:DEF456" length="734003200" type="application/x-bittorrent" />
    </item>
  </channel>
</rss>""")
        source = TorznabSource(base_url="http://jackett.test", api_key="secret", enabled=True)

        with self.patch_client():
            results = await source.search("ABP-588")

        self.assertEqual(results[0]["magnet"], "magnet:?xt=urn:btih:DEF456")
        self.assertEqual(results[0]["size"], "700.0MB")
        self.assertEqual(results[0]["resolution"], "720p")
        self.assertTrue(results[0]["hd"])

    async def test_parses_http_torrent_enclosure_without_magnet(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss>
  <channel>
    <item>
      <title>ABP-588 1080p</title>
      <enclosure url="https://indexer.test/download/ABP-588.torrent" length="2147483648" type="application/x-bittorrent" />
    </item>
  </channel>
</rss>""")
        source = TorznabSource(base_url="http://jackett.test", api_key="secret", enabled=True)

        with self.patch_client():
            results = await source.search("ABP-588")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["magnet"], "")
        self.assertEqual(results[0]["download_url"], "https://indexer.test/download/ABP-588.torrent")
        self.assertEqual(results[0]["torrent_url"], "https://indexer.test/download/ABP-588.torrent")
        self.assertEqual(results[0]["size"], "2.0GB")

    async def test_result_removes_secret_urls_and_secret_magnet_parameters(self):
        leaked = ("explicit-secret", "tracker-secret", "userinfo-secret", "url-secret")
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <item>
      <title>ABP-588 1080p</title>
      <enclosure url="https://user:userinfo-secret@indexer.test/download?jackett_apikey=url-secret" />
      <torznab:attr name="magneturl" value="magnet:?xt=urn:btih:SAFE123&amp;apikey=explicit-secret&amp;tr=https%3A%2F%2Ftracker.test%2Fannounce%3Fpasskey%3Dtracker-secret" />
    </item>
  </channel>
</rss>""")
        source = TorznabSource(
            base_url="http://indexer.test",
            api_key="request-secret",
            enabled=True,
        )

        with self.patch_client():
            results = await source.search("ABP-588")

        self.assertEqual(len(results), 1)
        serialized = str(results[0])
        for secret in leaked:
            self.assertNotIn(secret, serialized)
        self.assertIn("urn:btih:SAFE123", results[0]["magnet"])
        self.assertNotIn("download_url", results[0])
        self.assertNotIn("torrent_url", results[0])

    async def test_result_with_only_secret_http_url_is_dropped(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss>
  <channel>
    <item>
      <title>ABP-588 1080p</title>
      <enclosure url="https://user:password@indexer.test/download?passkey=only-secret" />
    </item>
  </channel>
</rss>""")
        source = TorznabSource(
            base_url="http://indexer.test",
            api_key="request-secret",
            enabled=True,
        )

        with self.patch_client():
            results = await source.search("ABP-588")

        self.assertEqual(results, [])

    async def test_prowlarr_secret_proxy_urls_fall_back_to_safe_info_hash_magnet(self):
        api_key = "prowlarr-secret"
        info_hash = "0123456789ABCDEF0123456789ABCDEF01234567"
        self.queue_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <item>
      <title>MIAA-784 1080p</title>
      <enclosure url="http://prowlarr.test/7/download?apikey={api_key}" />
      <torznab:attr name="magneturl" value="http://prowlarr.test/7/download?apikey={api_key}" />
      <torznab:attr name="infohash" value="{info_hash}" />
    </item>
  </channel>
</rss>""")
        source = TorznabSource(
            kind="prowlarr",
            base_url="http://prowlarr.test",
            api_key=api_key,
            enabled=True,
        )

        with self.patch_client():
            results = await source.search("MIAA-784")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["magnet"], f"magnet:?xt=urn:btih:{info_hash}")
        self.assertEqual(results[0]["info_hash"], info_hash)
        self.assertNotIn(api_key, str(results[0]))
        self.assertNotIn("download_url", results[0])
        self.assertNotIn("torrent_url", results[0])

    async def test_torznab_error_response_raises_without_echoing_api_key(self):
        api_key = "top-secret-key"
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<error code="100" description="Incorrect user credentials: top-secret-key" />""")
        source = TorznabSource(
            base_url="http://indexer.test",
            api_key=api_key,
            enabled=True,
        )

        with self.patch_client(), self.assertRaises(Exception) as raised:
            await source.search("SIVR-438")

        self.assertIn("100", str(raised.exception))
        self.assertNotIn(api_key, str(raised.exception))

    async def test_invalid_xml_raises_instead_of_becoming_empty_success(self):
        self.queue_response("<rss><channel>")
        source = TorznabSource(
            base_url="http://indexer.test",
            api_key="secret",
            enabled=True,
        )

        with self.patch_client(), self.assertRaises(Exception):
            await source.search("SIVR-438")

    async def test_http_transport_error_raises_without_echoing_api_key(self):
        api_key = "top-secret-key"

        def fail_request(**_kwargs):
            raise httpx.ConnectError(f"failed with api_key={api_key}")

        RecordingAsyncClient.add_response("get", fail_request)
        source = TorznabSource(
            base_url="http://indexer.test",
            api_key=api_key,
            enabled=True,
        )

        with self.patch_client(), self.assertRaises(Exception) as raised:
            await source.search("SIVR-438")

        self.assertNotIn(api_key, str(raised.exception))

    async def test_valid_empty_feed_is_a_successful_empty_result(self):
        self.queue_response("<?xml version='1.0'?><rss><channel /></rss>")
        source = TorznabSource(
            base_url="http://indexer.test",
            api_key="secret",
            enabled=True,
        )

        with self.patch_client():
            self.assertEqual(await source.search("SIVR-438"), [])

    async def test_registry_records_http_xml_and_torznab_errors_as_failures(self):
        from services.magnet_search import search_magnets
        from sources.registry import SourceRegistry

        api_key = "top-secret-key"
        cases = [
            ("http", FakeHTTPResponse(text="unavailable", status_code=503)),
            ("xml", FakeHTTPResponse(text="<rss><channel>")),
            (
                "torznab",
                FakeHTTPResponse(
                    text=(
                        '<error code="100" '
                        f'description="credentials rejected: {api_key}" />'
                    )
                ),
            ),
        ]

        for label, response in cases:
            with self.subTest(label=label):
                RecordingAsyncClient.reset()
                RecordingAsyncClient.add_response("get", response)
                source = TorznabSource(
                    name="torznab",
                    base_url="http://indexer.test",
                    api_key=api_key,
                    enabled=True,
                )
                with patch.object(
                    SourceRegistry,
                    "_sources",
                    {"torznab": source, "working": _WorkingSource()},
                ), patch.object(
                    SourceRegistry, "_priority", ["torznab", "working"]
                ), patch.object(SourceRegistry, "_attempts", []), patch(
                    "database.source_attempt.record_source_attempt"
                ), self.patch_client():
                    result = await search_magnets("SIVR-438")

                self.assertEqual(len(result["items"]), 1)
                self.assertEqual(result["items"][0]["source"], "working")
                self.assertEqual(
                    [attempt["source"] for attempt in result["errors"]],
                    ["torznab"],
                )
                self.assertNotIn(api_key, result["errors"][0]["error"])

    async def test_builds_url_for_direct_api_base(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss><channel></channel></rss>""")
        source = TorznabSource(
            kind="prowlarr",
            base_url="http://prowlarr.test/1/api",
            api_key="secret",
            categories="5000,5070",
            limit=7,
            enabled=True,
        )

        with self.patch_client():
            await source.search("SIVR-438")

        get_call = [call for call in RecordingAsyncClient.calls if call["method"] == "get"][0]
        self.assertEqual(get_call["url"], "http://prowlarr.test/1/api")
        self.assertEqual(get_call["kwargs"]["headers"]["X-Api-Key"], "secret")
        self.assertEqual(
            get_call["kwargs"]["params"],
            {"t": "search", "q": "SIVR-438", "limit": 7, "cat": "5000,5070"},
        )

    async def test_jackett_requires_query_api_key_instead_of_header_only_auth(self):
        api_key = "jackett-query-secret"

        def jackett_stub(**kwargs):
            request = kwargs["kwargs"]
            self.assertEqual(request["params"]["apikey"], api_key)
            self.assertNotIn("X-Api-Key", request.get("headers") or {})
            return FakeHTTPResponse(text="<rss><channel /></rss>")

        RecordingAsyncClient.add_response("get", jackett_stub)
        source = TorznabSource(
            kind="jackett",
            base_url="http://jackett.test",
            api_key=api_key,
            indexer="all",
            enabled=True,
        )

        with self.patch_client():
            self.assertEqual(await source.search("MIAA-784"), [])

    async def test_generic_torznab_uses_standard_query_api_key(self):
        api_key = "generic-query-secret"
        self.queue_response("<rss><channel /></rss>")
        source = TorznabSource(
            kind="torznab",
            base_url="http://generic.test/api",
            api_key=api_key,
            enabled=True,
        )

        with self.patch_client():
            self.assertEqual(await source.search("MIAA-784"), [])

        get_call = [
            call for call in RecordingAsyncClient.calls if call["method"] == "get"
        ][0]
        self.assertEqual(get_call["kwargs"]["params"]["apikey"], api_key)
        self.assertNotIn("X-Api-Key", get_call["kwargs"].get("headers") or {})

    async def test_jackett_query_key_never_reaches_registry_attempt_errors(self):
        from services.magnet_search import search_magnets
        from sources.registry import SourceRegistry

        api_key = "jackett-query-secret"

        def failing_stub(**kwargs):
            request = kwargs["kwargs"]
            self.assertEqual(request["params"]["apikey"], api_key)
            raise RuntimeError(
                f"GET http://jackett.test/api?apikey={api_key} failed"
            )

        RecordingAsyncClient.add_response("get", failing_stub)
        source = TorznabSource(
            name="jackett",
            kind="jackett",
            base_url="http://jackett.test",
            api_key=api_key,
            enabled=True,
        )
        with patch.object(
            SourceRegistry, "_sources", {"jackett": source}
        ), patch.object(
            SourceRegistry, "_priority", ["jackett"]
        ), patch.object(SourceRegistry, "_attempts", []), patch(
            "database.source_attempt.record_source_attempt"
        ), self.patch_client():
            result = await search_magnets("MIAA-784")

        self.assertEqual([row["source"] for row in result["errors"]], ["jackett"])
        self.assertNotIn(api_key, str(result))

    async def test_root_url_tries_prowlarr_then_jackett_paths_with_safe_auth(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss>
  <channel>
    <item>
      <title>MIAA-784</title>
      <torznab:attr xmlns:torznab="http://torznab.com/schemas/2015/feed" name="magneturl" value="magnet:?xt=urn:btih:ABC" />
    </item>
  </channel>
</rss>""")
        source = TorznabSource(
            kind="prowlarr",
            base_url="http://prowlarr.test",
            api_key="secret",
            indexer="7",
            enabled=True,
        )

        with self.patch_client():
            results = await source.search("MIAA-784")

        get_call = [call for call in RecordingAsyncClient.calls if call["method"] == "get"][0]
        self.assertEqual(get_call["url"], "http://prowlarr.test/api/v1/indexer/7/newznab")
        self.assertEqual(get_call["kwargs"]["headers"]["X-Api-Key"], "secret")
        self.assertNotIn("apikey", get_call["kwargs"]["params"])
        self.assertEqual(results[0]["magnet"], "magnet:?xt=urn:btih:ABC")


class TorznabRegistrationTest(unittest.TestCase):
    def test_register_all_sources_adds_enabled_torznab_configs(self):
        from sources import register_all_sources
        from sources.registry import SourceRegistry

        configs = [
            {
                "enabled": True,
                "name": "primary-indexer",
                "base_url": "http://prowlarr.test",
                "api_key": "secret",
                "indexer": "all",
                "categories": "",
                "limit": 20,
                "timeout": 15,
            }
        ]

        with patch.object(SourceRegistry, "_sources", {}), \
             patch.object(SourceRegistry, "_priority", []), \
             patch("sources.config", SimpleNamespace(enabled_torznab_configs=configs)):
            register_all_sources()

            source = SourceRegistry.get("primary-indexer")
            self.assertIsInstance(source, TorznabSource)
            self.assertEqual(source.base_url, "http://prowlarr.test")
            self.assertIn("primary-indexer", SourceRegistry.priority())

    def test_register_all_sources_removes_stale_torznab_configs(self):
        from sources import register_all_sources
        from sources.registry import SourceRegistry

        stale = TorznabSource(
            name="old-indexer",
            base_url="http://old.test",
            api_key="secret",
            enabled=True,
        )

        with patch.object(SourceRegistry, "_sources", {"old-indexer": stale}), \
             patch.object(SourceRegistry, "_priority", ["old-indexer"]), \
             patch("sources.config", SimpleNamespace(enabled_torznab_configs=[])):
            register_all_sources()

            self.assertIsNone(SourceRegistry.get("old-indexer"))
            self.assertNotIn("old-indexer", SourceRegistry.priority())
