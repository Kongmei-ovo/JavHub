from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from database.source_attempt import source_health_summary

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@router.get("/health")
async def get_sources_health() -> list[dict[str, Any]]:
    return await asyncio.to_thread(source_health_summary, window_minutes=60)
