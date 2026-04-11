# AV Downloader

🎬 支持多源搜索、自动订阅、离线下载的 AV 影片管理工具

![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js)

## 功能特性

- 🔍 **多源搜索** - JavBus / JavLib / JavDB 自动 fallback
- 📺 **订阅管理** - 订阅演员，自动检测新片
- 📥 **离线下载** - OpenList + 115 网盘无缝集成
- 🎬 **Emby 库检测** - 自动判断影片是否已存在
- 💬 **Telegram Bot** - 快捷搜索、下载指令
- 📬 **通知推送** - 新片发现、下载完成实时通知
- 🌐 **Web 管理后台** - 直观的 UI 操作界面

## 快速部署

### 方式一：使用 Docker

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/avdownloader.git
cd avdownloader

# 配置
cp config.yaml.example config.yaml
# 编辑 config.yaml 填入你的配置

# 启动
docker-compose up -d
```

### 方式二：手动部署

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端 (新终端)
cd frontend
npm install
npm run dev
```

## 配置说明

编辑 `config.yaml`:

```yaml
openlist:
  api_url: "https://your-openlist.com"  # OpenList 地址
  username: "your-username"
  password: "your-password"
  default_path: "/115/AV"               # 默认下载路径

emby:
  api_url: "http://your-emby:8096"     # Emby 地址
  api_key: "your-api-key"              # Emby API Key

telegram:
  bot_token: "123456:ABC-DEF..."       # Telegram Bot Token
  allowed_user_ids: ["123456789"]       # 授权用户 ID

notification:
  enabled: true
  telegram: true

scheduler:
  subscription_check_hour: 2           # 每日检查时间（凌晨2点）
```

## Web 界面

启动后访问 `http://localhost:3000`

| 页面 | 功能 |
|------|------|
| 首页 | 下载队列状态、统计数据 |
| 搜索 | 番号/演员搜索，选择磁力下载 |
| 订阅 | 管理演员订阅，手动检查更新 |
| 库检测 | 检查影片是否已在 Emby 库中 |
| 日志 | 查看系统运行日志 |
| 配置 | 修改系统配置 |

## Telegram Bot 命令

| 命令 | 说明 |
|------|------|
| `/search ABC-123` | 搜索影片 |
| `/sub add 演员名` | 添加订阅 |
| `/sub list` | 查看订阅列表 |
| `/sub del 演员名` | 删除订阅 |
| `/check` | 手动检查订阅更新 |
| `/status` | 查看下载队列 |

## API 接口

```
GET  /api/search?keyword=xxx     # 搜索影片
POST /api/download                # 创建下载任务
GET  /api/downloads               # 下载列表
GET  /api/subscriptions           # 订阅列表
POST /api/subscription           # 添加订阅
GET  /api/library/check?code=xxx  # 库检测
GET  /api/logs                   # 日志
GET  /api/config                 # 配置
PUT  /api/config                  # 更新配置
```

## 开发

### 项目结构

```
avdownloader/
├── backend/              # FastAPI 后端
│   ├── routers/          # API 路由
│   ├── services/         # 业务逻辑
│   └── telegram/         # Telegram Bot
├── frontend/             # Vue 3 前端
│   └── src/
│       ├── views/        # 页面组件
│       └── api/          # API 调用
└── docker-compose.yml
```

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## 部署到云端

推送到 GitHub 后，使用 GitHub Actions 自动构建 Docker 镜像：

1. Fork 本项目
2. 在 GitHub Secrets 添加配置：
   - `DOCKER_USERNAME`
   - `DOCKER_TOKEN`
3. Push 代码触发构建

## License

MIT
