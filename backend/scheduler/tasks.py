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
from database import add_inventory_job, add_log
from scheduler.inventory_tasks import run_inventory_comparison
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


def inventory_comparison_job(job_type: str = "full"):
    """Run the async inventory comparison job on the shared scheduler loop."""
    from scheduler.worker_loop import run as run_on_loop

    return run_on_loop(run_inventory_comparison(job_type=job_type))


def inventory_daily_pipeline_job():
    """Daily end-to-end: collect → compare → (preview).

    Replaces the old "compare only" cron, which never refreshed the Emby
    snapshot. Without this, every nightly compare ran against a stale
    snapshot — anything downloaded yesterday looked like it was still
    missing, so missing/candidate counts drifted further from reality each
    day. Stage 3 stays a dry-run preview; actual download dispatch is the
    job of the interval-driven candidate auto-process.
    """
    from scheduler.worker_loop import run as run_on_loop
    from services.supplement_pipeline import run_supplement_pipeline

    job_id = add_inventory_job("full", None, None)
    summary = run_on_loop(
        run_supplement_pipeline(
            job_id,
            do_collect=True,
            actor_id=None,
            process=True,
            dry_run=True,
        )
    )
    counts = (summary.get("stages", {}).get("process") or {}).get("counts") or {}
    add_log("INFO", f"日常 pipeline (collect+compare) 完成 job={job_id} preview_counts={counts}")
    return summary


def candidate_sent_audit_job():
    """Verify ``sent`` candidates landed: downloader finished + Emby has it.

    Closes the loop the audit called out: candidates used to stop at ``sent``
    forever, so the system never learned which downloads actually succeeded.
    For each ``sent`` row:
    - if the download task is failed → revert to ``failed`` (retryable)
    - if Emby confirms the code is present → promote to ``completed`` and
      delete the matching ``missing_videos`` row
    - otherwise leave alone (still downloading / not yet visible to Emby)
    """
    from scheduler.worker_loop import run as run_on_loop
    from services.sent_audit import audit_sent_candidates

    try:
        result = run_on_loop(audit_sent_candidates())
        add_log(
            "INFO",
            (
                "sent 候选核对完成: "
                f"checked={result.get('checked', 0)} "
                f"completed={result.get('completed', 0)} "
                f"failed={result.get('failed', 0)} "
                f"pending={result.get('pending', 0)}"
            ),
        )
        return result
    except Exception as exc:
        add_log("ERROR", f"sent 候选核对失败: {exc}")
        raise


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


def configure_candidate_sent_audit_job():
    """Install or refresh the sent-candidate audit interval job."""
    try:
        scheduler.remove_job('candidate_sent_audit')
    except Exception as exc:
        if "No job by the id" not in str(exc):
            logger.debug("Unable to remove sent-audit job before refresh: %s", exc)
    interval_minutes = config.inventory_sent_audit_interval_minutes
    if interval_minutes <= 0:
        return
    scheduler.add_job(
        scheduler_job_wrapper('candidate_sent_audit', candidate_sent_audit_job),
        IntervalTrigger(minutes=interval_minutes),
        id='candidate_sent_audit',
        name='sent 候选核对',
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

    # 日常 pipeline: collect → compare → preview。每天 3:00 整条跑一遍,
    # 这样隔天对比的快照是最新的(以前只跑 compare,快照永远滞后)。
    scheduler.add_job(
        scheduler_job_wrapper('inventory_daily_pipeline', inventory_daily_pipeline_job),
        CronTrigger(hour=3, minute=0),
        id='inventory_daily_pipeline',
        name='日常库存 Pipeline',
        replace_existing=True,
    )

    configure_candidate_auto_process_job()
    configure_candidate_sent_audit_job()

    scheduler.start()
    logger.info(f"Scheduler started, subscription check at {check_hour}:00")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
