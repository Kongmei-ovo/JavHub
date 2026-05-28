from __future__ import annotations

from math import ceil
from typing import Any


def page_response(
    data: list[Any],
    *,
    page: int = 1,
    page_size: int = 20,
    total_count: int | None = None,
    total_pages: int | None = None,
) -> dict[str, Any]:
    count = len(data) if total_count is None else total_count
    pages = max(1, ceil(count / page_size)) if total_pages is None else total_pages
    return {
        "data": data,
        "page": page,
        "page_size": page_size,
        "total_count": count,
        "total_pages": pages,
    }
