"""Logging helpers that keep bearer tokens and signed URLs out of logs."""
from __future__ import annotations

import logging
import re
from typing import Any


_QUERY_SECRET = re.compile(
    r"(?i)([?&](?:api_?key|token|access_token|x-emby-token|x-mediabrowser-token)=)[^&\s\"]+"
)
_AUTH_SECRET = re.compile(
    r"(?i)(authorization\s*[=:]\s*)(?:bearer|emby)\s+[^\s,\"]+"
)
_BEARER_SECRET = re.compile(r"(?i)\b(Bearer)\s+[A-Za-z0-9._~+/=-]+")
_TOKEN_ASSIGNMENT = re.compile(
    r'(?i)(\bToken\s*=\s*)(?:"[^"]*"|[^,\s]+)'
)


def redact_sensitive(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = _QUERY_SECRET.sub(r"\1[REDACTED]", value)
    value = _AUTH_SECRET.sub(r"\1[REDACTED]", value)
    value = _BEARER_SECRET.sub(r"\1 [REDACTED]", value)
    return _TOKEN_ASSIGNMENT.sub(r"\1[REDACTED]", value)


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not record.args:
            record.msg = redact_sensitive(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact_sensitive(value) for value in record.args)
        elif isinstance(record.args, dict):
            record.args = {
                key: redact_sensitive(value)
                for key, value in record.args.items()
            }
        return True


_FILTER = SensitiveDataFilter()


def install_sensitive_log_filter() -> None:
    for logger_name in ("", "uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        if not any(isinstance(item, SensitiveDataFilter) for item in logger.filters):
            logger.addFilter(_FILTER)
        for handler in logger.handlers:
            if not any(isinstance(item, SensitiveDataFilter) for item in handler.filters):
                handler.addFilter(_FILTER)
