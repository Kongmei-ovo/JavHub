# AV Downloader 重构设计Spec

## 1. 概述与目标

### 1.1 项目背景
当前系统存在多数据源耦合、检索与下载职责不清的问题。需要重构为清晰的**检索-磁力分离**架构，支持多源磁力 fallback。

### 1.2 核心目标
- **检索引擎**：统一使用 `javjaeger`（封装 javbus-api）作为主数据源，提供搜索、分类、筛选
- **磁力服务**：多源架构（JavBus / JavDB / JavLib），支持 fallback
- **下载服务**：通过 OpenList 离线下载
- **前端重构**：现代化 UI，完整站点功能（搜索/分类/筛选/详情）

## 2. 架构设计

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue3)                      │
│  首页 | 搜索 | 分类 | 订阅 | 下载管理 | 设置                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ Search API  │  │ Magnet API  │  │ Download API    │    │
│  │ (javjaeger) │  │ (多源fallback)│  │ (OpenList)      │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Unified Movie Model                    │    │
│  │  code, title, actor, date, cover, genres, stars...   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ JavBus   │   │ JavDB    │   │ JavLib   │
        │ (检索+磁力)│   │ (磁力)    │   │ (磁力)    │
        └──────────┘   └──────────┘   └──────────┘
```

### 2.2 数据模型

```python
class Movie(BaseModel):
    # 基础信息（统一格式）
    code: str              # 番号，如 "STAR-696"
    title: str             # 标题
    actor: str              # 主演（逗号分隔）
    release_date: str       # 发布日期
    cover_url: str          # 封面图
    backdrop_url: str       # 背景图（详情页）
    genres: List[str]       # 类型/标签
    studio: str             # 制作商
    publisher: str          # 发行商
    duration: int           # 时长（分钟）

    # 磁力信息
    magnets: List[MagnetInfo]  # 磁力链接列表

    # 剧照/预览图
    samples: List[str]     # 剧照 URL 列表

    # 扩展信息
    rating: float           # 评分（可选）
    source: str             # 数据来源：javbus/javdb/javlib
    source_url: str         # 原始页面 URL

class MagnetInfo(BaseModel):
    title: str              # 磁力标题（如 "STAR-696 1080p")
    magnet: str             # 磁力链接
    size: str               # 文件大小
    resolution: str         # 分辨率：720p/1080p/4K
    hd: bool                # 是否 HD
    subtitle: bool          # 是否有字幕
```

### 2.3 核心服务

#### 2.3.1 搜索服务（SearchService）
- **入口**：统一搜索 API
- **实现**：基于 javjaeger 的 javbus-api 封装
- **功能**：
  - 关键字搜索（番号/演员/标题）
  - 分类筛选（类型/演员/导演/商贩/系列）
  - 排序（最新/评分/热度）
  - 分页

#### 2.3.2 磁力服务（MagnetService）
- **多源架构**：可配置多个磁力源
- **Fallback 机制**：某源失败自动切换下一源
- **源优先级**：可配置
- **实现**：
  - JavBus Magnet Source
  - JavDB Magnet Source（预留）
  - JavLib Magnet Source（预留）

#### 2.3.3 下载服务（DownloadService）
- **实现**：OpenList API
- **功能**：
  - 创建离线下载任务
  - 查询下载状态
  - 重试失败任务

## 3. API 设计

### 3.1 搜索 API

```
GET /api/movies
  Query: keyword, page, page_size, genre, actor, studio, series, sort_by, video_type
  Response: { movies: [], pagination: {}, total: int }

GET /api/movies/{movie_id}
  Response: Movie (完整信息，含磁力)

GET /api/movies/{movie_id}/magnets
  Response: { magnets: [] }

GET /api/genres
  Response: [{ id, name, count }]

GET /api/actors/search?keyword=xxx
  Response: [{ id, name, avatar, movie_count }]
```

### 3.2 下载 API

```
POST /api/downloads
  Body: { code, title, magnet, path }
  Response: { task_id, status }

GET /api/downloads
  Response: [{ id, code, title, magnet, path, status, created_at }]

DELETE /api/downloads/{task_id}
  Response: { success }
```

### 3.3 配置 API

```
GET /api/config
PUT /api/config
```

## 4. 前端设计

### 4.1 页面结构

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页/下载管理 | `/` | 下载队列、统计 |
| 搜索 | `/search` | 关键字搜索、筛选 |
| 分类 | `/genres` | 类型分类浏览 |
| 订阅 | `/subscription` | 演员订阅管理 |
| 设置 | `/config` | 系统配置 |

### 4.2 搜索页功能

- 搜索框（关键字/番号/演员）
- 筛选栏（类型、演员数量、日期范围）
- 排序选项（最新、评分、热度）
- 卡片网格展示（封面+番号+标题+演员）
- 详情弹窗（封面+剧照+磁力+下载）

### 4.3 详情页功能

- 大封面展示
- 电影信息（番号、标题、演员、日期、类型）
- 剧照画廊
- 磁力列表（分辨率/字幕/大小筛选）
- 一键下载

## 5. 数据流

### 5.1 搜索流程

```
用户输入关键字
    │
    ▼
调用 /api/movies?keyword=xxx
    │
    ▼
SearchService.search(keyword)
    │
    ▼
调用 javjaeger javbus-api 搜索
    │
    ▼
返回统一 Movie 模型列表
    │
    ▼
前端展示卡片
```

### 5.2 磁力获取流程

```
用户点击影片详情
    │
    ▼
调用 /api/movies/{movie_id} 获取基本信息
    │
    ▼
用户点击下载按钮
    │
    ▼
调用 MagnetService 获取磁力
    │
    ▼
多源 fallback：JavBus → JavDB → JavLib
    │
    ▼
返回磁力列表
    │
    ▼
用户选择磁力下载
    │
    ▼
调用 /api/downloads 创建任务
```

## 6. 实施计划

### Phase 1: 后端重构
1. 统一数据模型
2. 重构 MagnetService（多源架构）
3. 重构 SearchService（基于 javjaeger）
4. 更新 API 路由

### Phase 2: 前端重构
1. 重构项目结构
2. 实现搜索页面
3. 实现分类页面
4. 实现详情弹窗
5. 优化 UI/UX

### Phase 3: 功能完善
1. 订阅功能
2. 下载管理
3. 配置页面
4. 测试验证

## 7. 技术选型

- **后端**：Python 3.11+ / FastAPI / httpx / asyncio
- **前端**：Vue 3 / Vite / Axios / Vue Router
- **数据源**：javbus-api（javjaeger 封装）
- **下载**：OpenList API
- **缓存**：内存缓存（LRU）
