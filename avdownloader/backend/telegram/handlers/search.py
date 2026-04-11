from telegram import Update
from telegram.ext import ContextTypes
from telegram.keyboards import search_result_keyboard
from modules.info_client import get_info_client
from modules.openlist_client import get_openlist_client

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /search 命令"""
    if not context.args:
        await update.message.reply_text("用法：/search <关键词>")
        return

    keyword = " ".join(context.args)
    info_client = get_info_client()

    try:
        result = await info_client.search_videos(q=keyword, page_size=5)
        items = result.get("data", [])

        if not items:
            await update.message.reply_text(f"未找到「{keyword}」相关影片")
            return

        for item in items:
            content_id = item.get("content_id") or item.get("dvd_id", "")
            title = item.get("title_en", "")
            release_date = item.get("release_date", "")
            runtime = item.get("runtime_mins", "")

            text = f"🎬 {content_id}\n{title}\n发行：{release_date} | 时长：{runtime}分钟"

            keyboard = search_result_keyboard(content_id)
            await update.message.reply_text(text, reply_markup=keyboard)

    except Exception as e:
        await update.message.reply_text(f"搜索失败：{str(e)}")

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理下载回调"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data or not data.startswith("download:"):
        return

    content_id = data.replace("download:", "")

    # 获取影片详情和磁力
    info_client = get_info_client()
    try:
        detail = await info_client.get_video(content_id)
        magnets = detail.get("magnets", [])

        if not magnets:
            await query.edit_message_text("❌ 暂无磁力链接")
            return

        # 取第一个磁力
        magnet = magnets[0].get("magnet")

        # 调用 OpenList 下载
        openlist = get_openlist_client()
        task_id = await openlist.add_offline_download(magnet)

        await query.edit_message_text(f"✅ 已提交下载任务：{content_id}\n任务ID：{task_id}")

    except Exception as e:
        await query.edit_message_text(f"❌ 下载失败：{str(e)}")