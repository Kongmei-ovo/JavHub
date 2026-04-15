# Telegram Bot 影片检索功能设计

## 概述

在 JavHub Telegram Bot 中新增影片检索能力：用户发 `/search 番号` 或 `/search 关键词`，Bot 以**封面卡片 + 详细文字**形式回复，支持**翻页**和**下载确认**。

---

## 一、搜索入口

**命令**：`/search <关键词或番号>`

- 支持精确番号（如 `/search abc-123`）
- 支持关键词全文搜索

**交互**：用户发送后，Bot 返回第一页结果（3条）。

---

## 二、结果卡片展示

每条结果发送一张 **封面图** + **caption 文字**，caption 格式：

```
🎬 [番号]
📌 标题（翻译后，日文备选）
📅 2024-01-15 | ⏱ 120分钟
👤 演员名

─────────────────
[◀] 第1页/共3页 [▶]
[🎬 下载] [📋 详情] [⭐ 订阅]
```

**注意**：封面使用 `sendPhoto` + `caption`，后续翻页用 `editMessageCaption` 更新文字（封面保持不变）。

---

## 三、翻页

**按钮**：`[◀]` 和 `[▶]`

**callback_data 编码**：
```
search:{keyword}:{page}
```
例：`search:abc-123:2` 表示 keyword=abc-123 第2页

**翻页行为**：`editMessageCaption` 更新文字，键盘同步更新（翻页不重新发图）。

---

## 四、下载确认

**触发**：「🎬 下载」按钮

**行为**：更新消息内容为确认界面：
```
🎬 [番号] 📌 标题
确认下载这部影片？

[✅ 确认下载] [❌ 取消]
```

**callback_data**：
```
confirm:{content_id}:{keyword}:{page}
```

**确认后**：调用后端下载接口，返回「✅ 已加入下载队列」，键盘变为「🔄 返回搜索」。

**取消**：返回原卡片状态，`editMessageCaption` 恢复。

---

## 五、详情按钮

**触发**：「📋 详情」按钮

**行为**：调用 `editMessageCaption` 展示完整详情：

```
🎬 [番号] [服务来源]
📌 日文标题
📌 中文标题
📅 发行日期：2024-01-15
⏱ 时长：120分钟
🏷 题材：高清 / 中文字幕
👤 演员：演员A、演员B
📝 简介：...

[🎬 下载] [⭐ 订阅演员]
```

键盘：「🔄 返回搜索」按钮，`callback_data = search:{keyword}:{page}`

---

## 六、订阅按钮

**触发**：「⭐ 订阅」按钮

**行为**：直接调用订阅接口，发送确认消息：「✅ 已订阅 [演员名]」，5秒后删除。

---

## 七、状态管理

所有状态编码进 `callback_data`，无 server-side 状态：

| callback_data | 含义 |
|---|---|
| `search:{kw}:{page}` | 搜索翻页 |
| `confirm:{cid}:{kw}:{page}` | 下载确认 |
| `detail:{cid}:{kw}:{page}` | 查看详情 |
| `back:{kw}:{page}` | 返回搜索卡片 |

---

## 八、技术约束

1. **封面更新**：`editMessageCaption` 不改变已发送的图片，因此翻页/详情/确认的图片 URL 必须一致
2. **图片加载**：JavInfoApi 返回的封面 URL 需为完整 URL，优先使用 `jacket_full_url`
3. **翻页重建**：总页数变化时（如搜索结果更新），caption 中的分页信息同步更新
4. **错误处理**：搜索无结果时回复「未找到相关影片」

---

## 九、文件变更

- `backend/telegram_bot/handlers/search.py` — 重写 search_handler，支持分页和 callback
- `backend/telegram_bot/keyboards.py` — 新增 `search_card_keyboard`、`confirm_download_keyboard`、`detail_keyboard`
- `backend/telegram_bot/bot.py` — 注册 CallbackQueryHandler 捕获所有按钮回调
