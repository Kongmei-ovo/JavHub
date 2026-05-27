from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sources.torznab_source import TorznabSource
from test_support.httpx import FakeHTTPResponse, RecordingAsyncClient


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

    async def test_ignores_torznab_error_response(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<error code="100" description="Incorrect user credentials" />""")
        source = TorznabSource(base_url="http://indexer.test", api_key="secret", enabled=True)

        with self.patch_client():
            results = await source.search("SIVR-438")

        self.assertEqual(results, [])

    async def test_builds_url_for_direct_api_base(self):
        self.queue_response("""<?xml version="1.0" encoding="UTF-8"?>
<rss><channel></channel></rss>""")
        source = TorznabSource(
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
