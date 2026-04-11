from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Any

def search_result_keyboard(content_id: str, actress_name: str = "") -> InlineKeyboardMarkup:
    """搜索结果 InlineKeyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🎬 下载", callback_data=f"download:{content_id}"),
            InlineKeyboardButton("📋 详情", callback_data=f"detail:{content_id}"),
        ],
    ]
    if actress_name:
        keyboard.append([
            InlineKeyboardButton("⭐ 订阅演员", callback_data=f"subscribe:{actress_name}"),
        ])
    return InlineKeyboardMarkup(keyboard)

def download_confirm_keyboard(content_id: str) -> InlineKeyboardMarkup:
    """下载确认 InlineKeyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ 确认下载", callback_data=f"confirm:{content_id}"),
            InlineKeyboardButton("❌ 取消", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def subscription_keyboard(action: str, actress_name: str) -> InlineKeyboardMarkup:
    """订阅操作 InlineKeyboard"""
    keyboard = [
        [
            InlineKeyboardButton("➕ 订阅", callback_data=f"sub_add:{actress_name}"),
            InlineKeyboardButton("➖ 取消订阅", callback_data=f"sub_del:{actress_name}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)