from fastapi import APIRouter, Query
from modules.info_client import get_info_client
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/labels", tags=["labels"])


@router.get("")
async def list_labels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
):
    client = get_info_client()
    labels_list = await client.list_labels(q=q)
    items = labels_list if isinstance(labels_list, list) else []
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    await get_translator_service().translate_entities(
        page_items,
        entity_type="label",
        keys=["name_ja", "name_en", "name"],
        allow_network=False,
    )

    return {
        "data": page_items,
        "page": page,
        "page_size": page_size,
        "total_count": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
