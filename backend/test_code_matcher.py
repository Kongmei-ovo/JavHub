from __future__ import annotations

import unittest

from modules.code_matcher import (
    code_matches_text,
    extract_code,
    normalize_code,
    parse_code,
)


class NormalizeAndParseTest(unittest.TestCase):
    def test_normalize_strips_separators_and_uppers(self):
        self.assertEqual(normalize_code(" abc-123 "), "ABC123")
        self.assertEqual(normalize_code("ABC_123-C"), "ABC123C")
        self.assertEqual(normalize_code(None), "")

    def test_parse_returns_prefix_number_suffix(self):
        self.assertEqual(parse_code("abc-123"), ("ABC", "123", ""))
        self.assertEqual(parse_code("ABC-123c"), ("ABC", "123", "C"))
        self.assertIsNone(parse_code(""))
        self.assertIsNone(parse_code("123-ABC"))


class CodeMatchesTextTest(unittest.TestCase):
    def test_exact_filename_matches(self):
        self.assertTrue(code_matches_text("SIVR-438", "/media/SIVR-438.mp4"))
        self.assertTrue(code_matches_text("SIVR-438", "Movie SIVR-438"))
        self.assertTrue(code_matches_text("SIVR-438", "sivr438.mkv"))

    def test_rejects_longer_number(self):
        # ABC-123 must not match a file containing ABC-1234
        self.assertFalse(code_matches_text("ABC-123", "ABC-1234.mp4"))
        self.assertFalse(code_matches_text("ABC-123", "/media/ABC-1234 4K.mkv"))

    def test_rejects_longer_prefix(self):
        # ABC-123 must not match XABC-123 / YABC-123
        self.assertFalse(code_matches_text("ABC-123", "XABC-123.mp4"))
        self.assertFalse(code_matches_text("ABC-123", "stuff-XABC-123"))

    def test_accepts_decorated_suffix(self):
        # Bare code may carry trailing tags like -C, -4K, .HACK
        self.assertTrue(code_matches_text("ABC-123", "ABC-123-C.mp4"))
        self.assertTrue(code_matches_text("ABC-123", "ABC-123-4K.mp4"))
        self.assertTrue(code_matches_text("ABC-123", "ABC-123.hack.mp4"))

    def test_suffix_in_code_must_match(self):
        # If the lookup code carries a suffix, only that suffix matches
        self.assertTrue(code_matches_text("ABC-123C", "ABC-123-C.mp4"))
        self.assertTrue(code_matches_text("ABC-123C", "ABC-123c.mp4"))
        self.assertFalse(code_matches_text("ABC-123D", "ABC-123-C.mp4"))

    def test_handles_missing_separator_and_underscore(self):
        self.assertTrue(code_matches_text("SIVR-438", "[SIVR_438] title.mkv"))
        self.assertTrue(code_matches_text("SIVR-438", "SIVR438 - title.mkv"))

    def test_empty_inputs(self):
        self.assertFalse(code_matches_text("", "ABC-123"))
        self.assertFalse(code_matches_text("ABC-123", ""))
        self.assertFalse(code_matches_text(None, "ABC-123"))


class ExtractCodeTest(unittest.TestCase):
    def test_extracts_first_canonical_code(self):
        self.assertEqual(extract_code("Movie ABC-123 (1080p).mp4"), "ABC-123")
        self.assertEqual(extract_code("[SIVR-438] Title.mkv"), "SIVR-438")

    def test_extracts_greedily_on_digits(self):
        # ABC-1234 must not be truncated to ABC-123
        self.assertEqual(extract_code("ABC-1234 4K.mp4"), "ABC-1234")

    def test_extracts_suffix(self):
        self.assertEqual(extract_code("ABC-123C.mp4"), "ABC-123C")

    def test_returns_none_when_absent(self):
        self.assertIsNone(extract_code("no code here.mp4"))
        self.assertIsNone(extract_code(""))


if __name__ == "__main__":
    unittest.main()
