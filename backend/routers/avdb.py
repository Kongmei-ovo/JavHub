from __future__ import annotations

from fastapi import APIRouter

from config import config
from database.avdb import get_avdb_status


router = APIRouter(prefix="/api/v1/avdb", tags=["avdb"])


@router.get("/status")
def avdb_status() -> dict:
    return {
        "enabled": config.avdb_enabled,
        "sync_enabled": config.avdb_sync_enabled,
        **get_avdb_status(),
    }
