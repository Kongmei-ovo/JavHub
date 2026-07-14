"""Small shared helpers for keeping credentials out of public source data."""
from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import (
    parse_qsl,
    quote,
    quote_plus,
    unquote_plus,
    urlencode,
    urlsplit,
    urlunsplit,
)


_SENSITIVE_QUERY_NAMES = frozenset(
    {
        "apikey",
        "jackettapikey",
        "passkey",
        "password",
        "passwd",
        "secret",
        "token",
        "accesstoken",
        "cookie",
        "authorization",
        "auth",
        "key",
    }
)
_URL_RE = re.compile(r"(?i)https?://[^\s<>\"']+")
_AUTHORIZATION_RE = re.compile(
    r"(?im)(\bauthorization\b\s*[:=]\s*)[^\r\n]+"
)
_COOKIE_RE = re.compile(r"(?im)(\bcookie\b\s*[:=]\s*)[^\r\n]+")
_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:jackett[_ -]?api[_ -]?key|api[_ -]?key|apikey|pass[_ -]?key|"
    r"password|passwd|secret|access[_ -]?token|token|key|auth)\b\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^&\s,;]+)"
)


def redact_sensitive_text(
    message: object,
    *,
    secrets: Iterable[str] = (),
) -> str:
    """Redact credentials from exception/attempt text without echoing values."""
    known_secrets = _known_secrets(secrets)
    text = str(message or "")
    text = _URL_RE.sub(
        lambda match: _redact_url_text(match.group(0), known_secrets),
        text,
    )
    text = _AUTHORIZATION_RE.sub(r"\1[redacted]", text)
    text = _COOKIE_RE.sub(r"\1[redacted]", text)
    text = _SENSITIVE_ASSIGNMENT_RE.sub(r"\1[redacted]", text)
    for secret in known_secrets:
        for representation in {
            secret,
            quote(secret, safe=""),
            quote_plus(secret, safe=""),
        }:
            if representation:
                text = text.replace(representation, "[redacted]")
    return text


def redact_attempt_rows(attempts: Iterable[dict]) -> list[dict]:
    rows = []
    for attempt in attempts or ():
        row = dict(attempt or {})
        if "error" in row:
            row["error"] = redact_sensitive_text(row.get("error"))
        rows.append(row)
    return rows


def redact_search_result(result: dict) -> dict:
    response = dict(result or {})
    if "attempts" in response:
        response["attempts"] = redact_attempt_rows(response.get("attempts") or [])
    if "errors" in response:
        response["errors"] = redact_attempt_rows(response.get("errors") or [])
    return response


def sanitize_source_item_uris(
    item: dict,
    *,
    secrets: Iterable[str] = (),
) -> dict | None:
    """Remove credential-bearing URIs, dropping rows with no safe download URI."""
    row = dict(item or {})
    known_secrets = _known_secrets(secrets)

    magnet = str(row.get("magnet") or "").strip()
    if magnet:
        if magnet.casefold().startswith("magnet:"):
            magnet = sanitize_magnet_uri(magnet, secrets=known_secrets)
        elif uri_contains_secret(magnet, secrets=known_secrets):
            magnet = ""
        if magnet:
            row["magnet"] = magnet
        else:
            row.pop("magnet", None)

    for key in ("torrent_url", "download_url"):
        uri = str(row.get(key) or "").strip()
        if not uri:
            row.pop(key, None)
            continue
        if uri_contains_secret(uri, secrets=known_secrets):
            row.pop(key, None)
        else:
            row[key] = uri

    if not _first_download_uri(row):
        return None
    return row


def sanitize_magnet_uri(
    uri: str,
    *,
    secrets: Iterable[str] = (),
) -> str:
    text = str(uri or "").strip()
    known_secrets = _known_secrets(secrets)
    try:
        parsed = urlsplit(text)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return ""
    if parsed.scheme.casefold() != "magnet" or parsed.username or parsed.password:
        return ""

    safe_pairs: list[tuple[str, str]] = []
    changed = False
    for key, value in pairs:
        if _is_sensitive_name(key):
            changed = True
            continue
        if _contains_known_secret(value, known_secrets):
            changed = True
            continue
        if _looks_like_uri(value) and uri_contains_secret(value, secrets=known_secrets):
            changed = True
            continue
        safe_pairs.append((key, value))
    if not safe_pairs:
        return ""
    if not changed:
        return text
    query = urlencode(safe_pairs, doseq=True, quote_via=quote, safe=":/")
    return urlunsplit(("magnet", "", parsed.path, query, parsed.fragment))


def uri_contains_secret(
    uri: str,
    *,
    secrets: Iterable[str] = (),
) -> bool:
    text = str(uri or "").strip()
    known_secrets = _known_secrets(secrets)
    if _contains_known_secret(text, known_secrets):
        return True
    try:
        parsed = urlsplit(text)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return True
    if parsed.username is not None or parsed.password is not None:
        return True
    for key, value in pairs:
        if _is_sensitive_name(key) or _contains_known_secret(value, known_secrets):
            return True
        if _looks_like_uri(value) and uri_contains_secret(value, secrets=known_secrets):
            return True
    return False


def _first_download_uri(item: dict) -> str:
    for key in ("magnet", "torrent_url", "download_url"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _known_secrets(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(str(value) for value in values if str(value or ""))


def _contains_known_secret(value: str, secrets: tuple[str, ...]) -> bool:
    decoded = unquote_plus(str(value or ""))
    return any(secret in value or secret in decoded for secret in secrets)


def _is_sensitive_name(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(name or "").casefold())
    return normalized in _SENSITIVE_QUERY_NAMES


def _looks_like_uri(value: str) -> bool:
    text = str(value or "").strip().casefold()
    return "://" in text or text.startswith(("magnet:", "http:", "https:"))


def _redact_url_text(uri: str, secrets: tuple[str, ...]) -> str:
    trailing = ""
    text = str(uri or "")
    while text and text[-1] in ".,);]":
        trailing = text[-1] + trailing
        text = text[:-1]
    try:
        parsed = urlsplit(text)
        hostname = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return "[redacted-url]" + trailing

    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if port is not None:
        netloc = f"{netloc}:{port}"

    safe_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if _is_sensitive_name(key):
            value = "[redacted]"
        elif _looks_like_uri(value):
            value = _redact_url_text(value, secrets)
        else:
            value = _replace_known_secrets(value, secrets)
        safe_pairs.append((key, value))
    query = urlencode(
        safe_pairs,
        doseq=True,
        quote_via=quote,
        safe=":/[]",
    )
    path = _replace_known_secrets(parsed.path, secrets)
    fragment = _replace_known_secrets(parsed.fragment, secrets)
    return urlunsplit(
        (parsed.scheme.casefold(), netloc, path, query, fragment)
    ) + trailing


def _replace_known_secrets(value: str, secrets: tuple[str, ...]) -> str:
    text = str(value or "")
    for secret in secrets:
        text = text.replace(secret, "[redacted]")
    return text
