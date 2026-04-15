from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from modules.info_client import get_info_client
from telegram_bot.keyboards import (
    search_card_keyboard,
    confirm_download_keyboard,
    detail_keyboard,
    back_to_search_keyboard,
)
from telegram.helpers import InputMediaPhoto


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /search 命令：发送封面卡片第一页"""
    if not context.args:
        await update.message.reply_text(
            "用法：/search <番号或关键词>\n"
            "例：/search abc-123\n"
            "   /search 步兵"
        )
        return

    keyword = " ".join(context.args).strip()
    page = 1
    page_size = 3

    info_client = get_info_client()
    result = await info_client.search_videos(q=keyword, page=page, page_size=page_size)
    total = result.get("total_count", 0)
    data = result.get("data", [])

    if total == 0 or not data:
        await update.message.reply_text(f"未找到「{keyword}」相关影片")
        return

    total_pages = (total + page_size - 1) // page_size

    first = data[0]
    caption = _build_caption(first, keyword, page, total_pages)
    cover_url = first.get("jacket_full_url") or first.get("jacket_thumb_url")
    has_actress = bool(first.get("actress_name"))

    try:
        if cover_url:
            await update.message.reply_photo(
                photo=cover_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=search_card_keyboard(keyword, page, total_pages, has_actress),
            )
        else:
            await update.message.reply_text(
                text=caption,
                parse_mode="HTML",
                reply_markup=search_card_keyboard(keyword, page, total_pages, has_actress),
            )
    except Exception as e:
        # 封面加载失败，降级到纯文字
        await update.message.reply_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=search_card_keyboard(keyword, page, total_pages, has_actress),
        )


def _build_caption(video: dict, keyword: str, page: int, total_pages: int) -> str:
    content_id = video.get("content_id") or video.get("dvd_id", "")
    title = video.get("title_ja_translated") or video.get("title_ja") or "无标题"
    release = video.get("release_date", "-")
    runtime = video.get("runtime_mins", "-")
    actress = video.get("actress_name", "-")

    return (
        f"🎬 <code>{content_id}</code>\n"
        f"📌 {title}\n"
        f"📅 {release} | ⏱ {runtime}分钟\n"
        f"👤 {actress}\n"
        f"─────────────────\n"
        f"[第{page}页/共{total_pages}页]"
    )


def _build_detail_caption(video: dict) -> str:
    content_id = video.get("content_id") or video.get("dvd_id", "")
    title_ja = video.get("title_ja", "-")
    title_cn = video.get("title_ja_translated") or "-"
    release = video.get("release_date", "-")
    runtime = video.get("runtime_mins", "-")
    actress = video.get("actress_name", "-")
    category = video.get("category_name", "-")
    maker = video.get("maker_name", "-")
    summary = video.get("summary", "-")

    return (
        f"🎬 <code>{content_id}</code>\n"
        f"📌 {title_ja}\n"
        f"📌 {title_cn}\n"
        f"📅 发行日期：{release}\n"
        f"⏱ 时长：{runtime}分钟\n"
        f"🏷 题材：{category}\n"
        f"🏭 工作室：{maker}\n"
        f"👤 演员：{actress}\n"
        f"📝 {summary}"
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """统一处理所有搜索相关 callback"""
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    data = query.data
    if not data:
        return

    parts = data.split(":")
    action = parts[0]

    if action == "search":
        keyword = parts[1]
        page = int(parts[2])
        await _send_search_page(query, keyword, page)

    elif action == "confirm":
        keyword = parts[1]
        page = int(parts[2])
        await _show_confirm(query, keyword, page)

    elif action == "detail":
        keyword = parts[1]
        page = int(parts[2])
        await _show_detail(query, keyword, page)

    elif action in ("dl", "confirm_dl"):
        content_id = parts[1]
        keyword = parts[2]
        page = int(parts[3])
        await _do_download(query, content_id, keyword, page)

    elif action == "back":
        keyword = parts[1]
        page = int(parts[2])
        await _send_search_page(query, keyword, page)


async def _send_search_page(query, keyword: str, page: int) -> None:
    page_size = 3
    info_client = get_info_client()
    result = await info_client.search_videos(q=keyword, page=page, page_size=page_size)
    total = result.get("total_count", 0)
    data = result.get("data", [])

    if not data:
        try:
            await query.edit_message_text(text=f"未找到「{keyword}」相关影片")
        except Exception:
            pass
        return

    total_pages = (total + page_size - 1) // page_size
    first = data[0]
    caption = _build_caption(first, keyword, page, total_pages)
    cover_url = first.get("jacket_full_url") or first.get("jacket_thumb_url")
    has_actress = bool(first.get("actress_name"))

    try:
        if cover_url:
            await query.edit_message_media(
                media=InputMediaPhoto(media=cover_url, caption=caption, parse_mode="HTML"),
                reply_markup=search_card_keyboard(keyword, page, total_pages, has_actress),
            )
        else:
            await query.edit_message_text(
                text=caption,
                parse_mode="HTML",
                reply_markup=search_card_keyboard(keyword, page, total_pages, has_actress),
            )
    except Exception:
        pass


async def _show_confirm(query, keyword: str, page: int) -> None:
    page_size = 3
    info_client = get_info_client()
    result = await info_client.search_videos(q=keyword, page=page, page_size=page_size)
    data = result.get("data", [])
    if not data:
        return

    first = data[0]
    content_id = first.get("content_id") or first.get("dvd_id", "")
    title = first.get("title_ja_translated") or first.get("title_ja", "")

    caption = f"🎬 <code>{content_id}</code>\n📌 {title}\n确认下载这部影片？"
    cover_url = first.get("jacket_full_url") or first.get("jacket_thumb_url")

    try:
        if cover_url:
            await query.edit_message_media(
                media=InputMediaPhoto(media=cover_url, caption=caption, parse_mode="HTML"),
                reply_markup=confirm_download_keyboard(content_id, keyword, page),
            )
        else:
            await query.edit_message_text(
                text=caption,
                parse_mode="HTML",
                reply_markup=confirm_download_keyboard(content_id, keyword, page),
            )
    except Exception:
        pass


async def _show_detail(query, keyword: str, page: int) -> None:
    page_size = 3
    info_client = get_info_client()
    result = await info_client.search_videos(q=keyword, page=page, page_size=page_size)
    data = result.get("data", [])
    if not data:
        return

    first = data[0]
    content_id = first.get("content_id") or first.get("dvd_id", "")
    detail = await info_client.get_video(content_id)
    caption = _build_detail_caption(detail)
    cover_url = detail.get("jacket_full_url") or detail.get("jacket_thumb_url")
    has_actress = bool(detail.get("actress_name"))

    try:
        if cover_url:
            await query.edit_message_media(
                media=InputMediaPhoto(media=cover_url, caption=caption, parse_mode="HTML"),
                reply_markup=detail_keyboard(content_id, keyword, page, has_actress),
            )
        else:
            await query.edit_message_text(
                text=caption,
                parse_mode="HTML",
                reply_markup=detail_keyboard(content_id, keyword, page, has_actress),
            )
    except Exception:
        pass


async def _do_download(query, content_id: str, keyword: str, page: int) -> None:
    try:
        from backend.routers.download import create_download_by_content_id
        await create_download_by_content_id(content_id)
        text = f"✅ <code>{content_id}</code> 已加入下载队列"
    except Exception as e:
        text = f"❌ 下载失败：{str(e)}"

    try:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=back_to_search_keyboard(keyword, page),
        )
    except Exception:
        pass
