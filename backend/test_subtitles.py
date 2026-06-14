from __future__ import annotations

import unittest

from services.subtitles import subtitle_language, to_webvtt


class SubtitleConversionTests(unittest.TestCase):
    def test_srt_becomes_vtt_with_dot_milliseconds(self):
        srt = "1\n00:00:01,000 --> 00:00:02,500\nHello\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld\n"
        vtt = to_webvtt(srt, "srt")
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:01.000 --> 00:00:02.500", vtt)
        self.assertNotIn(",", vtt.split("\n", 1)[1])  # commas gone from timestamps
        self.assertIn("Hello", vtt)
        self.assertIn("World", vtt)

    def test_vtt_passthrough_keeps_single_header(self):
        vtt_in = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi\n"
        out = to_webvtt(vtt_in, "vtt")
        self.assertEqual(out.count("WEBVTT"), 1)
        self.assertIn("Hi", out)

    def test_headerless_vtt_gets_header(self):
        out = to_webvtt("00:00:01.000 --> 00:00:02.000\nHi\n", "vtt")
        self.assertTrue(out.startswith("WEBVTT"))

    def test_ass_dialogue_is_extracted_and_styling_stripped(self):
        ass = (
            "[Script Info]\nTitle: x\n\n"
            "[V4+ Styles]\nFormat: Name\nStyle: Default\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,{\\an8}你好,世界\n"
            "Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,line two\\Nsecond\n"
        )
        vtt = to_webvtt(ass, "ass")
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:01.000 --> 00:00:02.500", vtt)
        self.assertIn("你好,世界", vtt)  # comma inside text preserved
        self.assertNotIn("{", vtt)  # override block stripped
        self.assertIn("line two\nsecond", vtt)  # \N -> newline

    def test_language_guess(self):
        self.assertEqual(subtitle_language("ABC-123.中文.srt"), "chi")
        self.assertEqual(subtitle_language("ABC-123.jpn.ass"), "jpn")
        self.assertEqual(subtitle_language("ABC-123.english.vtt"), "eng")
        self.assertEqual(subtitle_language("ABC-123.srt"), "und")


if __name__ == "__main__":
    unittest.main()
