import logging
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from database import init_db
from config import config as _cfg
from middlewares.performance import RequestTimingMiddleware
from middlewares.trace import TraceIdMiddleware
from services.log_redaction import install_sensitive_log_filter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
install_sensitive_log_filter()

# 导入新模块化路由
from routers.videos import router as videos_router
from routers.actresses import router as actresses_router
from routers.makers import router as makers_router
from routers.series import router as series_router
from routers.categories import router as categories_router
from routers.downloads import router as downloads_router
from routers.subscriptions import router as subscriptions_router
from routers.config import router as config_router
from routers.logs import router as logs_router
from routers.health import router as health_router
from routers.translation import router as translation_router
from routers.supplement import router as supplement_router
from routers.proxy import router as proxy_router
from routers.favorites import router as favorites_router
from routers.stream import router as stream_router
from routers.directors import router as directors_router
from routers.actors import router as actors_router
from routers.authors import router as authors_router
from routers.labels import router as labels_router
from routers.javinfo_imports import router as javinfo_imports_router
from routers.video_variant_index import router as video_variant_index_router
from routers.source_health import router as source_health_router
from routers.jobs import router as jobs_router
from routers.scheduler import router as scheduler_router
from routers.playback import router as playback_router
from routers.emby_compat import discovery_router as emby_discovery_router
from routers.emby_compat import router as emby_compat_router
from routers.open115 import router as open115_router
from routers.open115_files import router as open115_files_router
from routers.movie_resources import router as movie_resources_router
from routers.film_dictionary import router as film_dictionary_router
from routers.acquisitions import router as acquisitions_router
from services.emby_auth import EmbyHTTPException

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


@app.exception_handler(EmbyHTTPException)
async def emby_http_exception_handler(request: Request, exc: EmbyHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"Code": exc.emby_code, "Message": str(exc.detail)},
    )

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
            "message": "服务器内部错误",
        },
        headers={"X-Error-Code": "ERR_INTERNAL"}
    )

# CORS - 默认仅允许本地开发前端，部署时通过配置覆盖
_frontend_origin = _cfg.frontend_origin
if _frontend_origin == "*":
    raise RuntimeError("server.frontend_origin cannot be '*' while credentials are enabled")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Emby-Authorization",
        "X-Emby-Token",
        "X-Emby-Client",
        "X-Emby-Device-Id",
        "X-Emby-Device-Name",
        "X-Emby-Client-Version",
        "X-MediaBrowser-Authorization",
        "X-MediaBrowser-Token",
    ],
)

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(RequestTimingMiddleware, slow_request_ms=500)
app.add_middleware(TraceIdMiddleware)

# 速率限制中间件
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
app.include_router(config_router)
app.include_router(logs_router)
app.include_router(health_router)
app.include_router(translation_router)
app.include_router(supplement_router)
app.include_router(proxy_router)
app.include_router(favorites_router)
app.include_router(stream_router)
app.include_router(directors_router)
app.include_router(actors_router)
app.include_router(authors_router)
app.include_router(labels_router)
app.include_router(javinfo_imports_router)
app.include_router(video_variant_index_router)
app.include_router(source_health_router)
app.include_router(jobs_router)
app.include_router(scheduler_router)
app.include_router(playback_router)
app.include_router(open115_router)
app.include_router(open115_files_router)
app.include_router(movie_resources_router)
app.include_router(film_dictionary_router)
app.include_router(acquisitions_router)
# Emby 兼容层挂根路径与 /emby 双前缀（不同客户端拼法不同）
app.include_router(emby_compat_router)
app.include_router(emby_discovery_router, prefix="/emby")
app.include_router(emby_compat_router, prefix="/emby")


@app.on_event("startup")
async def startup_event():
    install_sensitive_log_filter()
    """启动时运行"""
    try:
        from scheduler.tasks import start_scheduler
        start_scheduler()
    except Exception as e:
        logging.error(f"Failed to start scheduler: {e}")

    # 推送代理配置到 JavInfoApi（如果 JavInfoApi 未就绪则静默失败）
    try:
        from routers.config import _push_proxy_to_javinfo
        await _push_proxy_to_javinfo()
    except Exception as e:
        logging.warning(f"Failed to push proxy to JavInfoApi on startup: {e}")

    # 注册下载源插件
    try:
        from sources import register_all_sources
        register_all_sources()
    except Exception as e:
        logging.error(f"Failed to register sources: {e}")

    # 后端启动后立刻 fire-and-forget 预热 FlareSolverr session,
    # 让用户首次开播跳过"chrome 冷启 + CF challenge"的 30s 头付。
    try:
        from services.cf_solver import start_warmup_background
        start_warmup_background()
    except Exception as e:
        logging.warning(f"Failed to start CF solver warmup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时运行"""
    try:
        from scheduler.tasks import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logging.error(f"Failed to stop scheduler: {e}")

    # 关闭 HTTP 客户端
    try:
        from modules.info_client import get_info_client
        await get_info_client().close()
    except Exception as e:
        logging.debug("Failed to close JavInfoApi client: %s", e)

    try:
        from services.open115 import open115_client
        await open115_client.close()
    except Exception as e:
        logging.debug("Failed to close 115 Open client: %s", e)

    try:
        from routers.playback import playback_hls_client
        await playback_hls_client.aclose()
    except Exception as e:
        logging.debug("Failed to close 115 HLS proxy client: %s", e)
