from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import config

def create_bot() -> Application:
    """创建 Telegram Bot 应用"""
    bot_token = config.telegram.get("bot_token", "")

    app = Application.builder().token(bot_token).build()

    # 注册命令处理器
    from handlers.search import search_handler, download_callback, callback_handler as search_callback_handler
    from handlers.subscription import sub_add_handler, sub_del_handler, sub_list_handler
    from handlers.status import status_handler

    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("sub", lambda update, context: handle_sub_command(update, context)))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("check", check_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # 注册回调处理器
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

async def check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /check 命令"""
    # TODO: 调用 SubscriptionService.check_all()
    await update.message.reply_text("🔄 正在检查订阅更新...")

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
    app = create_bot()
    await app.run_polling()
