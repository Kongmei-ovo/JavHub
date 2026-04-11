from fastapi import APIRouter
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

@router.get("")
async def list_categories():
    client = get_info_client()
    return await client.list_categories()