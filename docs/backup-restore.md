# Backup and Restore

This guide covers the files and volumes that make a JavHub instance recoverable
for both local development and Docker Compose deployments.

## What to Back Up

Back up these items before upgrades, host moves, or destructive maintenance:

- `config/config.yaml`: runtime settings and secrets. In Compose this is
  mounted at `/config/config.yaml` through
  `JAVHUB_CONFIG_PATH=/config/config.yaml`.
- `data/`: JavHub's local runtime directory. It includes logs, import job state,
  legacy SQLite backup files if you still have them, and other local runtime
  files. JavHub runtime state is no longer read from SQLite.
- PostgreSQL databases:
  - `r18`: JavInfoApi metadata and the JavHub JavInfo import target.
  - `javhub`: JavHub state such as subscriptions, favorites, downloads,
    translations, inventory, logs, and local workflow history.
- `javinfo-postgres`: the Compose PostgreSQL volume containing both `r18` and
  `javhub` in the default deployment.
- `javhub-redis`: the Compose Redis volume. Redis is used as a cache in the
  default Compose deployment. It is useful for warm cache recovery but is not a
  primary source of truth.
- `.env`: optional Compose overrides such as image tags, port mappings,
  database credentials, and shared tokens.

## Local Backup

Stop local services or make sure no write-heavy jobs are running before copying
runtime files and dumping PostgreSQL. The project helper keeps the
LaunchAgent-managed services in a known state:

```bash
scripts/services.sh status
scripts/services.sh stop
```

Create a timestamped archive from the repository root:

```bash
stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "backups/${stamp}"
tar -czf "backups/${stamp}/javhub-local.tgz" \
  config.yaml \
  data
test -f .env && cp .env "backups/${stamp}/.env"

pg_dump -h "${DB_HOST:-localhost}" \
  -p "${DB_PORT:-5432}" \
  -U "${DB_USER:-kongmei}" \
  -d "${DB_NAME:-r18}" \
  --format=custom \
  --file="backups/${stamp}/javinfo-r18.dump"

pg_dump -h "${JAVHUB_DB_HOST:-localhost}" \
  -p "${JAVHUB_DB_PORT:-5432}" \
  -U "${JAVHUB_DB_USER:-kongmei}" \
  -d "${JAVHUB_DB_NAME:-javhub}" \
  --format=custom \
  --file="backups/${stamp}/javhub-state.dump"
```

Restart services and verify health:

```bash
scripts/services.sh ensure
scripts/services.sh status
curl -fsS http://127.0.0.1:18090/health
```

## Docker Compose Backup

From the repository root, capture configuration, local runtime files,
PostgreSQL, and Redis:

```bash
stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "backups/${stamp}"

mkdir -p "backups/${stamp}/config"
cp config/config.yaml "backups/${stamp}/config/config.yaml"
test -f .env && cp .env "backups/${stamp}/.env"
tar -czf "backups/${stamp}/javhub-data.tgz" data

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${POSTGRES_DB:-r18}" \
  --format=custom \
  --file=/tmp/javinfo-r18.dump
docker compose cp postgres:/tmp/javinfo-r18.dump \
  "backups/${stamp}/javinfo-r18.dump"
docker compose exec -T postgres rm -f /tmp/javinfo-r18.dump

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${JAVHUB_DB_NAME:-javhub}" \
  --format=custom \
  --file=/tmp/javhub-state.dump
docker compose cp postgres:/tmp/javhub-state.dump \
  "backups/${stamp}/javhub-state.dump"
docker compose exec -T postgres rm -f /tmp/javhub-state.dump

docker compose exec -T redis redis-cli BGSAVE
docker compose cp redis:/data/dump.rdb "backups/${stamp}/redis-dump.rdb"
```

If the stack is already stopped, archive Docker volumes directly instead:

```bash
docker run --rm \
  -v javhub_javinfo-postgres:/volume:ro \
  -v "$PWD/backups/${stamp}:/backup" \
  alpine tar -czf /backup/javinfo-postgres-volume.tgz -C /volume .

docker run --rm \
  -v javhub_javhub-redis:/volume:ro \
  -v "$PWD/backups/${stamp}:/backup" \
  alpine tar -czf /backup/javhub-redis-volume.tgz -C /volume .
```

Check the actual volume names with `docker volume ls` if the Compose project
name is not `javhub`.

## Restore a Local Instance

Stop services, restore the local archive created by **Local Backup**, then
start again:

```bash
scripts/services.sh stop

tar -xzf backups/<stamp>/javhub-local.tgz
test -f backups/<stamp>/.env && cp backups/<stamp>/.env .env

scripts/services.sh ensure
```

If you are restoring the `javhub-data.tgz` archive from a Compose backup into a
local instance, restore the split files instead. Then restore the two
PostgreSQL dumps:

```bash
scripts/services.sh stop

tar -xzf backups/<stamp>/javhub-data.tgz
cp backups/<stamp>/config/config.yaml config.yaml
test -f backups/<stamp>/.env && cp backups/<stamp>/.env .env

pg_restore -h "${DB_HOST:-localhost}" \
  -p "${DB_PORT:-5432}" \
  -U "${DB_USER:-kongmei}" \
  -d "${DB_NAME:-r18}" \
  --clean \
  --if-exists \
  backups/<stamp>/javinfo-r18.dump

pg_restore -h "${JAVHUB_DB_HOST:-localhost}" \
  -p "${JAVHUB_DB_PORT:-5432}" \
  -U "${JAVHUB_DB_USER:-kongmei}" \
  -d "${JAVHUB_DB_NAME:-javhub}" \
  --clean \
  --if-exists \
  backups/<stamp>/javhub-state.dump

scripts/services.sh ensure
```

## Restore a Docker Compose Instance

Stop the stack and restore `config/config.yaml`, `.env`, and `data/`:

```bash
docker compose down

mkdir -p config
cp backups/<stamp>/config/config.yaml config/config.yaml
test -f backups/<stamp>/.env && cp backups/<stamp>/.env .env
rm -rf data
tar -xzf backups/<stamp>/javhub-data.tgz
```

Start PostgreSQL first, then restore its data:

```bash
docker compose up -d postgres

docker compose cp backups/<stamp>/javinfo-r18.dump \
  postgres:/tmp/javinfo-r18.dump
docker compose exec -T postgres pg_restore \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${POSTGRES_DB:-r18}" \
  --clean \
  --if-exists \
  /tmp/javinfo-r18.dump
docker compose exec -T postgres rm -f /tmp/javinfo-r18.dump

docker compose cp backups/<stamp>/javhub-state.dump \
  postgres:/tmp/javhub-state.dump
docker compose exec -T postgres pg_restore \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${JAVHUB_DB_NAME:-javhub}" \
  --clean \
  --if-exists \
  /tmp/javhub-state.dump
docker compose exec -T postgres rm -f /tmp/javhub-state.dump
```

Redis is a cache, so the safest restore path is usually to let it start empty.
If you need to restore the saved Redis snapshot, keep the stack stopped and load
it into a fresh Redis volume:

```bash
docker compose down
docker volume rm javhub_javhub-redis
docker volume create javhub_javhub-redis
docker run --rm \
  -v javhub_javhub-redis:/data \
  -v "$PWD/backups/<stamp>:/backup:ro" \
  alpine cp /backup/redis-dump.rdb /data/dump.rdb
```

Bring the full stack back:

```bash
docker compose up -d
docker compose ps
```

For raw volume archives, keep the stack stopped and unpack into fresh volumes:

```bash
docker compose down --volumes
docker volume create javhub_javinfo-postgres
docker volume create javhub_javhub-redis

docker run --rm \
  -v javhub_javinfo-postgres:/volume \
  -v "$PWD/backups/<stamp>:/backup:ro" \
  alpine sh -c 'tar -xzf /backup/javinfo-postgres-volume.tgz -C /volume'

docker run --rm \
  -v javhub_javhub-redis:/volume \
  -v "$PWD/backups/<stamp>:/backup:ro" \
  alpine sh -c 'tar -xzf /backup/javhub-redis-volume.tgz -C /volume'

docker compose up -d
```

## Import Jobs and Health Checks

JavInfo database imports are coordinated by JavHub and write into the same
PostgreSQL database used by JavInfoApi, usually `r18`. JavHub runtime state is
kept in a separate PostgreSQL database, usually `javhub`, so replacing `r18`
during an import does not replace subscriptions, favorites, download candidates,
translation jobs, inventory, or logs. Before taking a backup, avoid starting a
new import and let active imports finish or cancel them from the UI. After a
restore, check the import page for interrupted jobs before uploading a new dump.

Use these commands to validate the restored instance:

```bash
docker compose config
docker compose ps
curl -fsS http://127.0.0.1:3000/health
curl -fsS http://127.0.0.1:3000/api/v1/cache/stats
curl -fsS http://127.0.0.1:18080/health
docker compose exec -T postgres pg_isready \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${POSTGRES_DB:-r18}"
docker compose exec -T postgres pg_isready \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${JAVHUB_DB_NAME:-javhub}"
docker compose exec -T redis redis-cli ping
```

For local LaunchAgent services:

```bash
scripts/services.sh status
curl -fsS http://127.0.0.1:18090/health
curl -fsS http://127.0.0.1:18090/api/v1/cache/stats
curl -fsS http://127.0.0.1:8080/health
```

The JavHub `/health` endpoint confirms the web/backend process is responding.
Use `/health/readiness` when you also want configuration, PostgreSQL, JavInfo,
Redis/cache, and scheduler status details:

```bash
curl -fsS http://127.0.0.1:3000/health/readiness
curl -fsS http://127.0.0.1:18090/health/readiness
```
