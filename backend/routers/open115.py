from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.open115 import Open115AuthRequired, Open115Error, open115_client

router = APIRouter(prefix="/api/v1/open115", tags=["open115"])


class ImportRefreshTokenRequest(BaseModel):
    refresh_token: str


class OfflineAddRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)
    cid: str = "0"


class OfflineDeleteRequest(BaseModel):
    info_hash: str
    del_source: bool = False


class OfflineClearRequest(BaseModel):
    flag: int = 0


def _protocol_error(exc: Open115Error) -> HTTPException:
    if isinstance(exc, Open115AuthRequired):
        return HTTPException(
            status_code=409,
            detail={"message": exc.api_message, "code": "open115_unbound"},
        )
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


@router.get("/offline/quota")
async def offline_quota():
    try:
        return await open115_client.offline_quota()
    except Open115Error as exc:
        raise _protocol_error(exc) from exc


@router.get("/offline/tasks")
async def offline_tasks(page: int = Query(1, ge=1)):
    try:
        return await open115_client.list_offline_tasks(page)
    except Open115Error as exc:
        raise _protocol_error(exc) from exc


@router.post("/offline/add")
async def offline_add(req: OfflineAddRequest):
    urls = [str(item).strip() for item in req.urls if str(item or "").strip()]
    if not urls:
        raise HTTPException(status_code=422, detail="urls 不能为空")
    from services.downloader import downloader_service

    try:
        result = await downloader_service.create_open115_offline_tasks(urls, req.cid or "0")
    except Open115Error as exc:
        raise _protocol_error(exc) from exc
    try:
        result["quota"] = await open115_client.offline_quota()
    except Open115Error:
        result["quota"] = None
    return result


@router.post("/offline/delete")
async def offline_delete(req: OfflineDeleteRequest):
    try:
        await open115_client.delete_offline_task(req.info_hash, del_source=req.del_source)
    except Open115Error as exc:
        raise _protocol_error(exc) from exc
    return {"ok": True}


@router.post("/offline/clear")
async def offline_clear(req: OfflineClearRequest):
    try:
        await open115_client.clear_offline_tasks(req.flag)
    except Open115Error as exc:
        raise _protocol_error(exc) from exc
    return {"ok": True}
