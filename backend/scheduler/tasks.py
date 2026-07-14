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


def avdb_sync_job():
    """Check and atomically import the latest AVDB public release."""
    from services.avdb_sync import sync_avdb_release

    try:
        result = sync_avdb_release()
        if result.get("busy"):
            add_log("WARNING", "AVDB 同步已在其他后端进程中执行，本次触发跳过")
        elif result.get("changed"):
            add_log(
                "INFO",
                f"AVDB 同步完成: {result.get('current_release') or result.get('release')}, "
                f"{result.get('record_count', 0)} 条记录",
            )
        else:
            add_log("INFO", "AVDB 已是最新版本")
        return result
    except Exception as exc:
        add_log("ERROR", f"AVDB 同步失败: {exc}")
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


def configure_avdb_sync_job():
    """Install or remove the AVDB release-check interval job from current config."""
    try:
        scheduler.remove_job('avdb_sync')
    except Exception as exc:
        if "No job by the id" not in str(exc):
            logger.debug("Unable to remove AVDB sync job before refresh: %s", exc)
    if not config.avdb_sync_enabled:
        return
    interval_hours = int(config.avdb_source_config.get('interval_hours') or 12)
    scheduler.add_job(
        scheduler_job_wrapper('avdb_sync', avdb_sync_job),
        IntervalTrigger(hours=interval_hours),
        id='avdb_sync',
        name='AVDB 公开库同步',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def recover_avdb_sync_state() -> bool:
    from database.avdb import recover_interrupted_avdb_sync

    return recover_interrupted_avdb_sync()


# 可手动"立即运行"的调度作业白名单：id → 作业函数。
# 系统作业控制台 (POST /scheduler/jobs/{id}/run) 只允许触发这些。
_MANUAL_JOB_FUNCS: dict[str, Callable[[], Any]] = {
    'subscription_check': subscription_check_job,
    'variant_index_rebuild': variant_index_rebuild_job,
    'candidate_auto_process': candidate_auto_process_job,
    'acquisition_coordinator': acquisition_coordinator_job,
    'avdb_sync': avdb_sync_job,
}

MANUAL_JOB_IDS: tuple[str, ...] = tuple(_MANUAL_JOB_FUNCS)

_manual_run_threads: dict[str, threading.Thread] = {}
_manual_run_lock = threading.Lock()
MANUAL_JOB_SHUTDOWN_TIMEOUT = 10.0


def drain_manual_scheduler_jobs(
    timeout: float = MANUAL_JOB_SHUTDOWN_TIMEOUT,
) -> tuple[str, ...]:
    """Wait for manual jobs using one deadline shared by all job threads."""
    deadline = time.monotonic() + max(0.0, float(timeout))
    with _manual_run_lock:
        threads = tuple(
            thread for thread in _manual_run_threads.values() if thread.is_alive()
        )
    for thread in threads:
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
    alive = tuple(thread.name for thread in threads if thread.is_alive())
    for name in alive:
        logger.warning(
            "Manual scheduler job thread still running during shutdown: %s", name
        )
    return alive


def trigger_scheduler_job(job_id: str) -> dict[str, Any]:
    """Run a whitelisted scheduler job immediately in a background thread.

    Reuses ``scheduler_job_wrapper`` so a manual run records the same
    last_run/last_status as a scheduled run. Returns immediately; if the job
    is already running we report ``accepted=False`` instead of double-firing.
    """
    func = _MANUAL_JOB_FUNCS.get(job_id)
    if func is None:
        raise KeyError(job_id)
    with _manual_run_lock:
        existing = _manual_run_threads.get(job_id)
        if existing is not None and existing.is_alive():
            return {"accepted": False, "running": True}
        thread = threading.Thread(
            target=scheduler_job_wrapper(job_id, func),
            name=f"manual-{job_id}",
            daemon=True,
        )
        _manual_run_threads[job_id] = thread
        thread.start()
    return {"accepted": True, "running": True}


def start_scheduler():
    """启动定时任务"""
    try:
        if recover_avdb_sync_state():
            add_log("WARNING", "检测到中断的 AVDB 同步，已标记失败，可立即重试")
    except Exception as exc:
        logger.warning("Failed to recover interrupted AVDB sync state: %s", exc)
    check_hour = config.scheduler_check_hour
    # Subscription cron can be disabled independently; interval jobs such as
    # AVDB sync and acquisition coordination must continue to run.
    if check_hour is not None:
        scheduler.add_job(
            scheduler_job_wrapper('subscription_check', subscription_check_job),
            CronTrigger(hour=check_hour, minute=0),
            id='subscription_check',
            name='订阅检查',
            replace_existing=True
        )
    else:
        try:
            scheduler.remove_job('subscription_check')
        except Exception:
            pass

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
    configure_avdb_sync_job()

    scheduler.start()
    logger.info(
        "Scheduler started, subscription check %s",
        f"at {check_hour}:00" if check_hour is not None else "disabled",
    )


def stop_scheduler():
    """停止定时任务"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
    finally:
        drain_manual_scheduler_jobs()
