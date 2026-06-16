"""Subtitle normalization for first-party + Emby playback.

JavHub downloads subtitle files alongside videos (srt/vtt/ass/ssa). Web players
and Emby clients consume WebVTT most reliably, so external subtitle resources are
served as VTT: srt/vtt pass through (header-normalized), ass/ssa are converted by
extracting dialogue and dropping styling (complex styling is not preserved).
"""
from __future__ import annotations

import re

VTT_HEADER = "WEBVTT"

# srt/vtt timestamp uses a comma for the millisecond separator in srt.
_SRT_TIME = re.compile(r"(\d{2}:\d{2}:\d{2}),(\d{1,3})")
# ASS inline override blocks like {\an8}, {\i1}.
_ASS_OVERRIDE = re.compile(r"\{[^}]*\}")


def _ensure_vtt_header(content: str) -> str:
    text = content.lstrip("﻿").lstrip()
    if text.upper().startswith("WEBVTT"):
        return text if text.endswith("\n") else text + "\n"
    return f"{VTT_HEADER}\n\n{text}".rstrip() + "\n"


def _srt_to_vtt(content: str) -> str:
    body = content.lstrip("﻿")
    body = _SRT_TIME.sub(r"\1.\2", body)  # 00:00:01,000 -> 00:00:01.000
    return f"{VTT_HEADER}\n\n{body.strip()}\n"


def _ass_timestamp(value: str) -> str:
    """ASS ``H:MM:SS.cc`` (centiseconds) -> VTT ``HH:MM:SS.mmm``."""
    match = re.match(r"\s*(\d+):(\d{2}):(\d{2})[.,](\d{1,2})\s*$", value)
    if not match:
        return "00:00:00.000"
    hours, minutes, seconds, centis = match.groups()
    millis = int(centis.ljust(2, "0")) * 10
    return f"{int(hours):02d}:{minutes}:{seconds}.{millis:03d}"


def _ass_to_vtt(content: str) -> str:
    lines = content.splitlines()
    fields: list[str] = []
    cues: list[str] = []
    in_events = False
    for raw in lines:
        line = raw.strip()
        if line.lower().startswith("[events]"):
            in_events = True
            continue
        if line.startswith("[") and line.endswith("]"):
            in_events = False
            continue
        if not in_events:
            continue
        if line.lower().startswith("format:"):
            fields = [part.strip().lower() for part in line.split(":", 1)[1].split(",")]
            continue
        if not line.lower().startswith("dialogue:"):
            continue
        payload = line.split(":", 1)[1]
        # Text is the last field but may itself contain commas, so split with a cap.
        parts = payload.split(",", len(fields) - 1) if fields else payload.split(",", 9)
        if not fields or len(parts) < len(fields):
            continue
        record = dict(zip(fields, parts))
        start = _ass_timestamp(record.get("start", ""))
        end = _ass_timestamp(record.get("end", ""))
        text = record.get("text", "")
        text = _ASS_OVERRIDE.sub("", text).replace("\\N", "\n").replace("\\n", "\n").strip()
        if not text:
            continue
        cues.append(f"{start} --> {end}\n{text}")
    return f"{VTT_HEADER}\n\n" + "\n\n".join(cues) + ("\n" if cues else "")


def to_webvtt(content: str, source_format: str) -> str:
    fmt = str(source_format or "").lower().lstrip(".")
    text = str(content or "")
    if fmt == "vtt":
        return _ensure_vtt_header(text)
    if fmt == "srt":
        return _srt_to_vtt(text)
    if fmt in {"ass", "ssa"}:
        return _ass_to_vtt(text)
    return _ensure_vtt_header(text)


def subtitle_language(name: str) -> str:
    """Best-effort 3-letter language guess from the file name for client display."""
    lowered = str(name or "").lower()
    if any(token in lowered for token in ("中文", "中字", "简", "繁", "chs", "cht", ".zh", "chinese", "_zh")):
        return "chi"
    if any(token in lowered for token in ("日本", "日语", ".ja", "jpn", "japanese")):
        return "jpn"
    if any(token in lowered for token in ("english", "eng", ".en")):
        return "eng"
    return "und"
