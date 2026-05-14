from fastapi import APIRouter
from modules.info_client import get_info_client
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/makers", tags=["makers"])

@router.get("")
async def list_makers():
    client = get_info_client()
    makers_list = await client.list_makers()
    # 为每个 maker 注入翻译字段
    items = makers_list if isinstance(makers_list, list) else (makers_list.get("data", []) if isinstance(makers_list, dict) else [])
    if isinstance(items, list):
        await get_translator_service().translate_entities(
            items,
            entity_type="maker",
            keys=["name_ja", "name_en", "name"],
        )
    return makers_list
