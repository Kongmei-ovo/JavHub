from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])


@router.get("/{content_id}")
async def get_stream_url(content_id: str) -> dict[str, Any]:
    """获取影片的 m3u8 播放地址"""
    from sources.m3u8_source import M3U8Source
    source = M3U8Source()
    result = await source.search_m3u8(content_id)
    if not result:
        raise HTTPException(status_code=404, detail="未找到播放地址")
    return {"data": result}


class TransferRequest(BaseModel):
    m3u8_url: str
    content_id: str
    title: Optional[str] = ""


@router.post("/{content_id}/transfer")
async def transfer_to_cloud(content_id: str, req: TransferRequest) -> dict[str, Any]:
    """m3u8 转存到云盘（通过 AList 上传）"""
    # TODO: 实现 m3u8 下载并上传到 AList 的逻辑
    raise HTTPException(status_code=501, detail="转存功能尚未实现")
