import logging
import httpx
from typing import List, Optional
from config import config
from database import add_log

logger = logging.getLogger(__name__)

class NotificationService:
    """通知服务"""

    def __init__(self):
        self.enabled = config.notification_enabled
        self.telegram_notify = config.notification_telegram
        self.auto_download_notify = config.notification_auto_download
        self.download_complete_notify = config.notification_download_complete
        self.new_movie_notify = config.notification_new_movie
        self.bot_token = config.telegram_bot_token
        self.allowed_users = config.telegram_allowed_users
        self.telegram_timeout = config.telegram_timeout

    async def send_telegram_message(self, user_id: str, text: str) -> bool:
        """发送Telegram消息"""
        if not self.bot_token:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            async with httpx.AsyncClient(timeout=self.telegram_timeout) as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": user_id,
                        "text": text,
                        "parse_mode": "Markdown"
                    },
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    async def notify_new_movies(self, movies: list):
        """通知发现新片"""
        from database import get_subscriptions

        subs = get_subscriptions()
        auto_subs = {s["actress_name"]: s for s in subs if s.get("auto_download")}

        # 按演员分组
        by_actress = {}
        for movie in movies:
            actress = movie.get("actress_name", "未知")
            if actress not in by_actress:
                by_actress[actress] = []
            by_actress[actress].append(movie)

        for actress, actress_movies in by_actress.items():
            is_auto = actress in auto_subs
            if is_auto:
                text = f"🎬 *{actress}* 有新片已自动下载\n\n"
            else:
                text = f"🎬 *{actress}* 有新片\n\n"

            for movie in actress_movies[:5]:
                text += f"• `{movie['code']}` {movie.get('title', '')}\n"

            await self._broadcast(text)

    async def notify_download_complete(self, code: str, title: str):
        """通知下载完成"""
        if not self.enabled or not self.download_complete_notify:
            return

        text = f"✅ *下载完成*\n\n`{code}`\n{title}"
        await self._broadcast(text)

    async def notify_download_failed(self, code: str, error: str):
        """通知下载失败"""
        if not self.enabled:
            return

        text = f"❌ *下载失败*\n\n`{code}`\n原因: {error}"
        await self._broadcast(text)

    async def notify_auto_download(self, code: str, actor: str, title: str):
        """通知自动下载"""
        if not self.enabled or not self.auto_download_notify:
            return

        text = f"📥 *自动下载已触发*\n\n`{code}`\n演员: {actor}\n{title}"
        await self._broadcast(text)

    async def _broadcast(self, text: str):
        """向所有授权用户广播消息"""
        if not self.allowed_users:
            return

        for user_id in self.allowed_users:
            await self.send_telegram_message(user_id, text)

    def log_and_notify(self, level: str, message: str, notify: bool = False):
        """记录日志并可选通知"""
        add_log(level, message)

notification_service = NotificationService()
