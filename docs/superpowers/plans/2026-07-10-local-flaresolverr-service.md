# Local FlareSolverr Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the macOS local service helper start and manage an ARM64-compatible FlareSolverr container without changing cloud Docker Compose deployment.

**Architecture:** A new focused shell helper owns Colima/Docker lifecycle, configuration gating, container identity, and health checks. The existing `services.sh` delegates FlareSolverr commands to that helper while retaining LaunchAgent ownership of JavInfoApi, backend, and frontend.

**Tech Stack:** Bash, Docker CLI, Colima, FlareSolverr HTTP API, pytest subprocess tests, macOS LaunchAgents

## Global Constraints

- Work directly on `main`; do not create a feature branch.
- Do not modify `docker-compose.yml`, `docker-compose.cloudflare.yml`, `Dockerfile`, or container entrypoints.
- Only auto-manage FlareSolverr for localhost port 8191 unless `JAVHUB_LOCAL_FLARESOLVERR` explicitly overrides the decision.
- Never stop Colima during service shutdown.
- Never delete a same-name container unless it carries the JavHub local-management label.
- Publish only `127.0.0.1:8191:8191`.
- Push `main` only after tests and a real FlareSolverr smoke check pass.

---

## File Structure

- Create `scripts/local-flaresolverr.sh`: configuration decision, Docker/Colima lifecycle, health, status, and logs.
- Create `tests/test_local_flaresolverr.py`: cross-platform subprocess tests using Docker/Colima/curl stubs.
- Modify `scripts/services.sh`: command routing and lifecycle delegation only.
- Modify `tests/test_services.py`: macOS service-helper delegation contract tests.
- Modify `README.md`: document automatic local FlareSolverr and its opt-out/image variables.

### Task 1: Standalone local FlareSolverr helper

**Files:**
- Create: `tests/test_local_flaresolverr.py`
- Create: `scripts/local-flaresolverr.sh`

**Interfaces:**
- Consumes: `JAVHUB_CONFIG_PATH`, `JAVHUB_LOCAL_FLARESOLVERR`, `JAVHUB_FLARESOLVERR_IMAGE`, `FLARESOLVERR_LOG_LEVEL`, and `TZ`.
- Produces: commands `ensure`, `restart`, `stop`, `status`, `logs [--no-follow]`, and `doctor`.

- [ ] **Step 1: Write failing configuration and lifecycle tests**

Create tests that run the helper with temporary executable stubs:

```python
def run_helper(tmp_path, command, *, config, extra_env=None):
    env = {
        "HOME": str(tmp_path / "home"),
        "JAVHUB_CONFIG_PATH": str(config),
        "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
        **(extra_env or {}),
    }
    return subprocess.run(
        ["bash", "scripts/local-flaresolverr.sh", *command],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

def test_remote_solver_config_skips_docker(tmp_path):
    # config contains https://solver.example/v1
    # docker stub records every call
    result = run_helper(tmp_path, ["ensure"], config=config)
    assert result.returncode == 0
    assert "skipped" in result.stdout
    assert not docker_log.exists()

def test_ensure_starts_colima_then_creates_local_container(tmp_path):
    # docker info fails until the colima stub creates a daemon-ready marker.
    # docker inspect reports no container; docker run records its exact args.
    result = run_helper(tmp_path, ["ensure"], config=config)
    assert result.returncode == 0
    assert "colima start" in colima_log.read_text()
    run_call = docker_log.read_text()
    assert "run -d --name javhub-flaresolverr-local" in run_call
    assert "127.0.0.1:8191:8191" in run_call
    assert "com.kongmei.javhub.local-flaresolverr=true" in run_call

def test_stop_refuses_unowned_same_name_container(tmp_path):
    # inspect returns a container whose management label is empty.
    result = run_helper(tmp_path, ["stop"], config=config)
    assert result.returncode == 1
    assert "not managed by JavHub" in result.stderr
    assert "rm -f" not in docker_log.read_text()

def test_explicit_disable_skips_local_config(tmp_path):
    result = run_helper(
        tmp_path,
        ["ensure"],
        config=config,
        extra_env={"JAVHUB_LOCAL_FLARESOLVERR": "0"},
    )
    assert result.returncode == 0
    assert not docker_log.exists()
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_local_flaresolverr.py -v`

Expected: FAIL because `scripts/local-flaresolverr.sh` does not exist.

- [ ] **Step 3: Implement configuration gating and safe Docker lifecycle**

Implement the helper with these exact constants and decisions:

```bash
CONTAINER_NAME="${JAVHUB_FLARESOLVERR_CONTAINER:-javhub-flaresolverr-local}"
IMAGE="${JAVHUB_FLARESOLVERR_IMAGE:-ghcr.io/flaresolverr/flaresolverr:latest}"
MANAGED_LABEL="com.kongmei.javhub.local-flaresolverr=true"
HEALTH_URL="http://127.0.0.1:8191/"
```

Use a Python/YAML read restricted to `stream.cf_solver_url`; recognize only `localhost:8191` and `127.0.0.1:8191` in automatic mode. `ensure_docker_daemon` must call `docker info`, then `colima start` only on Darwin when Colima exists. Before `docker rm -f`, require `docker inspect --format '{{ index .Config.Labels "com.kongmei.javhub.local-flaresolverr" }}'` to equal `true`.

Create the container with:

```bash
docker run -d \
  --name "${CONTAINER_NAME}" \
  --label "${MANAGED_LABEL}" \
  --restart unless-stopped \
  -p "127.0.0.1:8191:8191" \
  -e "LOG_LEVEL=${FLARESOLVERR_LOG_LEVEL:-info}" \
  -e "TZ=${TZ:-Asia/Shanghai}" \
  "${IMAGE}"
```

Poll the health URL with bounded attempts. `stop` removes only the owned container. `status` reports skip, daemon, container, and health states. `logs --no-follow` uses `docker logs --tail 120`; default logs additionally use `--follow`.

- [ ] **Step 4: Run helper tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_local_flaresolverr.py -v`

Expected: all helper tests pass.

- [ ] **Step 5: Commit the standalone helper**

```bash
git add scripts/local-flaresolverr.sh tests/test_local_flaresolverr.py
git commit -m "feat(dev): manage local flaresolverr container"
```

### Task 2: Integrate services.sh commands

**Files:**
- Modify: `tests/test_services.py`
- Modify: `scripts/services.sh`

**Interfaces:**
- Consumes: `LOCAL_FLARESOLVERR_HELPER` path, defaulting to `scripts/local-flaresolverr.sh`.
- Produces: delegation from `ensure`, `doctor`, `status`, `restart`, `stop`, and `logs`.

- [ ] **Step 1: Write failing delegation tests**

Add a helper stub that records commands and test:

```python
def test_services_routes_flaresolverr_commands_to_local_helper(tmp_path):
    # Run restart, stop, and logs separately with LOCAL_FLARESOLVERR_HELPER.
    assert restart.returncode == 0
    assert stop.returncode == 0
    assert logs.returncode == 0
    assert helper_log.read_text().splitlines() == [
        "restart",
        "stop",
        "logs --no-follow",
    ]

def test_services_ensure_calls_local_flaresolverr_before_launch_agents(tmp_path):
    # Existing launchctl/curl/lsof/npm stubs keep the three services healthy.
    result = subprocess.run(["bash", "scripts/services.sh", "ensure"], ...)
    assert result.returncode == 0
    assert helper_log.read_text().splitlines() == ["ensure"]

def test_services_status_and_doctor_include_local_flaresolverr(tmp_path):
    # Run each command with a helper stub.
    assert "doctor" in helper_log.read_text().splitlines()
    assert "status" in helper_log.read_text().splitlines()
```

- [ ] **Step 2: Run delegation tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_services.py -k flaresolverr -v`

Expected: FAIL because `services.sh` has no FlareSolverr routing.

- [ ] **Step 3: Implement minimal delegation**

Add:

```bash
LOCAL_FLARESOLVERR_HELPER="${LOCAL_FLARESOLVERR_HELPER:-${ROOT_DIR}/scripts/local-flaresolverr.sh}"

run_local_flaresolverr() {
  "${LOCAL_FLARESOLVERR_HELPER}" "$@"
}
```

Update usage strings to include `flaresolverr`. Delegate explicit commands before `label_for_service`. Call `run_local_flaresolverr ensure` from `ensure_services`, `doctor` from `doctor`, and `status` from `status`. Include `restart` and `stop` in no-argument all-service flows without treating FlareSolverr as a LaunchAgent.

- [ ] **Step 4: Run service tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_services.py -v`

Expected: all macOS service tests pass.

- [ ] **Step 5: Commit integration**

```bash
git add scripts/services.sh tests/test_services.py
git commit -m "feat(dev): integrate flaresolverr with service helper"
```

### Task 3: Documentation, real startup, and verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: completed local and aggregate service helpers.
- Produces: documented operation and verified running service.

- [ ] **Step 1: Document local behavior**

Add to the Local Development section:

```markdown
When `stream.cf_solver_url` points to `http://127.0.0.1:8191/v1`,
`scripts/services.sh ensure` also ensures the local FlareSolverr container.
On macOS it starts Colima when needed. Set `JAVHUB_LOCAL_FLARESOLVERR=0`
to opt out or `JAVHUB_FLARESOLVERR_IMAGE` to pin another image. This local
helper does not participate in the Docker Compose deployment.
```

- [ ] **Step 2: Run focused and full automated verification**

Run:

```bash
.venv/bin/python -m pytest tests/test_local_flaresolverr.py tests/test_services.py -v
.venv/bin/python -m pytest
```

Expected: all tests pass with zero failures.

- [ ] **Step 3: Start the real local service stack**

Run: `scripts/services.sh ensure`

Expected: Colima starts, `javhub-flaresolverr-local` runs, port 8191 is healthy, and existing JavInfoApi/backend/frontend remain healthy.

- [ ] **Step 4: Verify FlareSolverr API behavior**

Run a `sessions.create`, a protected-site `request.get`, then `sessions.destroy` against `http://127.0.0.1:8191/v1`.

Expected: each API response reports `status: ok`; `request.get` returns upstream HTTP 200.

- [ ] **Step 5: Commit docs and push**

```bash
git add README.md
git commit -m "docs(dev): explain local flaresolverr startup"
git status --short
git push origin main
```

Expected: clean worktree and successful push of `main`.
