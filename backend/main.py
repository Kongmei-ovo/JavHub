import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db

# 导入新模块化路由
from routers.videos import router as videos_router
from routers.actresses import router as actresses_router
from routers.makers import router as makers_router
from routers.series import router as series_router
from routers.categories import router as categories_router
from routers.downloads import router as downloads_router
from routers.subscriptions import router as subscriptions_router
from routers.missing import router as missing_router
from routers.duplicates import router as duplicates_router
from routers.config import router as config_router
from routers.logs import router as logs_router
from routers.health import router as health_router

app = FastAPI(title="AV Downloader API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB
init_db()

# Register routers
app.include_router(videos_router)
app.include_router(actresses_router)
app.include_router(makers_router)
app.include_router(series_router)
app.include_router(categories_router)
app.include_router(downloads_router)
app.include_router(subscriptions_router)
app.include_router(missing_router)
app.include_router(duplicates_router)
app.include_router(config_router)
app.include_router(logs_router)
app.include_router(health_router)


@app.on_event("startup")
async def startup_event():
    """启动时运行"""
    try:
        from scheduler.tasks import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"Failed to start scheduler: {e}")

    # 注册下载源插件
    try:
        from sources import register_all_sources
        register_all_sources()
    except Exception as e:
        print(f"Failed to register sources: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时运行"""
    try:
        from scheduler.tasks import stop_scheduler
        stop_scheduler()
    except Exception as e:
        print(f"Failed to stop scheduler: {e}")

    # 关闭 HTTP 客户端
    try:
        from modules.info_client import get_info_client
        await get_info_client().close()
    except Exception:
        pass

    try:
        from modules.emby_client import get_emby_client
        await get_emby_client().close()
    except Exception:
        pass
