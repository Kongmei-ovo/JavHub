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
- Local library status checks
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

- PostgreSQL for JavInfoApi and JavHub import features
- JavInfoApi
- JavHub, exposed as the web entrypoint

```bash
git clone https://github.com/Kongmei-ovo/JavHub.git
cd JavHub
cp config.yaml.example config.yaml
```

Edit `config.yaml` before starting the stack. For the bundled compose network,
the JavInfo section should point at the compose service names:

```yaml
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

DB_HOST=postgres
DB_PORT=5432
DB_USER=javhub
DB_PASSWORD=change-me
DB_NAME=r18
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

### PostgreSQL Notes

PostgreSQL is included by default because the companion API needs it, and
JavHub's import workflow writes to the same database. The default database name
is `r18`.

If you already have PostgreSQL, you may comment out the `postgres` service and
the `depends_on: postgres` blocks. You must create the same database name before
startup:

```bash
createdb -h <db-host> -U <db-user> r18
```

Then update both places:

- `.env`: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `config.yaml`: `javinfo.import_db.host`, `user`, `password`, `database`

Keep the JavInfoApi `DB_NAME` and JavHub `javinfo.import_db.database` values the
same unless you deliberately manage separate databases.

### Persistent Data

| Path or volume | Purpose |
|----------------|---------|
| `./config.yaml` | Runtime configuration mounted into the container |
| `./data` | JavHub local SQLite data, runtime files, and logs |
| `javinfo-postgres` | PostgreSQL data volume |

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

openlist:
  api_url: "https://your-openlist.example"
  username: ""
  password: ""
  default_path: "/115/AV"

emby:
  api_url: "http://your-emby:8096"
  api_key: ""

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

Container deployments can override the companion API URL with
`JAVINFO_API_URL=http://javinfoapi:18080`. The JavInfo import settings also
read `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`, so compose
deployments can inherit the same database values used by JavInfoApi.

## Useful Commands

```bash
# Build the unified JavHub image locally
docker build -t javhub:test .

# Validate the compose file
docker compose config

# Run backend tests
PYTHONPATH=backend pytest

# Build frontend assets
cd frontend && npm ci && npm run build
```

## GitHub Actions

The repository includes three workflows:

- `CI`: backend tests and frontend build
- `CodeQL`: strict Python and JavaScript/TypeScript analysis
- `Build Docker Image`: builds the unified JavHub image

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
