from fastapi import APIRouter
from config import config

router = APIRouter(prefix="/api", tags=["config"])

@router.get("/config")
async def get_config():
    return config.get_all()

@router.put("/config")
async def update_config(new_config: dict):
    config.update(new_config)
    return {"success": True}
