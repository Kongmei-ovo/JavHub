from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix="/api/proxy", tags=["proxy"])


@router.get("/image")
async def proxy_image(url: str = Query(...)):
    """代理图片请求，避免CORS问题"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                resp.aiter_bytes(),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                }
            )
    except Exception as e:
        return StreamingResponse(
            iter([b""]),
            media_type="image/png",
            status_code=500
        )
