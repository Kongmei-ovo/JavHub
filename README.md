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

The compose file includes PostgreSQL, JavInfoApi, and one JavHub container that
serves both the Vue frontend and the FastAPI backend. PostgreSQL defaults to
database name `r18`. If you already have a PostgreSQL instance, comment out the
`postgres` service and the corresponding `depends_on` entries, then create a
database with the same name (`r18` by default) in your external PostgreSQL
before starting the stack.

Published images:

| Image | Purpose |
|-------|---------|
| `ghcr.io/kongmei-ovo/javhub:<tag>` | JavHub frontend and backend |
| `ghcr.io/kongmei-ovo/javinfoapi:<tag>` | JavInfoApi metadata API |

For container deployment, make sure `config.yaml` points JavHub import settings
at the same PostgreSQL database used by JavInfoApi:

```yaml
javinfo:
  api_url: "http://javinfoapi:18080"
  import_db:
    host: "postgres"
    port: 5432
    database: "r18"
    maintenance_database: "postgres"
    user: "javhub"
    password: "change-me"
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

Local development uses three ports by default:

| Service | URL | Purpose |
|---------|-----|---------|
| JavHub frontend | `http://localhost:5173` | Browser entrypoint |
| JavHub backend | `http://localhost:18090` | Frontend `/api` proxy target |
| JavInfoApi | `http://localhost:18080` | Metadata API called by JavHub backend |

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

javinfo:
  api_url: "http://localhost:18080"
  page_size: 30
  supplement_admin_token: ""

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

Push to GitHub and GitHub Actions will automatically build GHCR Docker images:

1. Enable package publishing for GitHub Actions if your fork requires it.
2. Push to `main`, push a `v*` tag, or manually run the Docker workflow.
3. Pull the images from GHCR using the lowercase image names above.

Pull requests build images for validation but do not push them.

## Disclaimer

This project is for personal use and educational purposes only.

- This project does not host or distribute any content
- All metadata is sourced from publicly available APIs
- Users are solely responsible for their use of this tool
- This tool is not intended for commercial use

## License

MIT
