from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram_bot.utils_image import jacket_full_url
from modules.info_client import get_info_client
from telegram_bot.keyboards import (
    search_card_keyboard,
    confirm_download_keyboard,
    detail_keyboard,
    back_to_search_keyboard,
)


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /search 命令：发送封面卡片第一页"""
    import logging
    import traceback
    import sys
    log = logging.getLogger('telegram.bot')
    print(f"[SEARCH HANDLER] invoked, args={context.args}", flush=True)
    sys.stderr.flush()
    log.info(f"[SEARCH HANDLER] invoked, args={context.args}")
    try:
        if not context.args:
            print("[SEARCH HANDLER] no args, sending usage", flush=True)
            log.info("[SEARCH HANDLER] no args, sending usage")
            await update.message.reply_text(
                "用法：/search <番号或关键词>\n"
                "例：/search abc-123\n"
                "   /search 步兵"
            )
            print("[SEARCH HANDLER] usage sent ok", flush=True)
            return

        keyword = " ".join(context.args).strip()
        print(f"[SEARCH HANDLER] keyword={keyword}", flush=True)
        log.info(f"[SEARCH HANDLER] keyword={keyword}")
        page = 1
        page_size = 3

        info_client = get_info_client()
        print("[SEARCH HANDLER] calling JavInfoApi", flush=True)
        log.info("[SEARCH HANDLER] calling JavInfoApi")
        # 番号精确匹配：content_id 参数映射到 JavInfoApi 的 dvd_id 字段
        result = await info_client.search_videos(content_id=keyword, page=page, page_size=page_size)
        if result.get("total_count", 0) == 0:
            # 番号搜不到再走关键词搜索
            result = await info_client.search_videos(q=keyword, page=page, page_size=page_size)
        print(f"[SEARCH HANDLER] got result, total={result.get('total_count', 0)}", flush=True)
        log.info(f"[SEARCH HANDLER] got result, total={result.get('total_count', 0)}")

        total = result.get("total_count", 0)
        data = result.get("data", [])

        if total == 0 or not data:
            print(f"[SEARCH HANDLER] no results for {keyword}", flush=True)
            await update.message.reply_text(f"未找到「{keyword}」相关影片")
            return

        # 获取第一结果的详情（包含高清封面）
        first = data[0]
        content_id = first.get("content_id") or first.get("dvd_id", "")
        try:
            detail = await info_client.get_video(content_id)
        except Exception:
            detail = first
        caption = _build_caption(detail, keyword, page, total_pages)
        cover_url = jacket_full_url(detail.get("jacket_thumb_url")) or detail.get("jacket_full_url") or detail.get("jacket_thumb_url")
        has_actress = bool(first.get("actress_name"))

        print(f"[SEARCH HANDLER] sending reply_photo, cover={bool(cover_url)}", flush=True)
        log.info(f"[SEARCH HANDLER] sending reply_photo, cover={bool(cover_url)}")
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
        print("[SEARCH HANDLER] reply sent ok", flush=True)
        log.info("[SEARCH HANDLER] reply sent ok")
    except Exception as e:
        import sys
        print(f"[SEARCH HANDLER] EXCEPTION: {e}\n{traceback.format_exc()}", flush=True)
        sys.stderr.flush()
        log.error(f"[SEARCH HANDLER] exception: {e}\n{traceback.format_exc()}")
        try:
            await update.message.reply_text(f"搜索出错：{str(e)}")
        except Exception:
            print("[SEARCH HANDLER] failed to send error reply", flush=True)
            log.error("[SEARCH HANDLER] failed to send error reply")


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
    # 番号精确匹配优先
    result = await info_client.search_videos(content_id=keyword, page=page, page_size=page_size)
    if result.get("total_count", 0) == 0:
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
    cover_url = jacket_full_url(first.get("jacket_thumb_url")) or first.get("jacket_full_url") or first.get("jacket_thumb_url")
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
    result = await info_client.search_videos(content_id=keyword, page=page, page_size=page_size)
    if result.get("total_count", 0) == 0:
        result = await info_client.search_videos(q=keyword, page=page, page_size=page_size)
    data = result.get("data", [])
    if not data:
        return

    first = data[0]
    content_id = first.get("content_id") or first.get("dvd_id", "")
    title = first.get("title_ja_translated") or first.get("title_ja", "")

    caption = f"🎬 <code>{content_id}</code>\n📌 {title}\n确认下载这部影片？"
    cover_url = jacket_full_url(first.get("jacket_thumb_url")) or first.get("jacket_full_url") or first.get("jacket_thumb_url")

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
    result = await info_client.search_videos(content_id=keyword, page=page, page_size=page_size)
    if result.get("total_count", 0) == 0:
        result = await info_client.search_videos(q=keyword, page=page, page_size=page_size)
    data = result.get("data", [])
    if not data:
        return

    first = data[0]
    content_id = first.get("content_id") or first.get("dvd_id", "")
    detail = await info_client.get_video(content_id)
    caption = _build_detail_caption(detail)
    cover_url = jacket_full_url(detail.get("jacket_thumb_url")) or detail.get("jacket_full_url") or detail.get("jacket_thumb_url")
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


async def search_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /id 命令：番号精确搜索"""
    import logging, traceback, sys
    log = logging.getLogger('telegram.bot')
    print(f"[ID HANDLER] invoked, args={context.args}", flush=True)
    log.info(f"[ID HANDLER] invoked, args={context.args}")
    try:
        if not context.args:
            await update.message.reply_text("用法：/id <番号>\n例：/id MIAA-784\n   /id abc-123")
            return
        content_id = " ".join(context.args).strip()
        print(f"[ID HANDLER] content_id={content_id}", flush=True)
        log.info(f"[ID HANDLER] content_id={content_id}")
        page = 1
        page_size = 3
        info_client = get_info_client()
        result = await info_client.search_videos(content_id=content_id, page=page, page_size=page_size)
        print(f"[ID HANDLER] got result, total={result.get('total_count', 0)}", flush=True)
        total = result.get("total_count", 0)
        data = result.get("data", [])
        if total == 0 or not data:
            await update.message.reply_text(f"未找到番号「{content_id}」相关影片")
            return
        total_pages = (total + page_size - 1) // page_size
        first = data[0]
        cid = first.get("content_id") or first.get("dvd_id", "")
        try:
            detail = await info_client.get_video(cid)
        except Exception:
            detail = first
        caption = _build_caption(detail, content_id, page, total_pages)
        cover_url = jacket_full_url(detail.get("jacket_thumb_url")) or detail.get("jacket_full_url") or detail.get("jacket_thumb_url")
        has_actress = bool(detail.get("actress_name"))
        if cover_url:
            await update.message.reply_photo(
                photo=cover_url, caption=caption, parse_mode="HTML",
                reply_markup=search_card_keyboard(content_id, page, total_pages, has_actress),
            )
        else:
            await update.message.reply_text(
                text=caption, parse_mode="HTML",
                reply_markup=search_card_keyboard(content_id, page, total_pages, has_actress),
            )
        print("[ID HANDLER] reply sent ok", flush=True)
    except Exception as e:
        print(f"[ID HANDLER] EXCEPTION: {e}\n{traceback.format_exc()}", flush=True)
        sys.stderr.flush()
        log.error(f"[ID HANDLER] exception: {e}\n{traceback.format_exc()}")
        try:
            await update.message.reply_text(f"搜索出错：{str(e)}")
        except Exception:
            print("[ID HANDLER] failed to send error reply", flush=True)
    try:
        from routers.download import create_download_by_content_id
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


# 兼容旧 export：download_callback = 统一的 callback_handler
download_callback = callback_handler
