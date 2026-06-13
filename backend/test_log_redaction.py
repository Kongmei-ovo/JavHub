from __future__ import annotations

import logging
import unittest


class SensitiveLogFilterTests(unittest.TestCase):
    def test_redacts_query_tokens_and_authorization_values(self):
        from services.log_redaction import SensitiveDataFilter

        record = logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            __file__,
            1,
            '%s "%s %s HTTP/%s" %d Authorization=%s',
            (
                "127.0.0.1",
                "GET",
                "/Videos/x/original.mp4?api_key=secret&token=other",
                "1.1",
                302,
                "Bearer top-secret",
            ),
            None,
        )
        SensitiveDataFilter().filter(record)
        rendered = record.getMessage()
        self.assertNotIn("secret", rendered)
        self.assertNotIn("other", rendered)
        self.assertNotIn("top-secret", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_redacts_mediabrowser_header_and_api_key_variants(self):
        from services.log_redaction import redact_sensitive

        rendered = redact_sensitive(
            'GET /Items?apiKey=query-secret&X-MediaBrowser-Token=header-secret '
            'Authorization: MediaBrowser Client="Infuse", Token="auth-secret"'
        )
        self.assertNotIn("query-secret", rendered)
        self.assertNotIn("header-secret", rendered)
        self.assertNotIn("auth-secret", rendered)
        self.assertEqual(rendered.count("[REDACTED]"), 3)


if __name__ == "__main__":
    unittest.main()
