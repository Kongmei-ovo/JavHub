# JavHub

JavHub is a self-hosted personal catalog dashboard. It combines a Vue web UI, a
FastAPI backend, a companion data API, background tasks, external service
connectors, and optional notifications.

![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js)

## What Is Included

- Query and detail views backed by the companion API
- Saved watches and scheduled refresh tasks
- Optional integrations with user-managed external services
- A unified JavInfo catalog where movies exist independently of downloaded files
- ItemId-bound 115 Open and online playback resources, resume, and continue watching
- An optional movie-focused Emby compatibility API for Emby, Infuse, VidHub, and SenPlayer (see [docs/emby-compat.md](docs/emby-compat.md))
- Web dashboard for search, imports, logs, and settings
- Optional chat-based commands and notifications
- One Docker image for the frontend and backend

## Docker Images

| Image | Purpose |
|-------|---------|
| `ghcr.io/kongmei-ovo/javhub:<tag>` | JavHub frontend, Nginx, and FastAPI backend |
| `ghcr.io/kongmei-ovo/javinfoapi:<tag>` | Companion data API |

Default moving release tags:

```bash
ghcr.io/kongmei-ovo/javhub:stable
ghcr.io/kongmei-ovo/javinfoapi:stable
```

Every push to `main` publishes `stable` plus an immutable automatic beta tag
such as `v1.2.0-beta.<github-run-number>`. Use `stable` for normal upgrades and
pin one of the generated beta tags when you need a fixed rollback target.

JavHub is intentionally published as a single image. The container builds the
Vue frontend, serves it with Nginx, and proxies `/api` plus `/health` to the
FastAPI backend running inside the same container.

## Docker Compose Deployment

`docker-compose.yml` is the recommended single-machine deployment example. It
starts:

- PostgreSQL for JavInfoApi metadata and JavHub state
- Redis for JavHub response/cache data
- JavInfoApi
- JavHub, exposed as the web entrypoint

```bash
git clone https://github.com/Kongmei-ovo/JavHub.git
cd JavHub
cp config.yaml.example config.yaml
```

Edit `config.yaml` before starting the stack. For the bundled compose network,
the JavHub state database and JavInfo import database should point at the
compose service names. Keep them as separate database names:

```yaml
database:
  host: "postgres"
  port: 5432
  database: "javhub"
  maintenance_database: "postgres"
  user: "javhub"
  password: "change-me"

javinfo:
  api_url: "http://javinfoapi:18080"
  page_size: 30
  supplement_admin_token: "change-me"
  import_db:
    host: "postgres"
    port: 5432
    database: "r18"
    maintenance_database: "postgres"
    user: "javhub"
    password: "change-me"
```

Create a local `.env` file if you want to override image tags or change passwords:

```bash
JAVHUB_IMAGE=ghcr.io/kongmei-ovo/javhub:stable
JAVINFOAPI_IMAGE=ghcr.io/kongmei-ovo/javinfoapi:stable
JAVHUB_PORT=3000
JAVINFOAPI_PORT=18080

POSTGRES_DB=r18
POSTGRES_USER=javhub
POSTGRES_PASSWORD=change-me
JAVHUB_DB_NAME=javhub

DB_HOST=postgres
DB_PORT=5432
DB_USER=javhub
DB_PASSWORD=change-me
DB_NAME=r18
JAVHUB_DB_HOST=postgres
JAVHUB_DB_PORT=5432
JAVHUB_DB_USER=javhub
JAVHUB_DB_PASSWORD=change-me
SUPPLEMENT_ADMIN_TOKEN=change-me
CORS_ALLOW_ORIGINS=http://localhost:3000
```

Validate and start:

```bash
docker compose config
docker compose pull
docker compose up -d
docker compose ps
```

After the stack is healthy, open the JavHub UI and import the base database
dump from the JavInfo import screen. Uploads are chunked and resumable from the
server-recorded byte offset. When the import finishes, JavHub automatically
asks JavInfoApi to apply its auxiliary tables and indexes. There is no separate
migration container or manual migrate step in the normal compose deployment
path.

Open JavHub at `http://localhost:3000`.

Health checks:

```bash
curl -fsS http://localhost:3000/health
curl -fsS http://localhost:18080/health
```

### Public Web Testing With Cloudflare Access

For public testing without adding application-level users yet, put Cloudflare
Access and Cloudflare Tunnel in front of JavHub. The optional
`docker-compose.cloudflare.yml` override adds a `cloudflared` container that
routes the private compose service `http://javhub:80` to a Cloudflare-protected
hostname.

See [docs/cloudflare-access-tunnel.md](docs/cloudflare-access-tunnel.md) for
the setup steps and public exposure checklist.

### PostgreSQL Notes

PostgreSQL is included by default for two separate data domains: JavInfoApi and
JavHub's import workflow use `r18`, while JavHub runtime state uses `javhub`.

If you already have PostgreSQL, you may comment out the `postgres` service and
the `depends_on: postgres` blocks. You must create both database names before
startup:

```bash
createdb -h <db-host> -U <db-user> r18
createdb -h <db-host> -U <db-user> javhub
```

Then update both places:

- `.env`: `DB_*` for JavInfoApi/import, `JAVHUB_DB_*` for JavHub state
- `config.yaml`: `database.*` for JavHub state, `javinfo.import_db.*` for JavInfo imports

Keep the JavInfoApi `DB_NAME` and JavHub `javinfo.import_db.database` values the
same unless you deliberately manage separate metadata databases. Do not point
JavHub `database.database` at the JavInfo import database, because imports can
replace that database.

### Persistent Data

| Path or volume | Purpose |
|----------------|---------|
| `./config.yaml` | Runtime configuration mounted into the container |
| `./data` | Runtime files and logs |
| `javinfo-postgres` | PostgreSQL data volume for `r18` and `javhub` |
| `javhub-redis` | Redis cache data volume |

Secrets, runtime data, logs, `config.yaml`, and database files are not baked
into the Docker image.

### Updating

For a source checkout deployment:

```bash
git pull
docker compose pull
docker compose up -d
```

For pinned releases, update `JAVHUB_IMAGE` and `JAVINFOAPI_IMAGE` in `.env`,
then run:

```bash
docker compose pull
docker compose up -d
```

Avoid relying on `latest` for self-hosted deployments. The compose defaults use
`stable`, which is updated by CI on every successful `main` build. For stricter
rollback and upgrade checks, pin a generated beta tag such as
`v1.2.0-beta.<github-run-number>`. `docker compose up -d` will not pull a
changed tag unless you run `docker compose pull` first.

## Local Development

On macOS, use the project helper instead of starting ad hoc background
processes:

```bash
scripts/services.sh ensure
scripts/services.sh status
scripts/services.sh restart backend
scripts/services.sh logs backend
```

The helper manages LaunchAgents:

| Service | Default URL | Notes |
|---------|-------------|-------|
| JavHub frontend | `http://localhost:5174` | Vite dev server |
| JavHub backend | `http://localhost:18090` | FastAPI API server |
| JavInfoApi | `http://localhost:8080` | Helper-managed companion API |

Direct manual startup is also possible:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 18090
```

```bash
cd frontend
npm ci
npm run dev
```

JavInfoApi's own default port is `18080` when run directly from that repository.

## Main Configuration

Most settings live in `config.yaml`.

```yaml
server:
  frontend_origin: "http://localhost:5174"

open115:
  app_id: ""
  root_path: "/JavHub"
  # Bind the account in Settings. Access and refresh tokens are managed by
  # the dedicated API and are never returned by normal configuration APIs.

emby_compat:
  enabled: false
  username: "javhub"
  password: "change-me"

javinfo:
  api_url: "http://localhost:18080"
  supplement_admin_token: ""
  import_db:
    host: "postgres"
    port: 5432
    database: "r18"
    maintenance_database: "postgres"
    user: "javhub"
    password: "change-me"

telegram:
  bot_token: ""
  allowed_user_ids: []
```

Container deployments mount `./config.yaml` at `/app/config.yaml` and set
`JAVHUB_CONFIG_PATH=/app/config.yaml`, so the settings page reflects the file
you edited. JavHub state reads `JAVHUB_DB_HOST`, `JAVHUB_DB_PORT`,
`JAVHUB_DB_USER`, `JAVHUB_DB_PASSWORD`, and `JAVHUB_DB_NAME`. JavInfo import
settings still read `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and
`DB_NAME`.

## Useful Commands

```bash
# Build the unified JavHub image locally
docker build -t javhub:test .

# Validate the compose file
docker compose config

# Run backend tests
python -m pytest -q

# Smoke test the cache backend
PYTHONPATH=backend python scripts/cache_backend_smoke.py

# Run a short read-only API load-test smoke
node scripts/api_load_test.mjs --base http://localhost:18090 --duration-scale 0.01

# Smoke test Redis cache mode when Redis is available
JAVHUB_CACHE_BACKEND=redis \
JAVHUB_REDIS_URL=redis://localhost:6379/0 \
JAVHUB_REDIS_PREFIX=javhub-cache-smoke \
PYTHONPATH=backend python scripts/cache_backend_smoke.py

# Build frontend assets
cd frontend && npm ci && npm run build
```

## GitHub Actions

The repository includes four workflows:

- `CI`: backend tests and frontend build
- `CodeQL`: strict Python and JavaScript/TypeScript analysis
- `Build Docker Image`: builds the unified JavHub image
- `Docker Smoke`: validates the compose stack and service health

Docker images are pushed to GHCR on `main`, `v*` tags, and manual workflow
dispatch. Pull requests build for validation but do not push images.

## Project Structure

```text
JavHub/
├── backend/              # FastAPI backend
├── frontend/             # Vue 3 frontend
├── scripts/              # service helpers and container entrypoint
├── Dockerfile            # unified frontend + backend image
├── docker-compose.yml    # single-machine deployment example
├── docker-compose.cloudflare.yml # Cloudflare Tunnel deployment override
├── nginx.conf            # static serving and /api proxy
└── config.yaml.example
```

## Disclaimer

This project is for personal use and educational purposes only.

- This project does not host or distribute third-party content.
- Data is read from public or user-configured sources.
- Users are responsible for complying with local laws and service terms.
- This tool is not intended for commercial use.

## License

MIT
