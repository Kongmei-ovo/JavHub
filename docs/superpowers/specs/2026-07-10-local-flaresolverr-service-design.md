# 本地 FlareSolverr 服务管理设计

## 目标

让 macOS 本地开发环境通过项目服务助手自动获得可用的 FlareSolverr，从而测试依赖 Cloudflare challenge 求解的来源；同时保持现有云端 Docker Compose 部署完全不变。

## 部署边界

- 本地开发继续使用 `scripts/services.sh`、macOS LaunchAgents 和 Colima。
- 云端继续使用 `docker compose up -d`；不修改 `docker-compose.yml`、`docker-compose.cloudflare.yml`、`Dockerfile` 或容器入口脚本。
- 本地容器使用独立名称 `javhub-flaresolverr-local`，只发布 `127.0.0.1:8191:8191`，不与 Compose 服务名或网络耦合。
- 默认镜像为 `ghcr.io/flaresolverr/flaresolverr:latest`，允许通过 `JAVHUB_FLARESOLVERR_IMAGE` 覆盖。

## 自动管理条件

新增 `scripts/local-flaresolverr.sh`，从 `JAVHUB_CONFIG_PATH` 或项目根目录 `config.yaml` 读取 `stream.cf_solver_url`。

- URL 指向 `127.0.0.1:8191` 或 `localhost:8191` 时，认为本地求解器由项目管理。
- URL 为空、指向远端或使用 Compose 服务名时，返回“跳过”，不启动 Colima 或 Docker。
- 可用 `JAVHUB_LOCAL_FLARESOLVERR=0` 显式禁用，也可用 `JAVHUB_LOCAL_FLARESOLVERR=1` 显式启用。

## 本地助手职责

`scripts/local-flaresolverr.sh` 提供以下命令：

- `ensure`：检查 Docker；在 macOS 且存在 Colima时，如 Docker daemon 不可用则执行 `colima start`。随后复用或创建本地容器，等待 HTTP 健康。
- `restart`：删除同名旧容器并按当前镜像重新创建，等待健康。
- `stop`：停止并删除本地容器，但不停止 Colima，避免影响用户其他容器。
- `status`：输出管理条件、Docker daemon、容器和 `http://127.0.0.1:8191/` 的状态。
- `logs`：透传 `docker logs`，支持 `--no-follow`。
- `doctor`：只检查配置、Docker CLI，以及需要时的 Colima 可用性，不修改状态。

容器启动参数固定包括端口映射、日志级别、时区和 `unless-stopped` 重启策略。启动已存在但停止的正确容器时优先复用；镜像或端口配置不一致时重新创建。

## 与 services.sh 集成

- `ensure` / `start` 在 LaunchAgent 依赖预检通过后调用本地求解器 `ensure`，然后继续现有三个服务。
- `restart flaresolverr`、`stop flaresolverr` 和 `logs flaresolverr` 委托给新助手。
- 无参数 `restart`、`stop` 同时包含 FlareSolverr；停止全部服务时仍不停止 Colima。
- `status` 在现有 LaunchAgent、端口和 HTTP 状态后追加 FlareSolverr 状态。
- `doctor` 追加本地求解器依赖信息；仅当配置要求本地求解器但依赖缺失时返回失败。
- `render-plists` 和 `rebuild-javinfo` 行为保持不变。

## 健康与错误处理

- FlareSolverr 根路径返回成功 JSON 即视为服务可用；等待上限采用有界重试。
- 8191 被非目标进程或其他容器占用时，不删除未知资源，输出明确诊断并失败。
- Colima 启动失败、镜像拉取失败、容器退出或健康超时均使调用失败，并给出后续可执行的状态/日志命令。
- 不读取或输出配置中的其他密钥。

## 测试与验收

- 先为本地助手和 `services.sh` 集成添加失败测试，再实现功能。
- 测试覆盖：本地/远程配置判断、禁用开关、Colima 自动启动、容器创建与复用、端口冲突、健康超时，以及 `services.sh` 的 ensure/restart/stop/status/logs 路由。
- 运行 `tests/test_services.py`、相关配置测试和完整项目测试。
- 在当前 arm64 Mac 上执行 `scripts/services.sh ensure`，确认 Colima、容器和 8191 健康；再通过 FlareSolverr API 发起一个受保护站点请求作为真实烟雾测试。
- 提交到 `main` 并推送当前分支。
