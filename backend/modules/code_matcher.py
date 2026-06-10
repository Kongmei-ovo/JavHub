"""Unified JAV content-ID parsing and matching.

Single source of truth for "does this code appear in this filename/title".
Replaces three earlier ad-hoc implementations that disagreed on edge cases
(ABC-123 vs ABC-1234, suffixed -C/-4K, embedded XABC-123, etc.).

Rules:
- ``normalize_code`` strips to ``[A-Z0-9]+`` upper-case (canonical compact form).
- ``parse_code`` splits a compact code into (prefix, number, suffix); the
  suffix is the optional trailing alpha group (e.g. ``ABC-123C`` → suffix=C).
- ``code_matches_text`` accepts the code only when it appears bounded by
  non-alphanumerics (no ``XABC-123`` / ``ABC-1234`` false-positives) and,
  when present, the suffix letters match. A bare ``ABC-123`` still accepts
  ``ABC-123-C`` / ``ABC-123.HACK`` style decorations.
- ``extract_code`` pulls the first plausible code from a name; it requires
  the same boundary discipline so ``Movie ABC-1234 4K`` returns ``ABC-1234``,
  not ``ABC-123``.
"""

from __future__ import annotations

import re
from typing import Iterable

__all__ = [
    "normalize_code",
    "parse_code",
    "code_matches_text",
    "extract_code",
    "video_code",
    "candidate_content_id",
]


_NORMALIZE_RE = re.compile(r"[^A-Z0-9]")
_CODE_PARTS_RE = re.compile(r"^([A-Z]+)(\d+)([A-Z]*)$")
# Extraction is intentionally stricter than parsing: free-form text contains
# noise like "mp-4" or "h-264" that should not be picked up. Real JAV codes
# always have a 2+ letter prefix and a 2+ digit number.
_EXTRACT_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2,})[-_\s]?(\d{2,})([A-Z]*)(?![A-Z0-9])")


def normalize_code(value: str | None) -> str:
    """Strip everything except ``[A-Z0-9]`` and upper-case the result."""
    return _NORMALIZE_RE.sub("", str(value or "").upper())


def parse_code(value: str | None) -> tuple[str, str, str] | None:
    """Parse a code into (prefix, number, suffix). Returns ``None`` on no match."""
    compact = normalize_code(value)
    if not compact:
        return None
    match = _CODE_PARTS_RE.match(compact)
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)


def code_matches_text(code: str | None, text: str | None) -> bool:
    """True iff ``code`` appears in ``text`` as an isolated token.

    Boundary rules:
    - the prefix may not be preceded by ``[A-Z0-9]`` (rejects ``XABC-123``)
    - the number/suffix may not be followed by ``[0-9]`` (rejects ``ABC-1234``)
    - separators between prefix/number/suffix may be ``-``, ``_``, whitespace,
      or absent — Emby filenames are inconsistent.
    - any trailing alpha tag (``-C``, ``-4K``) is allowed when the code itself
      carries no suffix, but ignored when it does.
    """
    parts = parse_code(code)
    if not parts or not text:
        return False
    prefix, number, suffix = parts
    haystack = text.upper()

    if suffix:
        suffix_pattern = rf"[-_\s]*{re.escape(suffix)}"
    else:
        suffix_pattern = r"(?:[-_\s]+(?=[A-Z])[A-Z0-9]+)?"

    pattern = (
        rf"(?<![A-Z0-9]){re.escape(prefix)}[-_\s]*{re.escape(number)}"
        rf"{suffix_pattern}(?![A-Z0-9])"
    )
    return bool(re.search(pattern, haystack))


def extract_code(name: str | None) -> str | None:
    """Pull the first plausible code from a free-form name.

    Greedy on digits — given ``ABC-1234``, returns ``ABC-1234`` (not ``ABC-123``).
    Returns ``None`` if nothing matches the canonical shape.
    """
    if not name:
        return None
    match = _EXTRACT_RE.search(name.upper())
    if not match:
        return None
    prefix, number, suffix = match.group(1), match.group(2), match.group(3)
    return f"{prefix}-{number}{suffix}" if suffix else f"{prefix}-{number}"


def video_code(video: dict) -> str:
    """Return the most authoritative raw code for a JavInfo video record."""
    return str(
        video.get("dvd_id")
        or video.get("content_id")
        or video.get("canonical_number")
        or ""
    ).strip()


def candidate_content_id(video: dict) -> str:
    """Return the stable local key (matches database.download_candidate)."""
    return str(
        video.get("content_id")
        or video.get("dvd_id")
        or video.get("canonical_number")
        or video.get("id")
        or ""
    ).strip()


def code_matches_any(code: str | None, texts: Iterable[str | None]) -> bool:
    return any(code_matches_text(code, text) for text in texts if text)
