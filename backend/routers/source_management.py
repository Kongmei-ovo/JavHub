from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeVar

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.magnet_search import search_magnets_for_item
from services.secret_redactor import redact_search_result
from services.source_manager import (
    SourceConfigError,
    create_source,
    delete_source,
    get_source_snapshot,
    source_runtime_name,
    update_source,
)


router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


class SourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["torznab", "avdb"]
    name: str = ""
    kind: Literal["prowlarr", "jackett", "torznab"] = "prowlarr"
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""
    indexer: str = "all"
    categories: str = ""
    limit: int = Field(default=20, ge=1, le=100)
    timeout: int = Field(default=15, ge=1, le=60)


class SourceSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(min_length=1, max_length=128)
    source_id: str = "auto"


ResultT = TypeVar("ResultT")


def _service_call(operation: Callable[..., ResultT], *args: Any) -> ResultT:
    try:
        return operation(*args)
    except SourceConfigError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/config")
def source_config():
    return get_source_snapshot()


@router.post("")
def add_source(body: SourcePayload):
    return _service_call(create_source, body.model_dump())


@router.post("/search")
async def search_sources(body: SourceSearchRequest):
    names = None
    if body.source_id != "auto":
        runtime_name = source_runtime_name(body.source_id)
        if not runtime_name:
            raise HTTPException(status_code=404, detail="下载源不存在或未启用")
        names = [runtime_name]
    result = await search_magnets_for_item(
        {"dvd_id": body.keyword},
        source_names=names,
    )
    return redact_search_result(result)


@router.put("/{source_id}")
def edit_source(source_id: str, body: SourcePayload):
    return _service_call(update_source, source_id, body.model_dump())


@router.delete("/{source_id}")
def remove_source(source_id: str):
    return _service_call(delete_source, source_id)
