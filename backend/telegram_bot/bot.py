from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import config

def create_bot() -> Application:
    """创建 Telegram Bot 应用"""
    bot_token = config.telegram.get("bot_token", "")

    app = Application.builder().token(bot_token).build()

    # 注册命令处理器
    from telegram_bot.handlers.search import search_handler, download_callback, callback_handler as search_callback_handler
    from telegram_bot.handlers.subscription import sub_add_handler, sub_del_handler, sub_list_handler
    from telegram_bot.handlers.status import status_handler

    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("sub", lambda update, context: handle_sub_command(update, context)))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("check", check_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # 注册回调处理器
    app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="^subscribe:"))
    app.add_handler(CallbackQueryHandler(download_callback))
    app.add_handler(CallbackQueryHandler(search_callback_handler))

    return app

async def handle_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /sub 命令（带子命令）"""
    if not context.args:
        await sub_list_handler(update, context)
        return

    sub_action = context.args[0].lower()

    if sub_action == "add":
        context.args = context.args[1:]
        await sub_add_handler(update, context)
    elif sub_action == "del":
        context.args = context.args[1:]
        await sub_del_handler(update, context)
    elif sub_action == "list":
        await sub_list_handler(update, context)
    else:
        await update.message.reply_text("用法：/sub <add/del/list> [演员名]")

async def check_handler(update, context):
    """处理 /check 命令 — 手动触发订阅检查"""
    await update.message.reply_text("🔄 正在检查订阅更新...")
    try:
        from services.subscription import check_all_subscriptions
        new_movies = await check_all_subscriptions()
        if new_movies:
            text = f"📢 发现 {len(new_movies)} 部新片！\n\n"
            for movie in new_movies[:10]:
                text += f"• `{movie['code']}` - {movie.get('actress_name', '未知')}\n"
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text("✅ 暂无新片")
    except Exception as e:
        await update.message.reply_text(f"❌ 检查失败：{str(e)}")

async def subscribe_callback(update, context):
    """处理订阅按钮回调"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("subscribe:"):
        return

    parts = data.split(":", 2)
    if len(parts) < 2:
        return

    actress_name = parts[1] if len(parts) == 2 else parts[1]

    try:
        # 查找 actress_id
        from modules.info_client import get_info_client
        client = get_info_client()
        result = await client.list_actresses(page=1, page_size=100)
        items = result.get("data", []) if isinstance(result, dict) else []

        actress_id = 0
        for item in items:
            names = [
                item.get("name_kanji", ""),
                item.get("name_romaji", ""),
                item.get("name_en", ""),
                item.get("name_ja", ""),
                item.get("name", ""),
            ]
            if actress_name in names:
                actress_id = item.get("id", 0)
                break

        from database import toggle_subscription
        result = toggle_subscription(actress_id, actress_name)
        if result["subscribed"]:
            await query.edit_message_text(f"✅ 已订阅：{actress_name}")
        else:
            await query.edit_message_text(f"❌ 已取消订阅：{actress_name}")
    except Exception as e:
        await query.edit_message_text(f"❌ 操作失败：{str(e)}")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /help 命令"""
    text = """
📖 命令帮助：

🔍 /search <关键词> - 搜索影片
📋 /sub add <演员> - 添加订阅
📋 /sub del <演员> - 删除订阅
📋 /sub list - 查看订阅
📥 /status - 下载队列
🔄 /check - 检查订阅更新
❓ /help - 帮助信息
"""
    await update.message.reply_text(text)

async def start_polling():
    """启动 Bot 轮询"""
    import threading
    import asyncio

    app = create_bot()
    await app.initialize()

    # 注册 bot 命令菜单（initialize 之后 bot 才真正连接）
    await app.bot.set_my_commands([
        BotCommand("search", "搜索影片"),
        BotCommand("sub", "订阅管理"),
        BotCommand("status", "下载队列"),
        BotCommand("check", "检查订阅更新"),
        BotCommand("help", "帮助"),
    ])

    # 在独立线程里跑 run_polling（子线程需要自己的 loop）
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.run_polling(stop_signals=None))

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # 阻塞等待 daemon 线程
    while t.is_alive():
        await asyncio.sleep(0.5)
