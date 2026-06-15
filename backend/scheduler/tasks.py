import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import config
from database import add_log
from services.candidate_processor import is_candidate_processing_running

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

# 防重入标志
_subscription_check_lock = threading.Lock()
_scheduler_job_results: dict[str, dict[str, Any]] = {}
_scheduler_job_results_lock = threading.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def record_scheduler_job_result(
    job_id: str,
    *,
    status: str,
    run_at: datetime,
    duration_ms: int,
    error: str | None,
) -> dict[str, Any]:
    result = {
        "last_run_at": _isoformat(run_at),
        "last_duration_ms": max(0, int(duration_ms)),
        "last_status": status,
        "last_error": error,
    }
    with _scheduler_job_results_lock:
        _scheduler_job_results[job_id] = result
    return result


def get_scheduler_job_result(job_id: str) -> dict[str, Any]:
    with _scheduler_job_results_lock:
        result = _scheduler_job_results.get(job_id)
        if result is None:
            return {
                "last_run_at": None,
                "last_duration_ms": None,
                "last_status": None,
                "last_error": None,
            }
        return dict(result)


def clear_scheduler_job_results() -> None:
    with _scheduler_job_results_lock:
        _scheduler_job_results.clear()


def scheduler_job_wrapper(job_id: str, func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        started_at = _utc_now()
        monotonic_started = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - monotonic_started) * 1000)
            record_scheduler_job_result(
                job_id,
                status="failed",
                run_at=started_at,
                duration_ms=duration_ms,
                error=str(exc) or exc.__class__.__name__,
            )
            raise
        duration_ms = int((time.perf_counter() - monotonic_started) * 1000)
        record_scheduler_job_result(
            job_id,
            status="success",
            run_at=started_at,
            duration_ms=duration_ms,
            error=None,
        )
        return result

    return wrapped


def subscription_check_job():
    """定时检查订阅任务"""
    if not _subscription_check_lock.acquire(blocking=False):
        add_log("WARNING", "订阅检查任务正在执行，跳过本次触发（防重入）")
        return
    add_log("INFO", "开始订阅检查...")
    try:
        from scheduler.worker_loop import run as run_on_loop
        from services.subscription import check_all_subscriptions
        new_movies = run_on_loop(check_all_subscriptions())
        add_log("INFO", f"订阅检查完成，生成/刷新 {len(new_movies)} 个下载候选")

        if new_movies:
            # 发送通知
            try:
                from services.notification import notification_service
                run_on_loop(notification_service.notify_new_movies(new_movies))
            except Exception as e:
                logger.error(f"Notification failed: {e}")
    except Exception as e:
        add_log("ERROR", f"订阅检查失败: {e}")
        raise
    finally:
        _subscription_check_lock.release()


def candidate_auto_process_job():
    """Process candidate queue according to automation policy."""
    policy = config.automation_download_policy
    if policy == "manual":
        return
    try:
        from scheduler.worker_loop import run as run_on_loop
        from services.candidate_processor import run_automatic_candidate_processing
        result = run_on_loop(run_automatic_candidate_processing())
        counts = result.get("counts", {}) if isinstance(result, dict) else {}
        add_log("INFO", f"候选自动处理完成: {counts}")
    except Exception as e:
        add_log("ERROR", f"候选自动处理失败: {e}")
        raise


_variant_index_rebuild_lock = threading.Lock()


def variant_index_rebuild_job():
    """Rebuild the materialized variant group index.

    The index backs cross-page variant injection (videos/favorites pages) and
    whole-group favoriting; it must follow data imports, supplement growth and
    grouping-rule changes, hence the daily rebuild.
    """
    if not _variant_index_rebuild_lock.acquire(blocking=False):
        add_log("WARNING", "变体索引重建正在执行，跳过本次触发（防重入）")
        return
    try:
        from database.video_variant_index import add_variant_group_job
        from services.video_variant_index import run_variant_index_job

        add_log("INFO", "开始重建变体索引...")
        job_id = add_variant_group_job("queued")
        result = run_variant_index_job(job_id)
        status = result.get("status")
        summary = (result.get("result") or {}) if isinstance(result, dict) else {}
        if status == "completed":
            add_log("INFO", f"变体索引重建完成: {summary}")
        else:
            add_log("ERROR", f"变体索引重建失败: {result.get('error')}")
    except Exception as e:
        add_log("ERROR", f"变体索引重建失败: {e}")
        raise
    finally:
        _variant_index_rebuild_lock.release()


def candidate_auto_process_schedule_state() -> dict:
    """Expose scheduler status for operations overview."""
    job = scheduler.get_job('candidate_auto_process') if scheduler.running else None
    next_run = getattr(job, "next_run_time", None) if job else None
    return {
        "enabled": bool(job),
        "running": is_candidate_processing_running(),
        "next_run_time": next_run.isoformat() if next_run else None,
    }


def configure_candidate_auto_process_job():
    """Install or refresh the candidate automation interval job."""
    try:
        scheduler.remove_job('candidate_auto_process')
    except Exception as exc:
        if "No job by the id" not in str(exc):
            logger.debug("Unable to remove candidate automation job before refresh: %s", exc)
    interval_minutes = config.automation_auto_process_interval_minutes
    if interval_minutes <= 0:
        return
    scheduler.add_job(
        scheduler_job_wrapper('candidate_auto_process', candidate_auto_process_job),
        'interval',
        minutes=interval_minutes,
        id='candidate_auto_process',
        name='候选自动处理',
        replace_existing=True,
        max_instances=1,
    )


def acquisition_coordinator_job():
    """Poll in-flight 115 offline tasks → finalize → sync acquisition sessions.

    This is the background coordinator the design called for:
    ``downloader_service.update_all_task_statuses`` existed but was never on any
    schedule, so 115 finalize never ran on its own. This interval job drives it.
    """
    from scheduler.worker_loop import run as run_on_loop
    from services.downloader import downloader_service

    try:
        run_on_loop(downloader_service.update_all_task_statuses())
    except Exception as exc:
        add_log("ERROR", f"获取任务协调失败: {exc}")
        raise


def configure_acquisition_coordinator_job():
    """Install or refresh the 115 finalize coordinator interval job."""
    try:
        scheduler.remove_job('acquisition_coordinator')
    except Exception as exc:
        if "No job by the id" not in str(exc):
            logger.debug("Unable to remove acquisition coordinator job before refresh: %s", exc)
    interval_minutes = config.acquisition_coordinator_interval_minutes
    if interval_minutes <= 0:
        return
    scheduler.add_job(
        scheduler_job_wrapper('acquisition_coordinator', acquisition_coordinator_job),
        IntervalTrigger(minutes=interval_minutes),
        id='acquisition_coordinator',
        name='获取任务协调器',
        replace_existing=True,
        max_instances=1,
    )


def start_scheduler():
    """启动定时任务"""
    check_hour = config.scheduler_check_hour
    if check_hour is None:
        logger.info("Scheduler disabled")
        return

    # 每天定时检查
    scheduler.add_job(
        scheduler_job_wrapper('subscription_check', subscription_check_job),
        CronTrigger(hour=check_hour, minute=0),
        id='subscription_check',
        name='订阅检查',
        replace_existing=True
    )

    # 每日变体索引重建（默认 4:00）。
    variant_index_hour = config.scheduler_variant_index_rebuild_hour
    if variant_index_hour is not None:
        scheduler.add_job(
            scheduler_job_wrapper('variant_index_rebuild', variant_index_rebuild_job),
            CronTrigger(hour=variant_index_hour, minute=0),
            id='variant_index_rebuild',
            name='变体索引重建',
            replace_existing=True,
        )

    configure_candidate_auto_process_job()
    configure_acquisition_coordinator_job()

    scheduler.start()
    logger.info(f"Scheduler started, subscription check at {check_hour}:00")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
