from telegram import Update
from telegram.ext import ContextTypes
from database import add_subscription, get_subscriptions, delete_subscription

async def sub_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /sub add 命令"""
    if not context.args:
        await update.message.reply_text("用法：/sub add <演员名>")
        return

    actress_name = " ".join(context.args)

    # TODO: 需要通过 InfoClient 获取 actress_id
    # 暂时用名称代替
    try:
        add_subscription(actress_id=0, actress_name=actress_name, auto_download=False)
        await update.message.reply_text(f"✅ 已添加订阅：{actress_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ 添加失败：{str(e)}")

async def sub_del_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /sub del 命令"""
    if not context.args:
        await update.message.reply_text("用法：/sub del <演员名>")
        return

    actress_name = " ".join(context.args)

    try:
        subs = get_subscriptions()
        for sub in subs:
            if sub.get("actress_name") == actress_name:
                delete_subscription(sub["id"])
                await update.message.reply_text(f"✅ 已删除订阅：{actress_name}")
                return

        await update.message.reply_text(f"❌ 未找到订阅：{actress_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ 删除失败：{str(e)}")

async def sub_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /sub list 命令"""
    try:
        subs = get_subscriptions()

        if not subs:
            await update.message.reply_text("📋 暂无订阅")
            return

        text = "📋 订阅列表：\n\n"
        for sub in subs:
            name = sub.get("actress_name", "")
            auto = "☑️" if sub.get("auto_download") else "☐"
            text += f"{auto} {name}\n"

        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ 获取失败：{str(e)}")