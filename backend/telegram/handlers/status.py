from telegram import Update
from telegram.ext import ContextTypes
from database import get_download_tasks

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /status 命令"""
    try:
        tasks = get_download_tasks(limit=10)

        if not tasks:
            await update.message.reply_text("📥 暂无下载任务")
            return

        text = "📥 下载队列：\n\n"
        for task in tasks:
            code = task.get("content_id", "")
            title = task.get("title", "")[:20]
            status = task.get("status", "")
            status_emoji = {"pending": "⏳", "downloading": "📥", "completed": "✅", "failed": "❌"}.get(status, "❓")
            text += f"{status_emoji} {code} - {title}\n"

        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ 获取失败：{str(e)}")