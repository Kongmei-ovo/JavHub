from fastapi import APIRouter
from modules.info_client import get_info_client
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

@router.get("")
async def list_categories():
    client = get_info_client()
    categories = await client.list_categories()
    # 为每个 category 注入翻译字段
    if isinstance(categories, list):
        await get_translator_service().translate_entities(
            categories,
            entity_type="category",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )
    return categories
