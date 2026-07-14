# LaunchAgent Configuration Boundaries Design

**Date:** 2026-07-14

## Context

The macOS service helper currently renders three LaunchAgent property lists with shell heredocs. Review confirmed three boundary defects:

1. `JAVHUB_CONFIG_PATH` is used while rendering JavInfo settings but is not placed in the backend LaunchAgent environment. A custom configuration therefore produces split-brain processes.
2. Database and Redis values are interpolated as raw XML. Characters such as `&` or `<` make the generated backend plist invalid after files have already been overwritten.
3. The JavInfo proxy renderer only checks `http_url` and `https_url`. In managed VLESS mode the effective backend proxy is a local SOCKS5 endpoint, so restarting JavInfo drops or misroutes its source proxy until the backend pushes configuration later.

## Goals

- Generate syntactically valid plists for every supported environment value.
- Pass the exact effective configuration path to the backend process.
- Make the JavInfo LaunchAgent proxy match `Config.proxy_url` semantics, including VLESS.
- Keep plist output deterministic so `ensure` does not restart healthy services without a semantic change.
- Preserve all existing labels, ports, paths, health behavior, and service commands.

## Non-Goals

- Replace LaunchAgents with another process manager.
- Change the application configuration schema or valid proxy-mode behavior; malformed VLESS ports are normalized consistently as an explicit bug fix.
- Restart services during renderer unit tests.
- Generalize the helper for arbitrary third-party services.

## Design

### Structured renderer

Add `scripts/render_service_plists.py`, a small command-line helper using the standard-library `plistlib`. `scripts/services.sh::write_plists()` will keep ownership of change detection, linting, and service lifecycle decisions, but delegate construction of the JavInfo, backend, and frontend dictionaries to this helper.

The shell-to-renderer contract is explicit:

- CLI arguments provide the three output paths, repository root, JavInfo directory, resolved `FRONTEND_NPM_BIN`, and effective configuration path. The renderer derives the existing labels, ports, backend uvicorn path, working directories, and log paths from those values.
- The inherited environment provides the existing `JAVHUB_DB_*`, `JAVHUB_CACHE_BACKEND`, `JAVHUB_REDIS_*`, and `JAVHUB_PROXY_ADVERTISE_HOST` values. The renderer applies the same defaults currently embedded in `services.sh`.
- `NPM_BIN` is resolved only by `services.sh`; the resulting `FRONTEND_NPM_BIN` is passed as an argument rather than rediscovered from an unexported shell variable.

`plistlib` will serialize all dynamic strings, so paths, passwords, URLs, and prefixes round-trip without manual XML escaping. XML output uses sorted keys and stable formatting for byte-for-byte change detection.

All three plist payloads will be constructed, serialized, and parsed back with `plistlib` before any destination is touched. Each payload is then written to a sibling temporary file with mode `0644` before each destination is atomically replaced with `os.replace()`. This is intentionally a per-file atomicity guarantee, not an impossible transaction across three filesystem paths: configuration, serialization, or temporary-write failures leave all installed files unchanged; a later `os.replace()` failure can leave a mix of old and new complete plists. In that case the helper fails, `set -e` prevents any lifecycle action, and no destination contains a partial or malformed file.

### Configuration path propagation

The shell passes this raw effective path:

```text
JAVHUB_CONFIG_PATH, when non-empty
otherwise <repo-root>/config.yaml
```

The renderer expands `~` and resolves a relative value against its invocation working directory, with `strict=False`, before doing any reads. That normalized absolute path is added to the backend `EnvironmentVariables` dictionary as `JAVHUB_CONFIG_PATH`. The same absolute path is used to read JavInfo worker and proxy settings, so a caller running `services.sh` outside the repository cannot give the two processes different relative-path bases.

### Effective JavInfo proxy

Extract a dependency-free `effective_proxy_url()` helper into `backend/modules/proxy_config.py`. Both `backend/config.py::Config.proxy_url` and the renderer call this helper, so valid and invalid proxy values have one definition instead of two similar implementations. The renderer adds `<repo-root>/backend` to its import path solely to load this pure helper.

When `proxy.enabled` is false, the shared helper returns an empty string and the JavInfo plist omits `JAVINFO_SOURCE_PROXY_URL`.

When enabled:

- `mode: vless` produces `socks5://<advertise-host>:<singbox-port>`, using stripped `JAVHUB_PROXY_ADVERTISE_HOST` or `127.0.0.1`. A numeric `singbox_port` in `1..65535` is used; empty, non-numeric, zero, negative, and out-of-range values use `17890` in both backend and renderer.
- Other modes use the first non-empty `http_url`, then `https_url`.
- An enabled non-VLESS proxy with neither URL omits the variable rather than writing an empty value.

This deliberately makes `Config.proxy_url` and the restart-time JavInfo environment identical for every supported or malformed input.

### Shell integration

`services.sh` will retain its public interface and the existing `JAVINFO_PLIST_CHANGED`, `BACKEND_PLIST_CHANGED`, and `FRONTEND_PLIST_CHANGED` comparisons. The heredoc blocks and `xml_escape`, `javinfo_source_proxy_url`, and `javinfo_worker_count` functions become unnecessary and will be removed after tests exercise the renderer directly.

## Error Handling

- Invalid or unreadable YAML falls back to the same defaults used today: six JavInfo workers and no source proxy.
- Invalid numeric worker values use the existing bounded default. Invalid VLESS ports use the shared normalization described above.
- Renderer failures propagate to `services.sh`; `set -e` prevents bootstrap or restart with stale assumptions.
- Destination directories are created before temporary files, and temporary files are removed on failure. A replacement failure is reported honestly as a possible mix of complete old and new plist versions.

## Tests

Create cross-platform renderer tests separate from the macOS-only lifecycle tests. Parse generated plists with `plistlib`, never string matching, and cover:

- custom `JAVHUB_CONFIG_PATH` round-trips into the backend plist;
- a relative custom path invoked outside the repository is normalized once and used for both the backend environment and renderer reads;
- DB password, Redis URL, Redis prefix, and paths containing XML metacharacters round-trip exactly;
- VLESS produces the configured SOCKS5 URL and ignores stale HTTP fields;
- empty, non-numeric, zero, negative, and out-of-range VLESS ports produce the same URL through the shared helper and the renderer;
- ordinary HTTP proxy and disabled proxy retain existing behavior;
- worker count remains bounded;
- rendering is deterministic across two identical runs;
- a configuration, serialization, or temporary-write error does not replace existing plist files;
- a replacement failure never produces a partial plist and prevents service lifecycle actions;
- all three parsed dictionaries preserve the existing labels, arguments, working directories, environment defaults, lifecycle flags, log paths, and `0644` file mode.

Keep `tests/test_services.py` integration coverage proving `services.sh render-plists` passes the resolved npm executable and configuration path, invokes the structured renderer, and produces all three structurally complete files.

## Verification

- Run the renderer and service-helper test files.
- Run `plutil -lint` on all three generated plists on macOS.
- Render with the current environment and compare parsed dictionaries against the installed LaunchAgents.
- Run `scripts/services.sh ensure`, then `scripts/services.sh status` and confirm healthy services are not restarted when files are unchanged.
- Temporarily render a VLESS configuration in an isolated HOME and verify the JavInfo proxy value without restarting the real service.

## Success Criteria

- Custom configuration paths cannot split backend and JavInfo configuration.
- All dynamic plist values survive arbitrary XML metacharacters.
- Managed VLESS restarts JavInfo with the correct local SOCKS5 proxy immediately.
- Failed rendering cannot leave malformed installed plist files.
- Existing service lifecycle tests and live health checks remain green.
