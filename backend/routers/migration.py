from __future__ import annotations

import logging

from fastapi import APIRouter

from services.library_import import emby_resource_parity, import_115_library

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/migration", tags=["migration"])


@router.post("/backfill-115")
async def backfill_115_library():
    """One-time: register historical 115 movie folders into movie_resources."""
    return await import_115_library()


@router.get("/parity")
async def emby_parity_report():
    """Emby↔resource parity. ``only_in_emby`` must be empty before de-Emby (P6)."""
    return emby_resource_parity()
