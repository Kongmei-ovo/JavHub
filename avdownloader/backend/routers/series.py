from fastapi import APIRouter
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/series", tags=["series"])

@router.get("")
async def list_series():
    client = get_info_client()
    return await client.list_series()