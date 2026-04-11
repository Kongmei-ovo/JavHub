import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import config
from database import add_log

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def subscription_check_job():
    """定时检查订阅任务"""
    add_log("INFO", "开始订阅检查...")
    try:
        # 使用新的 subscription 服务
        from services.subscription import check_all_subscriptions

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            new_movies = loop.run_until_complete(check_all_subscriptions())
        finally:
            loop.close()

        for movie in new_movies:
            # 自动下载
            add_log("INFO", f"自动下载: {movie['code']}")
            # TODO: 调用 OpenList 下载
            # from modules.openlist_client import get_openlist_client
            # openlist = get_openlist_client()
            # await openlist.add_offline_download(magnet, path)

        add_log("INFO", f"订阅检查完成，发现 {len(new_movies)} 部新片")

        # 发送通知
        if new_movies:
            try:
                from services.notification import notification_service
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(notification_service.notify_new_movies(new_movies))
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Notification failed: {e}")

    except Exception as e:
        add_log("ERROR", f"订阅检查失败: {e}")


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

    scheduler.start()
    logger.info(f"Scheduler started, subscription check at {check_hour}:00")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
