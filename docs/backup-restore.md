# Backup and Restore

This guide covers the files and volumes that make a JavHub instance recoverable
for both local development and Docker Compose deployments.

## What to Back Up

Back up these items before upgrades, host moves, or destructive maintenance:

- `config.yaml`: runtime settings and secrets. In Compose this is mounted at
  `/app/config.yaml` through `JAVHUB_CONFIG_PATH=/app/config.yaml`.
- `data/`: JavHub's local runtime directory. It includes the main SQLite
  database at `data/avdownloader.db`, SQLite WAL/SHM sidecar files when present,
  logs, import job state, and other local runtime files.
- `javinfo-postgres`: the Compose PostgreSQL volume used by JavInfoApi and the
  JavHub import workflow. The default database is `r18`.
- `javhub-redis`: the Compose Redis volume. Redis is used as a cache in the
  default Compose deployment. It is useful for warm cache recovery but is not a
  primary source of truth.
- `.env`: optional Compose overrides such as image tags, port mappings,
  database credentials, and shared tokens.

## Local Backup

Stop local services or make sure no write-heavy jobs are running before copying
SQLite files. The project helper keeps the LaunchAgent-managed services in a
known state:

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
```

Restart services and verify health:

```bash
scripts/services.sh ensure
scripts/services.sh status
curl -fsS http://127.0.0.1:18090/health
```

## Docker Compose Backup

From the repository root, capture configuration, local data, PostgreSQL, and
Redis:

```bash
stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "backups/${stamp}"

cp config.yaml "backups/${stamp}/config.yaml"
test -f .env && cp .env "backups/${stamp}/.env"
tar -czf "backups/${stamp}/javhub-data.tgz" data

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${POSTGRES_DB:-r18}" \
  --format=custom \
  --file=/tmp/javinfo-postgres.dump
docker compose cp postgres:/tmp/javinfo-postgres.dump \
  "backups/${stamp}/javinfo-postgres.dump"
docker compose exec -T postgres rm -f /tmp/javinfo-postgres.dump

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
local instance, restore the split files instead:

```bash
scripts/services.sh stop

tar -xzf backups/<stamp>/javhub-data.tgz
cp backups/<stamp>/config.yaml config.yaml
test -f backups/<stamp>/.env && cp backups/<stamp>/.env .env

scripts/services.sh ensure
```

## Restore a Docker Compose Instance

Stop the stack and restore `config.yaml`, `.env`, and `data/`:

```bash
docker compose down

cp backups/<stamp>/config.yaml config.yaml
test -f backups/<stamp>/.env && cp backups/<stamp>/.env .env
rm -rf data
tar -xzf backups/<stamp>/javhub-data.tgz
```

Start PostgreSQL first, then restore its data:

```bash
docker compose up -d postgres

docker compose cp backups/<stamp>/javinfo-postgres.dump \
  postgres:/tmp/javinfo-postgres.dump
docker compose exec -T postgres pg_restore \
  -U "${POSTGRES_USER:-javhub}" \
  -d "${POSTGRES_DB:-r18}" \
  --clean \
  --if-exists \
  /tmp/javinfo-postgres.dump
docker compose exec -T postgres rm -f /tmp/javinfo-postgres.dump
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
PostgreSQL database used by JavInfoApi. Before taking a backup, avoid starting a
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
Use `/health/readiness` when you also want configuration, SQLite, JavInfo, and
cache status details:

```bash
curl -fsS http://127.0.0.1:3000/health/readiness
curl -fsS http://127.0.0.1:18090/health/readiness
```
