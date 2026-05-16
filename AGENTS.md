# JavHub Codex Notes

Use the project service helper instead of ad hoc process commands.

- Ensure services are installed and running: `scripts/services.sh ensure`
- Check status and ports: `scripts/services.sh status`
- Restart everything: `scripts/services.sh restart`
- Restart one service: `scripts/services.sh restart backend|frontend|javinfo`
- Stop services: `scripts/services.sh stop [backend|frontend|javinfo]`
- Rebuild JavInfoApi after Go changes: `scripts/services.sh rebuild-javinfo`
- Tail logs: `scripts/services.sh logs backend|frontend|javinfo`

Services are managed as macOS user LaunchAgents:

- `com.kongmei.javinfoapi` listens on port `8080`.
- `com.kongmei.javhub.backend` listens on port `18090`.
- `com.kongmei.javhub.frontend` listens on port `5174`.

Codex environment setup should call `scripts/services.sh ensure` so opening the project starts missing services without killing healthy ones.
