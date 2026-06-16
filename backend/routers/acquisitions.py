from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services import acquisition
from services.emby_auth import require_app_token

logger = logging.getLogger(__name__)

# Two path families share one router: per-movie start under /movies, and
# per-session control under /acquisitions. Single-user authed like playback.
router = APIRouter(
    prefix="/api/v1", tags=["acquisitions"], dependencies=[Depends(require_app_token)]
)


class StartAcquisitionBody(BaseModel):
    auto: bool = True
    trigger: str = "user"
    title: str | None = None


class SelectOptionBody(BaseModel):
    index: int | None = None
    magnet: str | None = None
    confirm: bool = False


def _raise_for(exc: ValueError) -> None:
    message = str(exc)
    status_code = 404 if ("not found" in message or "不存在" in message) else 400
    raise HTTPException(status_code=status_code, detail=message)


@router.post("/movies/{movie_id}/acquisitions")
async def start_movie_acquisition(movie_id: str, body: StartAcquisitionBody | None = None):
    payload = body or StartAcquisitionBody()
    try:
        return await acquisition.start_acquisition(
            movie_id, auto=payload.auto, trigger=payload.trigger, title=payload.title
        )
    except ValueError as exc:
        _raise_for(exc)


@router.get("/acquisitions/{session_id}")
async def get_acquisition(session_id: int):
    snapshot = acquisition.session_snapshot(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="获取会话不存在")
    return snapshot


@router.post("/acquisitions/{session_id}/select")
async def select_acquisition_option(session_id: int, body: SelectOptionBody):
    try:
        return await acquisition.select_option(
            session_id, index=body.index, magnet=body.magnet, confirm=body.confirm
        )
    except ValueError as exc:
        _raise_for(exc)


@router.post("/acquisitions/{session_id}/retry")
async def retry_acquisition(session_id: int):
    try:
        return await acquisition.retry(session_id)
    except ValueError as exc:
        _raise_for(exc)


@router.post("/acquisitions/{session_id}/stop-waiting")
async def stop_waiting_acquisition(session_id: int):
    try:
        return acquisition.stop_waiting(session_id)
    except ValueError as exc:
        _raise_for(exc)
