# JavHub

A self-hosted media library management tool with multi-source metadata aggregation, automated monitoring, and direct download integration.

![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js)

## Features

- **Multi-Provider Metadata** — Aggregates content from multiple public sources with automatic fallback
- **Performer Monitoring** — Subscribe to performers and receive alerts on new content
- **Direct Link Download** — Integrates with OpenList-compatible endpoints for offline downloads
- **Emby Library Sync** — Detects whether content already exists in your Emby library
- **Telegram Bot** — Search, subscribe, and manage downloads directly from chat
- **Real-time Notifications** — New content alerts, download completion, and system status
- **Web Dashboard** — Intuitive UI for all management operations

## Quick Start

### Docker

```bash
git clone https://github.com/Kongmei-ovo/JavHub.git
cd JavHub
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
docker-compose up -d
```

### Manual

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Configuration

Edit `config.yaml`:

```yaml
openlist:
  api_url: "https://your-openlist.com"
  username: "your-username"
  password: "your-password"
  default_path: "/115/AV"

emby:
  api_url: "http://your-emby:8096"
  api_key: "your-api-key"

telegram:
  bot_token: "123456:ABC-DEF..."
  allowed_user_ids: ["123456789"]

notification:
  enabled: true
  telegram: true

scheduler:
  subscription_check_hour: 2
```

## Web UI

Access at `http://localhost:3000` after startup.

| Page | Description |
|------|-------------|
| Dashboard | Download queue, system statistics |
| Search | Search by content ID or performer, select download |
| Subscriptions | Manage performer subscriptions, manual checks |
| Library Check | Verify if content exists in Emby |
| Logs | View system logs |
| Settings | Configure system parameters |

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/search ABC-123` | Search by content ID |
| `/sub add Name` | Add performer subscription |
| `/sub list` | List all subscriptions |
| `/sub del Name` | Remove subscription |
| `/check` | Manually trigger subscription check |
| `/status` | View download queue |

## API

```
GET  /api/v1/videos/search?q=xxx      # Search content
GET  /api/v1/videos/{id}              # Content detail
POST /api/downloads                    # Create download task
GET  /api/downloads                   # Download list
GET  /api/subscriptions               # Subscription list
POST /api/subscriptions               # Add subscription
GET  /api/library/check?code=xxx      # Emby library check
GET  /api/logs                        # System logs
GET  /api/config                       # Configuration
PUT  /api/config                       # Update configuration
```

## Project Structure

```
JavHub/
├── backend/              # FastAPI backend
│   ├── routers/          # API routes
│   ├── services/         # Business logic
│   └── telegram/         # Telegram bot
├── frontend/             # Vue 3 frontend
│   └── src/
│       ├── views/        # Page components
│       └── api/          # API client
└── docker-compose.yml
```

## Cloud Deployment

Push to GitHub and GitHub Actions will automatically build Docker images:

1. Fork this repository
2. Add to GitHub Secrets:
   - `DOCKER_USERNAME`
   - `DOCKER_TOKEN`
3. Push to trigger build

## Disclaimer

This project is for personal use and educational purposes only.

- This project does not host or distribute any content
- All metadata is sourced from publicly available APIs
- Users are solely responsible for their use of this tool
- This tool is not intended for commercial use

## License

MIT
