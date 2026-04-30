from fastapi import APIRouter
from modules.info_client import get_info_client
from database import get_translation
from services.translation import _translate_item

router = APIRouter(prefix="/api/v1/makers", tags=["makers"])

@router.get("")
async def list_makers():
    client = get_info_client()
    makers_list = await client.list_makers()
    # 为每个 maker 注入翻译字段
    items = makers_list if isinstance(makers_list, list) else (makers_list.get("data", []) if isinstance(makers_list, dict) else [])
    if isinstance(items, list):
        for maker in items:
            maker_id = maker.get("id")
            if maker_id:
                trans = get_translation(f"maker:{maker_id}")
                if trans:
                    maker_map = trans.get("maker", {})
                    for name_key in ["name_ja", "name_en", "name"]:
                        orig = maker.get(name_key)
                        if orig:
                            maker[f"{name_key}_translated"] = _translate_item(orig, maker_map)
                            break
    return makers_list
