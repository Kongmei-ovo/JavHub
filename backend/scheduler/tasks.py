import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import config
from database import add_log
from backend.scheduler.inventory_tasks import run_inventory_comparison

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

        # asyncio.run() 管理自己的 loop，避免重复创建/关闭
        new_movies = asyncio.run(check_all_subscriptions())

        for movie in new_movies:
            add_log("INFO", f"自动下载: {movie['code']}")
            # TODO: 调用 OpenList 下载
            # from modules.openlist_client import get_openlist_client
            # asyncio.run(openlist.add_offline_download(...))

        add_log("INFO", f"订阅检查完成，发现 {len(new_movies)} 部新片")

        # 发送通知
        if new_movies:
            try:
                from services.notification import notification_service
                asyncio.run(notification_service.notify_new_movies(new_movies))
            except Exception as e:
                logger.error(f"Notification failed: {e}")

    except Exception as e:
        add_log("ERROR", f"订阅检查失败: {e}")
    finally:
        _running = False


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

    scheduler.start()
    logger.info(f"Scheduler started, subscription check at {check_hour}:00")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
