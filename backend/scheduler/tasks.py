import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import config
from database import add_log
from scheduler.inventory_tasks import run_inventory_comparison
from services.candidate_processor import is_candidate_processing_running

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

# 防重入标志
_running = False


def subscription_check_job():
    """定时检查订阅任务"""
    global _running
    if _running:
        add_log("WARNING", "订阅检查任务正在执行，跳过本次触发（防重入）")
        return
    add_log("INFO", "开始订阅检查...")
    _running = True
    try:
        from services.subscription import check_all_subscriptions
        new_movies = asyncio.run(check_all_subscriptions())
        add_log("INFO", f"订阅检查完成，生成/刷新 {len(new_movies)} 个下载候选")

        if new_movies:
            # 发送通知
            try:
                from services.notification import notification_service
                asyncio.run(notification_service.notify_new_movies(new_movies))
            except Exception as e:
                logger.error(f"Notification failed: {e}")
    except Exception as e:
        add_log("ERROR", f"订阅检查失败: {e}")
    finally:
        _running = False


def candidate_auto_process_job():
    """Process candidate queue according to automation policy."""
    policy = config.automation_download_policy
    if policy == "manual":
        return
    try:
        from services.candidate_processor import run_automatic_candidate_processing
        result = asyncio.run(run_automatic_candidate_processing())
        counts = result.get("counts", {}) if isinstance(result, dict) else {}
        add_log("INFO", f"候选自动处理完成: {counts}")
    except Exception as e:
        add_log("ERROR", f"候选自动处理失败: {e}")


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
        candidate_auto_process_job,
        'interval',
        minutes=interval_minutes,
        id='candidate_auto_process',
        name='候选自动处理',
        replace_existing=True,
        max_instances=1,
    )


def start_scheduler():
    """启动定时任务"""
    check_hour = config.scheduler_check_hour
    if not check_hour and check_hour != 0:
        logger.info("Scheduler disabled")
        return

    # 每天定时检查
    scheduler.add_job(
        subscription_check_job,
        CronTrigger(hour=check_hour, minute=0),
        id='subscription_check',
        name='订阅检查',
        replace_existing=True
    )

    # 库存对比任务
    scheduler.add_job(
        run_inventory_comparison,
        CronTrigger(hour=3, minute=0),
        id='inventory_comparison',
        name='库存对比',
        replace_existing=True,
        kwargs={"job_type": "full"}
    )

    configure_candidate_auto_process_job()

    scheduler.start()
    logger.info(f"Scheduler started, subscription check at {check_hour}:00")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
