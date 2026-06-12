from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.open115 import Open115Error, open115_client

router = APIRouter(prefix="/api/v1/open115", tags=["open115"])


class ImportRefreshTokenRequest(BaseModel):
    refresh_token: str


def _protocol_error(exc: Open115Error) -> HTTPException:
    return HTTPException(status_code=502, detail=exc.api_message)


@router.get("/status")
async def get_status():
    return open115_client.status()


@router.post("/auth/start")
async def start_auth():
    try:
        result = await open115_client.start_device_auth()
    except Open115Error as exc:
        raise _protocol_error(exc) from exc
    return {
        **result,
        "qrcode_image_url": open115_client.qrcode_image_url(result["uid"]),
    }


@router.get("/auth/{uid}")
async def poll_auth(uid: str):
    try:
        return await open115_client.poll_device_auth(uid)
    except Open115Error as exc:
        raise _protocol_error(exc) from exc


@router.post("/auth/import")
async def import_auth(req: ImportRefreshTokenRequest):
    try:
        return await open115_client.import_refresh_token(req.refresh_token)
    except Open115Error as exc:
        raise _protocol_error(exc) from exc


@router.post("/test")
async def test_connection():
    try:
        return await open115_client.test_connection()
    except Open115Error as exc:
        raise _protocol_error(exc) from exc


@router.post("/unbind")
async def unbind():
    try:
        open115_client.unbind()
    except Open115Error as exc:
        raise HTTPException(status_code=409, detail=exc.api_message) from exc
    return {"bound": False}
