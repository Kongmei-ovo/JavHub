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

def search_card_keyboard(keyword: str, page: int, total_pages: int, has_actress: bool = False) -> InlineKeyboardMarkup:
    """搜索结果卡片底部的翻页+操作按钮"""
    prev_callback = f"search:{keyword}:{page-1}" if page > 1 else "noop"
    next_callback = f"search:{keyword}:{page+1}" if page < total_pages else "noop"

    rows = [
        [
            InlineKeyboardButton("◀", callback_data=prev_callback),
            InlineKeyboardButton(f"第{page}页/共{total_pages}页", callback_data="noop"),
            InlineKeyboardButton("▶", callback_data=next_callback),
        ],
    ]
    if has_actress:
        rows.append([
            InlineKeyboardButton("🎬 下载", callback_data=f"confirm:{keyword}:{page}"),
            InlineKeyboardButton("📋 详情", callback_data=f"detail:{keyword}:{page}"),
            InlineKeyboardButton("⭐ 订阅", callback_data=f"subscribe:{keyword}:{page}"),
        ])
    else:
        rows.append([
            InlineKeyboardButton("🎬 下载", callback_data=f"confirm:{keyword}:{page}"),
            InlineKeyboardButton("📋 详情", callback_data=f"detail:{keyword}:{page}"),
        ])
    return InlineKeyboardMarkup(rows)


def confirm_download_keyboard(content_id: str, keyword: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 确认下载", callback_data=f"dl:{content_id}:{keyword}:{page}"),
            InlineKeyboardButton("❌ 取消", callback_data=f"search:{keyword}:{page}"),
        ]
    ])


def detail_keyboard(content_id: str, keyword: str, page: int, has_actress: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🎬 下载", callback_data=f"confirm_dl:{content_id}:{keyword}:{page}"),
            InlineKeyboardButton("🔄 返回搜索", callback_data=f"search:{keyword}:{page}"),
        ]
    ]
    if has_actress:
        rows.append([
            InlineKeyboardButton("⭐ 订阅演员", callback_data=f"subscribe:{keyword}:{page}"),
        ])
    return InlineKeyboardMarkup(rows)


def back_to_search_keyboard(keyword: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 返回搜索", callback_data=f"search:{keyword}:{page}")]
    ])
