"""Data quality overview API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from services.data_quality import build_data_quality_overview
from services.supplement_repair_progress import get_supplement_repair_progress

router = APIRouter(prefix="/api/v1/data-quality", tags=["data-quality"])


@router.get("/overview")
async def data_quality_overview(limit: int = Query(8, ge=1, le=50)) -> dict[str, Any]:
    repair_progress = await get_supplement_repair_progress()
    if repair_progress:
        return build_data_quality_overview(limit=limit, repair_progress=repair_progress)
    return build_data_quality_overview(limit=limit)
