# AV Downloader 重构设计文档

## 1. 项目概述

### 1.1 背景
AV Downloader 需要从原有的多源爬虫模式重构为基于 JavInfoApi (元数据服务) 的模块化架构，实现：
- 元数据查询与下载逻辑分离
- 下载源可插拔
- Telegram Bot 功能模块化
- Emby 库检测增强（缺失演员影片 + 去重管理）
- 前端 UI 功能补全

### 1.2 最终架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Main App (FastAPI) :8000                     │
├─────────────────────────────────────────────────────────────────────┤
│  Modules (Protocol 接口定义，实现可插拔)                              │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ Info Module │  │ Emby Module │  │     Download Module         │ │
│  │             │  │             │  │                             │ │
│  │ • 搜索影片   │  │ • 库检测    │  │  ┌─────────────────────┐   │ │
│  │ • 演员查询   │  │ • 去重      │  │  │  MagnetSource       │   │ │
│  │ • 分类/厂商  │  │ • 缺失检测  │  │  │  (Protocol)         │   │ │
│  │ • 元数据    │  │             │  │  ├─────────────────────┤   │ │
│  └──────┬──────┘  └──────┬──────┘  │  │  JavBusSource      │   │ │
│         │                │        │  │  JavDBSource       │   │ │
│         │         JavInfoApi       │  │  JavLibSource       │   │ │
│         │         (外部:8080)      │  │  ...                │   │ │
│         │                       │  └─────────────────────┘   │ │
│         │                       │         ▲                  │ │
│         │                       │    SourceRegistry          │ │
│  ┌──────┴──────┐  ┌─────────────┴──┴─────────────────────────┐ │
│  │   Offline   │  │              Telegram Module              │ │
│  │  Download   │  │                                            │ │
│  │  Module     │  │  • /search, /sub, /check, /status        │ │
│  │             │  │  • Inline buttons (下载确认)               │ │
│  │  OpenList   │  │  • 通知推送 (新片/下载完成/订阅更新)        │ │
│  │  (115)      │  │                                            │ │
│  └─────────────┘  └────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │ Scheduler   │  │ Subscription │  │       Frontend          │   │
│  │ Module      │  │   Module     │  │       (Vue 3)            │   │
│  │             │  │             │  │                         │   │
│  │ • 定时检查   │  │ • 演员订阅   │  │  • 首页/搜索/订阅/配置  │   │
│  │ • 订阅更新   │  │ • 新片检测   │  │  • 缺失演员看板        │   │
│  │             │  │ • 自动下载   │  │  • 去重管理界面        │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
           │
           │ HTTP API
           ▼
┌──────────────────┐     ┌──────────────────┐
│   JavInfoApi     │     │   PostgreSQL     │
│   :8080          │────►│   (r18.dev数据)   │
│   (独立服务)      │     │                   │
└──────────────────┘     └──────────────────┘
```

---

## 2. 模块设计

### 2.1 Info Module (元数据模块)

**职责：** 封装对 JavInfoApi 的所有 HTTP 调用

**接口设计：**
```python
class InfoClient:
    async def search_videos(
        q: str | None = None,
        content_id: str | None = None,
        maker_id: int | None = None,
        series_id: int | None = None,
        actress_id: int | None = None,
        category_id: int | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> VideoListResponse: ...

    async def get_video(content_id: str) -> VideoDetailResponse: ...

    async def list_makers() -> list[Maker]: ...
    async def list_series() -> list[Series]: ...
    async def list_categories() -> list[Category]: ...

    async def list_actresses(page: int = 1, page_size: int = 20) -> ActressListResponse: ...
    async def get_actress(id: int) -> ActressDetailResponse: ...
    async def get_actress_videos(actress_id: int) -> VideoListResponse: ...

    async def get_stats() -> StatsResponse: ...
```

**配置：**
```yaml
javinfo:
  api_url: "http://localhost:8080"
  timeout: 30
```

### 2.2 Emby Module

**职责：** Emby 库检测、去重、缺失演员统计

**接口设计：**
```python
class EmbyClient:
    # 库检测
    async def check_exists(content_id: str) -> bool: ...
    async def get_all_movies() -> list[EmbyItem]: ...

    # 去重
    async def find_duplicates(
        javinfo: InfoClient
    ) -> list[DuplicateItem]:
        """
        比对 Emby 库中影片名称与 JavInfoApi 元数据名称
        返回可疑重复列表
        """
        ...

    async def delete_item(item_id: str) -> bool: ...

    # 缺失检测
    async def get_missing_actresses_summary(
        javinfo: InfoClient
    ) -> list[ActressMissingSummary]:
        """
        遍历所有订阅演员，计算其作品在 Emby 中的缺失数量
        返回按缺失数量降序的列表
        """
        ...
```

**DuplicateItem 模型：**
```python
class DuplicateItem(BaseModel):
    emby_item_id: str
    emby_name: str
    content_id: str | None  # JavInfoApi 匹配的番号
    javinfo_title: str | None
    similarity: float  # 相似度 0-1
    reason: str  # 重复原因描述
```

**ActressMissingSummary 模型：**
```python
class ActressMissingSummary(BaseModel):
    actress_id: int
    actress_name: str
    total_in_javinfo: int
    missing_count: int
    missing_videos: list[MissingVideo]  # 按发行日期排序
```

### 2.3 Download Module (可插拔架构)

#### 2.3.1 MagnetSource Protocol

```python
from typing import Protocol

class MagnetSource(Protocol):
    """下载源协议 - 所有下载源必须实现此接口"""

    name: str  # 唯一标识，如 "javbus", "javdb", "javlib"

    async def search(self, keyword: str) -> list[MagnetInfo]:
        """搜索磁力链接"""
        ...

    async def get_detail(self, content_id: str) -> MovieDetail | None:
        """获取影片详情（含磁力列表）"""
        ...

    async def get_actress_videos(self, actress_name: str) -> list[MagnetInfo]:
        """获取某演员的最新作品（用于订阅检查）"""
        ...
```

#### 2.3.2 SourceRegistry

```python
class SourceRegistry:
    _sources: dict[str, MagnetSource] = {}
    _priority: list[str] = []  # 搜索优先级顺序

    @classmethod
    def register(cls, source: MagnetSource) -> None:
        """注册下载源"""
        cls._sources[source.name] = source
        if source.name not in cls._priority:
            cls._priority.append(source.name)

    @classmethod
    def get(cls, name: str) -> MagnetSource | None:
        """获取指定下载源"""
        return cls._sources.get(name)

    @classmethod
    def all(cls) -> list[MagnetSource]:
        """获取所有已注册下载源"""
        return list(cls._sources.values())

    @classmethod
    def search_all(cls, keyword: str) -> list[MagnetInfo]:
        """按优先级遍历所有源搜索，返回聚合结果"""
        results = []
        for name in cls._priority:
            source = cls._sources.get(name)
            if source:
                try:
                    results.extend(await source.search(keyword))
                except Exception:
                    continue  # 单个源失败不影响其他源
        return results
```

#### 2.3.3 内置下载源实现

**JavBusSource：**
- 实现 `MagnetSource` Protocol
- 调用 JavBus API 或爬虫获取数据
- 支持登录态（cookie 管理）

**JavDBSource：**
- 实现 `MagnetSource` Protocol
- JavDB 站点数据

**JavLibSource：**
- 实现 `MagnetSource` Protocol
- JavLib 站点数据

#### 2.3.4 配置

```yaml
sources:
  priority:
    - javbus
    - javdb
    - javlib

javbus:
  enabled: true
  api_url: "https://www.javbus.com"
  # ...

javdb:
  enabled: false
  # ...

javlib:
  enabled: false
  # ...
```

### 2.4 Offline Download Module

**职责：** 封装 OpenList (115) API

```python
class OpenListClient:
    async def add_offline_download(magnet: str, path: str) -> str:
        """添加离线下载，返回任务ID"""

    async def get_task_status(task_id: str) -> TaskStatus:
        """获取任务状态"""

    async def delete_task(task_id: str) -> bool:
        """删除离线任务"""
```

### 2.5 Telegram Module

#### 2.5.1 命令体系

| 命令 | 功能 | 说明 |
|------|------|------|
| `/search <关键词>` | 搜索影片 | 返回影片信息 + InlineButtons |
| `/sub add <演员名>` | 添加订阅 | |
| `/sub list` | 订阅列表 | |
| `/sub del <演员名>` | 删除订阅 | |
| `/check` | 手动检查订阅 | 立即执行订阅更新检查 |
| `/status` | 下载队列状态 | 显示当前下载任务 |
| `/help` | 帮助信息 | |

#### 2.5.2 Inline 交互

**搜索结果消息：**
```
🎬 ABC-123
白石茉莉奈 2024-03-15 120分钟

[下载] [查看详情] [加入订阅]
```

**下载确认按钮：**
- 点击 `/search ABC-123` 后
- Bot 回复带 InlineKeyboard 的消息
- 用户点击「下载」→ 触发 OpenList 下载
- 用户点击「加入订阅」→ 添加该演员到订阅

#### 2.5.3 主动通知

| 触发条件 | 通知内容 |
|----------|----------|
| 订阅检查发现新片 | 🎬 白石茉莉奈 新片：ABC-123 [下载] |
| OpenList 下载完成 | ✅ ABC-123 下载完成 |
| 订阅更新完成 | 📋 订阅检查完成：共 8 个订阅，2 部新片 |

### 2.6 Subscription Module

```python
class SubscriptionService:
    async def check_all() -> list[SubscriptionUpdate]:
        """检查所有订阅，返回有新片的订阅列表"""
        ...

    async def auto_download_new(updates: list[SubscriptionUpdate]):
        """对发现的新片自动下载"""
        ...
```

### 2.7 Scheduler Module

```python
class SchedulerService:
    # 每日定时任务
    subscription_check_hour: int = 2  # 凌晨2点

    # 可选：定期刷新缺失演员缓存
    missing_check_interval_hours: int = 6
```

---

## 3. 数据库设计

### 3.1 SQLite 表结构

**subscriptions 表（已有）：**
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    actress_id INTEGER,
    actress_name TEXT NOT NULL,
    created_at DATETIME,
    auto_download BOOLEAN DEFAULT 0
);
```

**download_tasks 表（已有）：**
```sql
CREATE TABLE download_tasks (
    id INTEGER PRIMARY KEY,
    content_id TEXT,
    title TEXT,
    magnet TEXT,
    status TEXT,  -- pending, downloading, completed, failed
    created_at DATETIME,
    completed_at DATETIME,
    openlist_task_id TEXT
);
```

**logs 表（已有）：**
```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY,
    level TEXT,
    message TEXT,
    created_at DATETIME
);
```

**ignored_duplicates 表（新增）：**
```sql
CREATE TABLE ignored_duplicates (
    id INTEGER PRIMARY KEY,
    content_id TEXT,
    emby_item_id TEXT NOT NULL,
    ignored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);
```

**actress_missing_summary 表（新增，缓存）：**
```sql
CREATE TABLE actress_missing_summary (
    id INTEGER PRIMARY KEY,
    actress_id INTEGER NOT NULL UNIQUE,
    actress_name TEXT NOT NULL,
    total_in_javinfo INTEGER,
    missing_count INTEGER,
    missing_videos_json TEXT,  -- JSON 序列化的缺失影片列表
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. API 设计

### 4.1 后端 API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| **搜索与元数据** | | |
| GET | `/api/v1/videos/search` | 搜索影片（透传 JavInfoApi） |
| GET | `/api/v1/videos/{content_id}` | 影片详情 |
| GET | `/api/v1/actresses/{id}` | 演员详情 |
| GET | `/api/v1/actresses/{id}/videos` | 演员作品列表 |
| GET | `/api/v1/makers` | 厂商列表 |
| GET | `/api/v1/series` | 系列列表 |
| GET | `/api/v1/categories` | 题材列表 |
| GET | `/api/v1/stats` | 统计数据 |
| **下载** | | |
| POST | `/api/downloads` | 创建下载任务 |
| GET | `/api/downloads` | 下载列表 |
| DELETE | `/api/downloads/{id}` | 删除任务 |
| **订阅** | | |
| GET | `/api/subscriptions` | 订阅列表 |
| POST | `/api/subscriptions` | 添加订阅 |
| DELETE | `/api/subscriptions/{id}` | 删除订阅 |
| POST | `/api/subscriptions/check` | 手动检查订阅 |
| **缺失检测** | | |
| GET | `/api/missing/actresses` | 缺失演员摘要列表 |
| GET | `/api/missing/actresses/{id}` | 某演员缺失影片详情 |
| POST | `/api/missing/actresses/refresh` | 刷新缺失缓存 |
| **去重** | | |
| GET | `/api/duplicates` | 可疑重复列表 |
| POST | `/api/duplicates/{emby_item_id}/delete` | 删除 Emby 条目 |
| POST | `/api/duplicates/{emby_item_id}/ignore` | 忽略可疑重复 |
| **配置** | | |
| GET | `/api/config` | 获取配置 |
| PUT | `/api/config` | 更新配置 |
| **其他** | | |
| GET | `/api/logs` | 日志 |
| GET | `/health` | 健康检查 |

### 4.2 请求/响应模型

**GET /api/duplicates 响应：**
```json
{
  "data": [
    {
      "emby_item_id": "abc123",
      "emby_name": "白石茉莉奈 ABC-001",
      "content_id": "ABC-001",
      "javinfo_title": "白石茉莉奈 ABC-001 完整标题",
      "similarity": 0.95,
      "reason": "Emby 名称与 JavInfoApi 番号高度匹配"
    }
  ],
  "total": 5
}
```

**GET /api/missing/actresses 响应：**
```json
{
  "data": [
    {
      "actress_id": 1,
      "actress_name": "白石茉莉奈",
      "total_in_javinfo": 50,
      "missing_count": 5
    }
  ],
  "total": 12
}
```

**GET /api/missing/actresses/{id} 响应：**
```json
{
  "actress_id": 1,
  "actress_name": "白石茉莉奈",
  "missing_count": 5,
  "videos_by_year": {
    "2024": [
      {
        "content_id": "ABC-123",
        "title": "白石茉莉奈 2024作品",
        "release_date": "2024-03-15",
        "jacket_thumb_url": "https://..."
      }
    ],
    "2023": [...]
  }
}
```

---

## 5. 前端设计

### 5.1 路由结构

```
/                   # 仪表盘
/search             # 搜索页面
/subscription       # 订阅管理
/missing            # 缺失演员看板
/missing/:id       # 缺失演员详情
/duplicates         # 去重管理
/config             # 配置页面
/logs               # 日志页面
```

### 5.2 仪表盘 (/)

**布局：**
```
┌─────────────────────────────────────────────────────────────┐
│  仪表盘                                              [刷新] │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 下载队列  │ │ 活跃订阅  │ │ 缺少数    │ │ 可疑重复  │       │
│  │    12    │ │    8     │ │   47     │ │    5     │       │
│  │  ↗跳转   │ │  ↗跳转   │ │  ↗跳转   │ │  ↗跳转   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│  最近下载                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ABC-123  白石茉莉奈  2024-01-15  已完成                │   │
│  │ XYZ-456  明日花绮罗  2024-01-14  下载中 45%           │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  快捷操作                                                    │
│  [搜索影片] [管理订阅] [检查更新] [手动添加订阅]              │
└─────────────────────────────────────────────────────────────┘
```

**交互：**
- 四个统计卡片可点击跳转对应页面
- 最近下载列表可点击进入详情
- 快捷操作按钮触发对应功能

### 5.3 搜索页面 (/search)

**搜索栏：**
- 支持关键词输入（标题、番号模糊匹配）
- 右侧下拉支持按 厂商/系列/演员/题材 筛选（可填也可选，支持联想补全）
- 排序：按名称/番号排序

**搜索结果（卡片列表）：**
```
┌──────────┐ ┌──────────┐ ┌──────────┐
│  [封面]  │ │  [封面]  │ │  [封面]  │
│ ABC-123 │ │ DEF-456  │ │ GHI-789  │
│白石茉莉奈│ │明日花绮罗 │ │  三上悠亚 │
│2024-03-15│ │2024-02-20│ │2024-01-10│
└──────────┘ └──────────┘ └──────────┘
```

**详情弹窗（点击卡片）：**
```
┌─────────────────────────────────────────────────────────────┐
│  [封面大图]                                                  │
│                                                             │
│  ABC-123  ★★★★☆                                           │
├─────────────────────────────────────────────────────────────┤
│  番号: ABC-123        发行日期: 2024-03-15                   │
│  厂商: [S1]           时长: 120分钟                         │
│  系列: [S1 Premium]   题材: [单体作品] [高画质]              │
│                                                             │
│  演员: [白石茉莉奈] [点击跳转检索]                          │
│                                                             │
│  磁力列表:                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ABC-123 1080P  2.5GB  ✓  [下载]                     │   │
│  │ ABC-123 720P   1.2GB  ✓  [下载]                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                                            [关闭]          │
└─────────────────────────────────────────────────────────────┘
```

**交互：**
- 厂商、系列、题材、演员均可点击跳转回搜索页，带对应筛选条件
- 磁力点击下载

### 5.4 缺失演员看板 (/missing)

**列表页：**
```
┌─────────────────────────────────────────────────────────────┐
│  缺失演员看板                                    [刷新缓存] │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [头像] 白石茉莉奈    缺失 5/50 部         [查看详情] │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ [头像] 明日花绮罗    缺失 3/30 部         [查看详情] │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ [头像] 三上悠亚      缺失 2/25 部         [查看详情] │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 5.5 缺失演员详情 (/missing/:id)

**布局：**
```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回    白石茉莉奈  (缺失 5 部)              [一键下载] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  2024 年                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [封面] │ ABC-123  标题文字                │ [下载][忽略] │
│  │        │ 2024-03-15                             │         │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [封面] │ DEF-456  标题文字                │ [下载][忽略] │
│  │        │ 2024-05-20                             │         │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  2023 年                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [封面] │ GHI-789  标题文字                │ [下载][忽略] │
│  │        │ 2023-08-10                             │         │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                                                    [一键下载] │
└─────────────────────────────────────────────────────────────┘
```

**卡片样式：**
- 竖向长方形卡片
- 顶部封面图
- 底部数据区：番号 + 标题 + 发行日期
- 右侧操作按钮：[下载] [忽略]

### 5.6 去重管理 (/duplicates)

**布局：**
```
┌─────────────────────────────────────────────────────────────┐
│  去重管理                                        [重新扫描] │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [封面] ABC-123  白石茉莉奈                           │   │
│  │       Emby名称: ABC-123                             │   │
│  │       匹配番号: ABC-123  (相似度 95%)               │   │
│  │       [删除] [忽略]                                 │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ [封面] XYZ-456  明日花绮罗                           │   │
│  │       Emby名称: 明日花 XYZ-456                      │   │
│  │       匹配番号: XYZ-456  (相似度 88%)               │   │
│  │       [删除] [忽略]                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 5.7 配置页面 (/config)

**布局（按功能分组）：**

```
┌─────────────────────────────────────────────────────────────┐
│  配置                                                        │
├─────────────────────────────────────────────────────────────┤
│  ▼ OpenList (115离线下载)                                   │
│    API地址: [________________]                               │
│    用户名:   [________________]                               │
│    密码:    [*******] [显示/隐藏]                           │
│    默认路径: [________________]                               │
│                                                             │
│  ▼ Emby                                                    │
│    API地址: [________________]                               │
│    API密钥: [________________]                               │
│                                                             │
│  ▼ Telegram                                                │
│    Bot Token: [________________]                           │
│    授权用户: [________________] (逗号分隔)                  │
│                                                             │
│  ▼ 通知设置                                                 │
│    [x] 订阅更新通知    [x] 下载完成通知    [x] 新片通知     │
│                                                             │
│  ▼ 下载源优先级 (拖拽排序)                                   │
│    [1] JavBus  [2] JavDB  [3] JavLib                        │
│                                                             │
│  ▼ 自动下载                                                │
│    [x] 启用自动下载                                         │
│                                                             │
│  ▼ 定时任务                                                 │
│    订阅检查时间: [02] 点                                    │
│    缺失缓存刷新: [6] 小时                                   │
│                                                             │
│                                                    [保存]   │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Telegram Bot 详细设计

### 6.1 命令列表

| 命令 | 触发条件 | 响应 |
|------|----------|------|
| `/search <关键词>` | 用户发送 | 搜索结果 + InlineKeyboard |
| `/sub add <演员>` | 用户发送 | 添加订阅成功/失败 |
| `/sub del <演员>` | 用户发送 | 删除订阅成功/失败 |
| `/sub list` | 用户发送 | 订阅列表 |
| `/check` | 用户发送 | 立即执行订阅检查，返回新片列表 |
| `/status` | 用户发送 | 下载队列状态 |
| `/help` | 用户发送 | 帮助信息 |

### 6.2 Inline Keyboard 设计

**搜索结果消息：**
```
🎬 ABC-123 | 白石茉莉奈 | 2024-03-15 | 120分钟

[🎬下载] [📋详情] [⭐订阅演员]
```

**下载确认（点击后二次确认）：**
```
确认下载 ABC-123 吗？

[✅确认] [❌取消]
```

### 6.3 主动推送模板

**新片发现：**
```
🎬 订阅更新 - 白石茉莉奈

发现新片：ABC-123
发行日期：2024-03-15
厂商：S1

[🎬下载] [📋查看详情]
```

**下载完成：**
```
✅ 下载完成

ABC-123 - 白石茉莉奈
存放路径：/115/AV/ABC-123
```

---

## 7. 部署架构

### 7.1 Docker Compose

```yaml
version: '3.8'

services:
  javinfoapi:
    image: javinfoapi:latest
    container_name: javinfoapi
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/javinfo
    depends_on:
      - postgres

  avdownloader:
    image: avdownloader:latest
    container_name: avdownloader
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config.yaml
    depends_on:
      - javinfoapi

  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=javinfo
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 7.2 配置 (config.yaml)

```yaml
# JavInfoApi 连接
javinfo:
  api_url: "http://javinfoapi:8080"
  timeout: 30

# OpenList (115)
openlist:
  api_url: "https://your-openlist.com"
  username: "your-username"
  password: "your-password"
  default_path: "/115/AV"

# Emby
emby:
  api_url: "http://your-emby:8096"
  api_key: "your-api-key"

# Telegram
telegram:
  bot_token: "123456:ABC-DEF..."
  allowed_user_ids:
    - "123456789"

# 下载源
sources:
  priority:
    - javbus
    - javdb
    - javlib

javbus:
  enabled: true
  api_url: "https://www.javbus.com"
  cookies: {}  # 可选，登录态

javdb:
  enabled: false
  api_url: "https://www.javdb.com"

javlib:
  enabled: false
  api_url: "https://www.javlib.com"

# 通知
notification:
  enabled: true
  telegram: true
  auto_download_notify: true
  download_complete_notify: true
  new_movie_notify: true

# 定时
scheduler:
  subscription_check_hour: 2
  missing_check_interval_hours: 6

# 自动下载
auto_download:
  enabled: false
```

---

## 8. 项目目录结构

```
avdownloader/
├── backend/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 配置管理
│   ├── database.py                # SQLite 操作
│   ├── models/                    # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── video.py
│   │   ├── actress.py
│   │   ├── subscription.py
│   │   ├── download.py
│   │   ├── duplicate.py
│   │   └── missing.py
│   ├── routers/                   # API 路由
│   │   ├── __init__.py
│   │   ├── videos.py              # /api/v1/videos
│   │   ├── actresses.py           # /api/v1/actresses
│   │   ├── makers.py              # /api/v1/makers
│   │   ├── series.py             # /api/v1/series
│   │   ├── categories.py          # /api/v1/categories
│   │   ├── downloads.py           # /api/downloads
│   │   ├── subscriptions.py       # /api/subscriptions
│   │   ├── missing.py             # /api/missing
│   │   ├── duplicates.py          # /api/duplicates
│   │   ├── config.py              # /api/config
│   │   ├── logs.py                # /api/logs
│   │   └── health.py              # /health
│   ├── modules/                   # 核心模块
│   │   ├── __init__.py
│   │   ├── info_client.py         # JavInfoApi 客户端
│   │   ├── emby_client.py         # Emby 客户端
│   │   ├── openlist_client.py     # OpenList 客户端
│   │   ├── subscription.py         # 订阅服务
│   │   ├── notification.py        # 通知服务
│   │   └── scheduler.py           # 调度服务
│   ├── sources/                   # 下载源插件
│   │   ├── __init__.py
│   │   ├── base.py                # MagnetSource Protocol
│   │   ├── registry.py            # SourceRegistry
│   │   ├── javbus_source.py       # JavBus 实现
│   │   ├── javdb_source.py        # JavDB 实现
│   │   └── javlib_source.py        # JavLib 实现
│   └── telegram/                  # Telegram Bot
│       ├── __init__.py
│       ├── bot.py                  # Bot 入口
│       ├── handlers/               # 命令处理器
│       │   ├── __init__.py
│       │   ├── search.py
│       │   ├── subscription.py
│       │   ├── status.py
│       │   └── help.py
│       └── keyboards.py            # InlineKeyboard 构建
├── frontend/
│   ├── src/
│   │   ├── api/                    # API 调用
│   │   │   ├── index.js
│   │   │   ├── videos.js
│   │   │   ├── subscriptions.js
│   │   │   ├── missing.js
│   │   │   └── duplicates.js
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── views/
│   │   │   ├── Home.vue            # 仪表盘
│   │   │   ├── Search.vue          # 搜索
│   │   │   ├── Subscription.vue     # 订阅管理
│   │   │   ├── Missing.vue         # 缺失演员看板
│   │   │   ├── MissingDetail.vue   # 缺失演员详情
│   │   │   ├── Duplicates.vue       # 去重管理
│   │   │   ├── Config.vue          # 配置
│   │   │   └── Logs.vue
│   │   └── components/
│   │       ├── VideoCard.vue
│   │       ├── VideoModal.vue
│   │       ├── ActressCard.vue
│   │       └── StatCard.vue
│   └── package.json
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-04-10-avdownloader-refactor-design.md
├── config.yaml
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 9. 实现优先级

### Phase 1: 核心架构
1. 模块 Protocol 定义
2. SourceRegistry 实现
3. JavInfoApi Client (Info Module)
4. 基础 API 路由搭建

### Phase 2: 主要功能
5. Emby Module (去重 + 缺失检测)
6. OpenList Module
7. 订阅 Module

### Phase 3: Telegram
8. Telegram Bot 重构
9. 通知推送

### Phase 4: 前端
10. 仪表盘增强
11. 搜索页面重构
12. 缺失演员看板 + 详情
13. 去重管理页面
14. 配置页面优化

### Phase 5: 完善
15. 下载源插件完善 (JavDB/JavLib)
16. 调度任务完善
17. 日志模块
