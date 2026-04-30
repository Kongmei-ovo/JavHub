# 订阅演员功能设计文档

> 日期: 2026-04-30
> 状态: 已确认

## 概述

订阅演员功能允许用户关注特定演员，系统定时检查其新作品，通过 Telegram 通知用户，并支持磁力离线下载和 m3u8 在线播放两种获取方式。

## 设计决策

| 决策项 | 结论 |
|--------|------|
| 收藏 vs 订阅 | 独立系统，互不干扰。收藏是被动书签，订阅是主动监控 |
| 订阅入口 | Subscription.vue（搜索）、DiscoveryDetail.vue（演员详情）、Telegram Bot |
| 数据来源 | 自建爬虫（javbus/javdb/javlib）获取磁力 + 参考 NASSAV 实现 m3u8 爬虫 |
| 下载路径 | A: 磁力→OpenList→115云盘离线 · B: m3u8在线播放/下载/转存云盘 |
| 自动下载 | 订阅级 auto_download 开关，开启后按全局配置方式自动下载 |
| 通知行为 | Telegram 推送，可配置是否附带 m3u8 播放链接 |
| 影片详情 | 不受订阅约束，用户可自由选择任意路径 |

## 系统架构

```
订阅入口 → 订阅存储 → 定时检查 → 通知用户 → 用户操作
                                              ├─ 磁力下载 → OpenList → 115云盘 → Emby入库
                                              └─ m3u8播放 → 前端直链播放 / 转存云盘
```

### 模块拆解

#### 1. 爬虫层 (backend/sources/)

**磁力源** — 实现现有 MagnetSource 协议：
- `search(keyword)` → 番号列表
- `get_detail(content_id)` → 磁力链接详情
- `get_actress_videos(actress_name)` → 演员最新片单

需要实现至少一个源（优先 javbus），其余可后续补充。

**m3u8 源** — 新增，参考 NASSAV 项目：
- `search(content_id)` → m3u8 播放地址
- 返回结构包含 m3u8 直链、标题、时长等

#### 2. 订阅检查 (backend/services/subscription.py)

`check_all_subscriptions()` 流程：
1. 遍历所有 enabled 订阅
2. 对每条订阅，调用爬虫 `get_actress_videos(actress_name)` 获取最新片单
3. 对比 Emby 已有片库（`EmbyClient.check_exists()`）
4. 筛选出不在 Emby 中的新片
5. 更新 `last_check` 时间
6. 返回新片列表

#### 3. 自动下载 (backend/services/downloader.py + scheduler/)

订阅检查发现新片后，如果订阅的 `auto_download=ON`：
- 按全局配置的下载方式自动执行：
  - **磁力模式**：爬虫获取磁力 → `openlist_client.add_offline_download()` → 115云盘
  - **m3u8 模式**：爬虫获取 m3u8 → 下载文件 → AList 上传到云盘

全局下载方式在 `config.yaml` 中配置，默认磁力。

#### 4. 通知层 (backend/services/notification.py + telegram_bot/)

Telegram 通知内容根据 auto_download 状态不同：

**auto_download=ON 时：**
```
🎬 演员名 有新片已自动下载
XXX-001 标题名
XXX-002 标题名
[播放] (可选，后台配置)
```

**auto_download=OFF 时：**
```
🎬 演员名 有新片
XXX-001 标题名
XXX-002 标题名
[磁力下载] [在线播放] (内联按钮)
```

通知是否附带播放链接在 Telegram 设置中配置。

#### 5. 前端

**Subscription.vue 修复与增强：**
- 补全 `api.searchActors()` 方法（调用后端搜索演员 API）
- 补全 `api.checkSubscription(id)` 方法（单条订阅检查）
- 已订阅列表展示优化

**DiscoveryDetail.vue 增强：**
- 演员详情页工具栏加订阅按钮（收藏按钮旁边）
- 使用 `subscriptionState.js` 管理状态（类似 favoriteState.js）

**影片详情页增强：**
- VideoModal 中增加「m3u8 播放」按钮（与现有磁力下载并列）
- 增加「转存到云盘」按钮（通过 AList 上传）
- m3u8 内嵌播放器组件

#### 6. 数据层

**subscriptions 表增强：**
```sql
ALTER TABLE subscriptions ADD COLUMN last_check TEXT;
ALTER TABLE subscriptions ADD COLUMN last_found TEXT;
```

**Pydantic 模型对齐：**
- 统一命名：`actor_name` → `actress_name`（或反之，保持一致）
- 补充 `actress_id` 字段

**新增 stream_links 表（可选）：**
```sql
CREATE TABLE IF NOT EXISTS stream_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,
    m3u8_url TEXT NOT NULL,
    source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT
);
```
缓存 m3u8 地址，避免重复爬取。

#### 7. 配置项

**config.yaml 新增：**
```yaml
subscription:
  default_download_method: "magnet"  # magnet | m3u8
  check_hour: 2
  check_enabled: true

telegram:
  notify_with_play_link: true  # 通知中附带播放链接
```

**Config.vue 对应 UI：**
- 下载方式选择（磁力/m3u8）
- 通知带播放链接开关

## API 端点

### 修复现有

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/subscriptions/search?q=xxx` | 搜索演员（供前端订阅搜索用） |
| POST | `/api/v1/subscriptions/{id}/check` | 单条订阅检查 |

### 新增

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/stream/{content_id}` | 获取 m3u8 播放地址 |
| POST | `/api/v1/stream/{content_id}/transfer` | m3u8 转存到云盘 |
| PUT | `/api/v1/subscriptions/{id}` | 更新订阅设置 (enabled, auto_download) |

## 实施优先级

### P0 — 修复断裂 + 基础功能

1. 修复 `api.searchActors()` — 后端新增搜索端点，前端 API client 补全
2. 修复 `api.checkSubscription(id)` — 后端新增单条检查端点
3. 实现至少一个磁力源的 `get_actress_videos()`（javbus 优先）
4. 连通调度器 → OpenList 自动下载（scheduler/tasks.py 中取消注释并完善）
5. 修复 Telegram bot `actress_id=0`（通过名称查 InfoClient 获取真实 ID）
6. 修复 Telegram `/check` 命令（调用 SubscriptionService.check_all()）
7. DiscoveryDetail.vue 演员详情加订阅按钮
8. subscriptions 表补充 last_check / last_found 列

### P1 — m3u8 播放 + 下载

1. 参考 NASSAV 实现 m3u8 爬虫源
2. 新增 `/api/v1/stream` 端点
3. 前端 m3u8 播放器组件
4. m3u8 转存到云盘功能（AList 上传）
5. 影片详情页集成双路径选择
6. 全局下载方式配置

### P2 — 体验优化

1. Telegram 通知带播放链接配置
2. Telegram 内联按钮（下载/播放回调）
3. 多磁力源实现（javdb/javlib）
4. stream_links 缓存表
5. 订阅管理增强（批量操作、启用/暂停）
