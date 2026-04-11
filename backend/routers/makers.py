from fastapi import APIRouter
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/makers", tags=["makers"])

@router.get("")
async def list_makers():
    client = get_info_client()
    return await client.list_makers()