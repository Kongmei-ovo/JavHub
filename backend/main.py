import asyncio
import logging
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import init_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

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
from routers.translation import router as translation_router
from routers.proxy import router as proxy_router
from routers.inventory import router as inventory_router

app = FastAPI(title="AV Downloader API")

# ========== 统一错误响应格式 ==========
class ApiResponse:
    """统一 API 响应格式
    成功: { "data": ..., "message": "ok" }
    错误: { "detail": "错误信息", "code": "ERR_XXX" }
    """
    SUCCESS = "ok"
    ERR_NOT_FOUND = "ERR_NOT_FOUND"
    ERR_BAD_REQUEST = "ERR_BAD_REQUEST"
    ERR_INTERNAL = "ERR_INTERNAL"
    ERR_UNAUTHORIZED = "ERR_UNAUTHORIZED"
    ERR_FORBIDDEN = "ERR_FORBIDDEN"

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.status_code,
            "message": exc.detail,
        },
        headers={"X-Error-Code": str(exc.status_code)} if exc.status_code >= 500 else {}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback
    logging.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误",
            "code": "ERR_INTERNAL",
            "message": str(exc) if hasattr(exc, '__str__') else "Unknown error",
        },
        headers={"X-Error-Code": "ERR_INTERNAL"}
    )

# CORS - 默认仅允许本地开发前端，部署时通过配置覆盖
_frontend_origin = "http://localhost:5173"  # Vite dev server
try:
    from config import config as _cfg
    _origin = getattr(_cfg, 'frontend_origin', None)
    if _origin:
        _frontend_origin = _origin
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 速率限制中间件
from config import config as _cfg
if _cfg.rate_limit_enabled:
    from middlewares.rate_limit import init_limiter, get_limiter
    init_limiter(requests_per_minute=_cfg.rate_limit_rpm, burst=_cfg.rate_limit_burst)
    _rate_limiter = get_limiter()

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if _rate_limiter is None:
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        allowed, headers = _rate_limiter.is_allowed(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
                headers=headers,
            )
        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response

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
app.include_router(translation_router)
app.include_router(proxy_router)
app.include_router(inventory_router)


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
