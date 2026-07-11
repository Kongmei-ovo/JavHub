import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_executable(path, contents):
    path.write_text(contents)
    path.chmod(0o755)


def prepare(tmp_path, solver_url="http://127.0.0.1:8191/v1"):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(f'stream:\n  cf_solver_url: "{solver_url}"\n')
    return bin_dir, home_dir, config


def run_helper(tmp_path, command, *, config, bin_dir, home_dir, extra_env=None):
    env = {
        "HOME": str(home_dir),
        "JAVHUB_CONFIG_PATH": str(config),
        "JAVHUB_FLARESOLVERR_HEALTH_ATTEMPTS": "2",
        "JAVHUB_FLARESOLVERR_HEALTH_INTERVAL": "0",
        "PATH": f"{bin_dir}:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
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
    bin_dir, home_dir, config = prepare(tmp_path, "https://solver.example/v1")
    docker_log = tmp_path / "docker.log"
    write_executable(bin_dir / "docker", '#!/bin/sh\necho "$@" >> "$DOCKER_LOG"\nexit 0\n')

    result = run_helper(
        tmp_path,
        ["ensure"],
        config=config,
        bin_dir=bin_dir,
        home_dir=home_dir,
        extra_env={"DOCKER_LOG": str(docker_log)},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "skipped" in result.stdout.lower()
    assert not docker_log.exists()


def test_explicit_disable_skips_local_config(tmp_path):
    bin_dir, home_dir, config = prepare(tmp_path)
    docker_log = tmp_path / "docker.log"
    write_executable(bin_dir / "docker", '#!/bin/sh\necho "$@" >> "$DOCKER_LOG"\nexit 0\n')

    result = run_helper(
        tmp_path,
        ["ensure"],
        config=config,
        bin_dir=bin_dir,
        home_dir=home_dir,
        extra_env={"DOCKER_LOG": str(docker_log), "JAVHUB_LOCAL_FLARESOLVERR": "0"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "disabled" in result.stdout.lower()
    assert not docker_log.exists()


def test_ensure_starts_colima_then_creates_local_container(tmp_path):
    bin_dir, home_dir, config = prepare(tmp_path)
    docker_log = tmp_path / "docker.log"
    colima_log = tmp_path / "colima.log"
    daemon_ready = tmp_path / "daemon-ready"
    write_executable(
        bin_dir / "docker",
        "#!/bin/sh\n"
        'echo "$@" >> "$DOCKER_LOG"\n'
        'case "$1" in\n'
        '  info) [ -f "$DAEMON_READY" ] ;;\n'
        '  inspect) exit 1 ;;\n'
        '  run) echo local-container-id; exit 0 ;;\n'
        '  *) exit 0 ;;\n'
        "esac\n",
    )
    write_executable(
        bin_dir / "colima",
        "#!/bin/sh\n"
        'echo "$@" >> "$COLIMA_LOG"\n'
        'touch "$DAEMON_READY"\n'
        "exit 0\n",
    )
    write_executable(bin_dir / "curl", "#!/bin/sh\nexit 0\n")
    write_executable(bin_dir / "lsof", "#!/bin/sh\nexit 0\n")
    # This case verifies the macOS-only Colima fallback. CI runs on Linux, so
    # supply the platform command the shell helper consults.
    write_executable(bin_dir / "uname", "#!/bin/sh\necho Darwin\n")

    result = run_helper(
        tmp_path,
        ["ensure"],
        config=config,
        bin_dir=bin_dir,
        home_dir=home_dir,
        extra_env={
            "COLIMA_LOG": str(colima_log),
            "DAEMON_READY": str(daemon_ready),
            "DOCKER_LOG": str(docker_log),
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert colima_log.read_text().splitlines() == ["start"]
    docker_calls = docker_log.read_text()
    assert "run -d --name javhub-flaresolverr-local" in docker_calls
    assert "127.0.0.1:8191:8191" in docker_calls
    assert "com.kongmei.javhub.local-flaresolverr=true" in docker_calls
    assert "FlareSolverr http://127.0.0.1:8191/: ok" in result.stdout


def test_stop_refuses_unowned_same_name_container(tmp_path):
    bin_dir, home_dir, config = prepare(tmp_path)
    docker_log = tmp_path / "docker.log"
    write_executable(
        bin_dir / "docker",
        "#!/bin/sh\n"
        'echo "$@" >> "$DOCKER_LOG"\n'
        'case "$1" in\n'
        '  info) exit 0 ;;\n'
        '  inspect)\n'
        '    case "$2" in --format) echo false; exit 0 ;; esac\n'
        '    exit 0\n'
        '    ;;\n'
        '  *) exit 0 ;;\n'
        "esac\n",
    )
    write_executable(bin_dir / "curl", "#!/bin/sh\nexit 0\n")

    result = run_helper(
        tmp_path,
        ["stop"],
        config=config,
        bin_dir=bin_dir,
        home_dir=home_dir,
        extra_env={"DOCKER_LOG": str(docker_log)},
    )

    assert result.returncode == 1
    assert "not managed by JavHub" in result.stderr
    assert "rm -f" not in docker_log.read_text()
