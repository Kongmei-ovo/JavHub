import subprocess
import sys
from pathlib import Path

import pytest

# scripts/services.sh 是 macOS launchd 工具 (launchctl bootstrap/kickstart/print 等),
# 所有用例都通过 `bash scripts/services.sh ...` 走那条路径。Linux CI 没有 launchctl,
# 测试桩对不齐就会全炸 —— 这里整文件 skip,保留本地 macOS 上的 dev-tooling 保护。
pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="scripts/services.sh is macOS-only (uses launchctl); skip on non-darwin CI runners",
)


@pytest.fixture(autouse=True)
def disable_real_local_flaresolverr_for_service_helper_tests(monkeypatch):
    original_run = subprocess.run

    def run(*args, **kwargs):
        if kwargs.get("env") is not None:
            env = dict(kwargs["env"])
            env.setdefault("JAVHUB_LOCAL_FLARESOLVERR", "0")
            kwargs["env"] = env
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)


def write_executable(path, contents):
    path.write_text(contents)
    path.chmod(0o755)


def test_services_routes_flaresolverr_commands_to_local_helper(tmp_path):
    helper_log = tmp_path / "helper.log"
    helper = tmp_path / "local-flaresolverr.sh"
    write_executable(helper, '#!/bin/sh\necho "$@" >> "$HELPER_LOG"\nexit 0\n')
    env = {
        "HOME": str(tmp_path / "home"),
        "HELPER_LOG": str(helper_log),
        "LOCAL_FLARESOLVERR_HELPER": str(helper),
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    }

    commands = [
        ["restart", "flaresolverr"],
        ["stop", "flaresolverr"],
        ["logs", "flaresolverr", "--no-follow"],
    ]
    results = [
        subprocess.run(
            ["bash", "scripts/services.sh", *command],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        for command in commands
    ]

    assert [result.returncode for result in results] == [0, 0, 0]
    assert helper_log.read_text().splitlines() == ["restart", "stop", "logs --no-follow"]


def test_services_declares_flaresolverr_lifecycle_delegation():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "services.sh").read_text()

    assert 'run_local_flaresolverr "ensure"' in source
    assert 'run_local_flaresolverr "doctor"' in source
    assert 'run_local_flaresolverr "status"' in source
    assert 'run_local_flaresolverr "restart"' in source
    assert 'run_local_flaresolverr "stop"' in source


def test_services_render_plists_injects_javinfo_source_proxy(tmp_path):
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "proxy:\n"
        "  enabled: true\n"
        "  http_url: http://127.0.0.1:1082\n"
        "  https_url: ''\n"
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "render-plists"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "JAVHUB_CONFIG_PATH": str(config_path),
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    javinfo_plist = home_dir / "Library" / "LaunchAgents" / "com.kongmei.javinfoapi.plist"
    assert javinfo_plist.exists()
    contents = javinfo_plist.read_text()
    assert "<key>JAVINFO_SOURCE_PROXY_URL</key>" in contents
    assert "<string>http://127.0.0.1:1082</string>" in contents


def test_services_render_plists_serves_frontend_preview_on_public_port(tmp_path):
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "render-plists"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    frontend_plist = home_dir / "Library" / "LaunchAgents" / "com.kongmei.javhub.frontend.plist"
    contents = frontend_plist.read_text()
    assert "<string>preview</string>" in contents
    assert "<string>--host</string>" in contents
    assert "<string>0.0.0.0</string>" in contents
    assert "<string>--port</string>" in contents
    assert "<string>5174</string>" in contents
    assert "<string>dev</string>" not in contents


def test_services_render_plists_uses_configured_frontend_npm_binary(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    npm_bin = bin_dir / "npm"
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")
    write_executable(npm_bin, "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "render-plists"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "NPM_BIN": str(npm_bin),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    frontend_plist = home_dir / "Library" / "LaunchAgents" / "com.kongmei.javhub.frontend.plist"
    contents = frontend_plist.read_text()
    assert f"<string>{npm_bin}</string>" in contents


def test_services_restart_frontend_builds_before_kickstart(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    npm_log = tmp_path / "npm.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 200'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "npm",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$NPM_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "frontend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "NPM_LOG": str(npm_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert npm_log.read_text().splitlines() == ["run build"]
    launchctl_calls = launchctl_log.read_text()
    assert "bootout gui/" in launchctl_calls
    assert "bootstrap gui/" in launchctl_calls
    assert "kickstart -k gui/" in launchctl_calls


def test_services_restart_frontend_reports_unstable_service_after_health_success(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    frontend_crashed = tmp_path / "frontend-crashed"
    npm_log = tmp_path / "npm.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.frontend*)\n"
        "      if [ -f \"$FRONTEND_CRASHED\" ]; then\n"
        "        echo 'state = spawn scheduled'\n"
        "      else\n"
        "        echo 'state = running'\n"
        "        echo 'pid = 200'\n"
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ ! -f \"$FRONTEND_CRASHED\" ]; then\n"
        "      echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:5174*) touch \"$FRONTEND_CRASHED\"; echo '<html></html>'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "npm",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$NPM_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "frontend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "FRONTEND_CRASHED": str(frontend_crashed),
            "JAVHUB_RESTART_STABILITY_DELAY": "0",
            "LAUNCHCTL_LOG": str(launchctl_log),
            "NPM_LOG": str(npm_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "javhub-frontend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "javhub-frontend.launchd.err.log"
    assert result.returncode == 1
    assert "frontend http://127.0.0.1:5174: ok after restart" in result.stdout
    assert "frontend http://127.0.0.1:5174: unstable after restart" in result.stdout
    assert "frontend launchd: not running (state = spawn scheduled)" in result.stdout
    assert "frontend port 5174: no listener" in result.stdout
    assert f"frontend stdout: {stdout_log}" in result.stdout
    assert f"frontend stderr: {stderr_log}" in result.stdout


def test_services_doctor_reports_ready_dependencies(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")
    for name in ("launchctl", "lsof", "curl", "npm"):
        write_executable(bin_dir / name, "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "doctor"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Dependency check:" in result.stdout
    assert "launchctl: ok" in result.stdout
    assert "lsof: ok" in result.stdout
    assert "curl: ok" in result.stdout
    assert "backend uvicorn: ok" in result.stdout
    assert "frontend npm: ok" in result.stdout
    assert "javinfo binary: ok" in result.stdout
    assert "missing" not in result.stdout


def test_services_doctor_reports_missing_dependencies(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(bin_dir / "launchctl", "#!/bin/sh\nexit 0\n")
    write_executable(bin_dir / "curl", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "doctor"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Dependency check:" in result.stdout
    assert "launchctl: ok" in result.stdout
    assert "curl: ok" in result.stdout
    assert "lsof: missing" in result.stdout
    assert "frontend npm: missing" in result.stdout
    assert "javinfo binary: missing" in result.stdout
    assert "backend uvicorn: ok" in result.stdout


def test_services_doctor_reports_missing_configured_frontend_npm_binary(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")
    for name in ("launchctl", "lsof", "curl"):
        write_executable(bin_dir / name, "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "doctor"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "NPM_BIN": str(bin_dir / "missing-npm"),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert f"frontend npm: missing ({bin_dir / 'missing-npm'})" in result.stdout


def test_services_doctor_reports_ready_frontend_build_output(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<html></html>")

    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")
    for name in ("launchctl", "lsof", "curl", "npm"):
        write_executable(bin_dir / name, "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "doctor"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "JAVHUB_FRONTEND_DIST": str(frontend_dist),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert f"frontend build: ok ({frontend_dist / 'index.html'})" in result.stdout


def test_services_doctor_reports_missing_frontend_build_output(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    frontend_dist = tmp_path / "missing-dist"

    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")
    for name in ("launchctl", "lsof", "curl", "npm"):
        write_executable(bin_dir / name, "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "doctor"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "JAVHUB_FRONTEND_DIST": str(frontend_dist),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert f"frontend build: missing ({frontend_dist / 'index.html'})" in result.stdout


def test_services_logs_creates_missing_files_and_prints_paths(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tail_log = tmp_path / "tail.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "tail",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$TAIL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "logs", "backend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "TAIL_LOG": str(tail_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 0, result.stderr
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout
    assert stdout_log.exists()
    assert stderr_log.exists()
    tail_call = tail_log.read_text()
    assert "-n 120 -f" in tail_call
    assert str(stdout_log) in tail_call
    assert str(stderr_log) in tail_call


def test_services_logs_no_follow_prints_recent_lines_without_following(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tail_log = tmp_path / "tail.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "tail",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$TAIL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "logs", "frontend", "--no-follow"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "TAIL_LOG": str(tail_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "javhub-frontend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "javhub-frontend.launchd.err.log"
    assert result.returncode == 0, result.stderr
    assert f"frontend stdout: {stdout_log}" in result.stdout
    assert f"frontend stderr: {stderr_log}" in result.stdout
    tail_call = tail_log.read_text()
    tail_args = tail_call.split()
    assert tail_args[:2] == ["-n", "120"]
    assert "-f" not in tail_args
    assert str(stdout_log) in tail_call
    assert str(stderr_log) in tail_call


def test_services_logs_rejects_unknown_extra_arguments(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tail_log = tmp_path / "tail.log"
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "tail",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$TAIL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "logs", "backend", "--bogus"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "TAIL_LOG": str(tail_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Usage: scripts/services.sh logs" in result.stderr
    assert not tail_log.exists() or tail_log.read_text() == ""


def test_services_ensure_reports_missing_dependencies_before_launchctl(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    for name in ("launchctl", "lsof", "curl", "npm"):
        write_executable(
            bin_dir / name,
            "#!/bin/sh\n"
            "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
            "exit 0\n",
        )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Dependency check:" in result.stdout
    assert "javinfo binary: missing" in result.stdout
    assert not launchctl_log.exists() or launchctl_log.read_text() == ""
    assert not (home_dir / "Library" / "LaunchAgents").exists()


def test_services_ensure_builds_missing_frontend_preview_output(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    npm_log = tmp_path / "npm.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    frontend_dist = tmp_path / "frontend-dist"
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.frontend*) echo 'state = spawn scheduled'; exit 0 ;;\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 123'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(
        bin_dir / "npm",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$NPM_LOG\"\n"
        "mkdir -p \"$JAVHUB_FRONTEND_DIST\"\n"
        "printf '<html></html>' > \"$JAVHUB_FRONTEND_DIST/index.html\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "JAVHUB_FRONTEND_DIST": str(frontend_dist),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "NPM_LOG": str(npm_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert npm_log.read_text().splitlines() == ["run build"]
    assert (frontend_dist / "index.html").exists()
    launchctl_calls = launchctl_log.read_text()
    assert "kickstart gui/" in launchctl_calls
    assert "com.kongmei.javhub.frontend" in launchctl_calls


def test_services_status_prints_http_health_summary(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_log = tmp_path / "curl.log"

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 12345'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 12345 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 12345 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 12345 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    result = subprocess.run(
        ["bash", "scripts/services.sh", "status"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(tmp_path / "home"),
            "CURL_LOG": str(curl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "HTTP health:" in result.stdout
    assert "javinfo http://127.0.0.1:8080/health: ok" in result.stdout
    assert "backend http://127.0.0.1:18090/health: ok" in result.stdout
    assert "frontend http://127.0.0.1:5174: ok" in result.stdout
    curl_calls = curl_log.read_text()
    assert "http://127.0.0.1:8080/health" in curl_calls
    assert "http://127.0.0.1:18090/health" in curl_calls
    assert "http://127.0.0.1:5174" in curl_calls


def test_services_status_reports_port_listener_pid_mismatches(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_log = tmp_path / "curl.log"

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 12345'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 22222'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND   PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python  67890 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*) echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o command= -p 67890' ]; then\n"
        "  echo 'Python fake-server --port 18090'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    result = subprocess.run(
        ["bash", "scripts/services.sh", "status"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(tmp_path / "home"),
            "CURL_LOG": str(curl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Port diagnostics:" in result.stdout
    assert (
        "backend port 18090: listener pid(s) 67890 differ from launchd pid 12345"
        in result.stdout
    )
    assert "pid 67890 command: Python fake-server --port 18090" in result.stdout


def test_services_status_returns_nonzero_when_http_health_fails(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_log = tmp_path / "curl.log"

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 12345'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 12345 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 12345 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 12345 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) exit 22 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "status"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(tmp_path / "home"),
            "CURL_LOG": str(curl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "backend http://127.0.0.1:18090/health: failed" in result.stdout


def test_services_status_reports_backend_readiness_degradation(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_log = tmp_path / "curl.log"

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 12345'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 12345 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 12345 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 12345 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health/readiness*)\n"
        "    cat <<'JSON'\n"
        "{\"status\":\"degraded\",\"database\":{\"connectable\":false,\"host\":\"state-postgres\",\"port\":5432,\"database\":\"javhub\",\"error\":\"connection refused\"},\"javinfo\":{\"reachable\":false,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"timeout\"},\"cache\":{\"backend\":\"redis\",\"error\":\"redis down\"}}\n"
        "JSON\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "status"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(tmp_path / "home"),
            "CURL_LOG": str(curl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Backend readiness:" in result.stdout
    assert "backend readiness: degraded" in result.stdout
    assert (
        "database: failed (state-postgres:5432/javhub) connection refused"
        in result.stdout
    )
    assert "javinfo: failed (http://127.0.0.1:8080) timeout" in result.stdout
    assert "cache: failed (redis) redis down" in result.stdout
    assert "http://127.0.0.1:18090/health/readiness" in curl_log.read_text()


def test_services_status_treats_child_listener_pid_as_launchd_owned(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_log = tmp_path / "curl.log"

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 22222'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 22222 test 14u IPv4 0xabc      0t0  TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 22222 test 14u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node    200 test 14u IPv4 0xabc      0t0  TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 100'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*) echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )
    result = subprocess.run(
        ["bash", "scripts/services.sh", "status"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(tmp_path / "home"),
            "CURL_LOG": str(curl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        "frontend port 5174: ok (listener pid(s) 200 owned by launchd pid 100)"
        in result.stdout
    )
    assert "frontend port 5174: listener pid(s) 200 differ" not in result.stdout


def test_services_status_waits_for_transient_frontend_startup(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_log = tmp_path / "curl.log"
    lsof_count = tmp_path / "lsof-count"

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.frontend*) echo 'state = spawn scheduled'; echo 'pid = 100'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 22222'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 22222 test 14u IPv4 0xabc      0t0  TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 22222 test 14u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    count=0\n"
        "    if [ -f \"$LSOF_COUNT\" ]; then count=$(cat \"$LSOF_COUNT\"); fi\n"
        "    count=$((count + 1))\n"
        "    echo \"$count\" > \"$LSOF_COUNT\"\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ \"$count\" -ge 3 ]; then\n"
        "      echo 'node    200 test 14u IPv4 0xabc      0t0  TCP *:5174 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 100'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*)\n"
        "    if [ -f \"$LSOF_COUNT\" ] && [ \"$(cat \"$LSOF_COUNT\")\" -ge 3 ]; then\n"
        "      echo '<html></html>'\n"
        "      exit 0\n"
        "    fi\n"
        "    exit 22\n"
        "    ;;\n"
        "esac\n"
        "exit 22\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "status"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(tmp_path / "home"),
            "CURL_LOG": str(curl_log),
            "LSOF_COUNT": str(lsof_count),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "frontend port 5174: ok (listener pid(s) 200 owned by launchd pid 100)" in result.stdout
    assert "frontend http://127.0.0.1:5174: ok" in result.stdout


def test_services_ensure_prints_health_without_restarting_running_services(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 123'; exit 0 ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 100 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "HTTP health:" in result.stdout
    assert "javinfo http://127.0.0.1:8080/health: ok" in result.stdout
    assert "backend http://127.0.0.1:18090/health: ok" in result.stdout
    assert "frontend http://127.0.0.1:5174: ok" in result.stdout
    launchctl_calls = launchctl_log.read_text()
    assert "kickstart" not in launchctl_calls
    assert "bootout" not in launchctl_calls


def test_services_ensure_reports_unstable_running_backend_after_readiness_ok(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    backend_crashed = tmp_path / "backend-crashed"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*)\n"
        "      if [ -f \"$BACKEND_CRASHED\" ]; then\n"
        "        echo 'state = spawn scheduled'\n"
        "      else\n"
        "        echo 'state = running'\n"
        "        echo 'pid = 123'\n"
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 100 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ ! -f \"$BACKEND_CRASHED\" ]; then\n"
        "      echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 200'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*)\n"
        "    touch \"$BACKEND_CRASHED\"\n"
        "    echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_CRASHED": str(backend_crashed),
            "CURL_LOG": str(curl_log),
            "JAVHUB_RESTART_STABILITY_DELAY": "0",
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 1
    assert "backend readiness: ok" in result.stdout
    assert "backend http://127.0.0.1:18090/health: unstable" in result.stdout
    assert "backend launchd: not running (state = spawn scheduled)" in result.stdout
    assert "backend port 18090: no listener" in result.stdout
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout
    assert "kickstart" not in launchctl_log.read_text()


def test_services_ensure_reloads_loaded_frontend_when_plist_changes(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    npm_log = tmp_path / "npm.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    launch_agents_dir = home_dir / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True)
    old_npm = bin_dir / "old-npm"
    new_npm = bin_dir / "npm"
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")
    write_executable(new_npm, "#!/bin/sh\necho \"$@\" >> \"$NPM_LOG\"\nexit 0\n")

    frontend_plist = launch_agents_dir / "com.kongmei.javhub.frontend.plist"
    frontend_plist.write_text(
        "<plist><dict><key>ProgramArguments</key><array>"
        f"<string>{old_npm}</string>"
        "</array></dict></plist>\n"
    )

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 100 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 100 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 200'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "NPM_LOG": str(npm_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    launchctl_calls = launchctl_log.read_text()
    assert "bootout gui/" in launchctl_calls
    assert "bootstrap gui/" in launchctl_calls
    assert "kickstart -k gui/" in launchctl_calls
    assert "com.kongmei.javhub.frontend" in launchctl_calls
    assert f"<string>{new_npm}</string>" in frontend_plist.read_text()


def test_services_ensure_restarts_running_backend_when_health_fails(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    backend_restarted = tmp_path / "backend-restarted"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *kickstart*javhub.backend*) touch \"$BACKEND_RESTARTED\" ;;\n"
        "esac\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 123'; exit 0 ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python  123 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health*)\n"
        "    if [ ! -f \"$BACKEND_RESTARTED\" ]; then exit 22; fi\n"
        "    echo '{\"status\":\"ok\"}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_RESTARTED": str(backend_restarted),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        "backend http://127.0.0.1:18090/health: failed; restarting backend"
        in result.stdout
    )
    assert "backend http://127.0.0.1:18090/health: recovered" in result.stdout
    launchctl_calls = launchctl_log.read_text()
    assert "bootout gui/" in launchctl_calls
    assert "kickstart -k gui/" in launchctl_calls
    assert "com.kongmei.javhub.backend" in launchctl_calls


def test_services_ensure_restarts_backend_when_readiness_degrades(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    backend_restarted = tmp_path / "backend-restarted"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *kickstart*javhub.backend*) touch \"$BACKEND_RESTARTED\" ;;\n"
        "esac\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 123'; exit 0 ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 100 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 200'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*)\n"
        "    if [ ! -f \"$BACKEND_RESTARTED\" ]; then\n"
        "      echo '{\"status\":\"degraded\",\"database\":{\"connectable\":false,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"connection refused\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "      exit 0\n"
        "    fi\n"
        "    echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_RESTARTED": str(backend_restarted),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "backend readiness: degraded; restarting backend" in result.stdout
    assert "backend readiness: ok" in result.stdout
    assert "database: ok (localhost:5432/javhub)" in result.stdout
    launchctl_calls = launchctl_log.read_text()
    assert "bootout gui/" in launchctl_calls
    assert "kickstart -k gui/" in launchctl_calls
    assert "com.kongmei.javhub.backend" in launchctl_calls


def test_services_ensure_reports_unstable_backend_after_readiness_recovery(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    backend_restarted = tmp_path / "backend-restarted"
    backend_crashed = tmp_path / "backend-crashed"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *kickstart*javhub.backend*) touch \"$BACKEND_RESTARTED\" ;;\n"
        "esac\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*)\n"
        "      if [ -f \"$BACKEND_CRASHED\" ]; then\n"
        "        echo 'state = spawn scheduled'\n"
        "      else\n"
        "        echo 'state = running'\n"
        "        echo 'pid = 123'\n"
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 100 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ ! -f \"$BACKEND_CRASHED\" ]; then\n"
        "      echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 200'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*)\n"
        "    if [ ! -f \"$BACKEND_RESTARTED\" ]; then\n"
        "      echo '{\"status\":\"degraded\",\"database\":{\"connectable\":false,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"connection refused\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "      exit 0\n"
        "    fi\n"
        "    touch \"$BACKEND_CRASHED\"\n"
        "    echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_CRASHED": str(backend_crashed),
            "BACKEND_RESTARTED": str(backend_restarted),
            "CURL_LOG": str(curl_log),
            "JAVHUB_RESTART_STABILITY_DELAY": "0",
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 1
    assert "backend readiness: degraded; restarting backend" in result.stdout
    assert "backend readiness: ok" in result.stdout
    assert "backend http://127.0.0.1:18090/health: unstable after restart" in result.stdout
    assert "backend launchd: not running (state = spawn scheduled)" in result.stdout
    assert "backend port 18090: no listener" in result.stdout
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout


def test_services_ensure_reports_log_paths_when_readiness_stays_degraded(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 123'; exit 0 ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 100 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 200'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*)\n"
        "    echo '{\"status\":\"degraded\",\"database\":{\"connectable\":false,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"connection refused\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 1
    assert "backend readiness: degraded; restarting backend" in result.stdout
    assert "backend readiness: degraded" in result.stdout
    assert "database: failed (localhost:5432/javhub) connection refused" in result.stdout
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout


def test_services_ensure_prints_log_paths_when_backend_recovery_fails(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 123'; exit 0 ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python  123 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health*) exit 22 ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 1
    assert "backend http://127.0.0.1:18090/health: still failed after restart" in result.stdout
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout


def test_services_ensure_waits_for_newly_started_backend_before_recovery(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    backend_health_count = tmp_path / "backend-health-count"
    backend_started = tmp_path / "backend-started"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *kickstart*javhub.backend*) touch \"$BACKEND_STARTED\" ;;\n"
        "esac\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*)\n"
        "      if [ -f \"$BACKEND_STARTED\" ]; then\n"
        "        echo 'state = running'\n"
        "        echo 'pid = 123'\n"
        "      else\n"
        "        echo 'state = spawn scheduled'\n"
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ -f \"$BACKEND_STARTED\" ]; then\n"
        "      echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health*)\n"
        "    count=0\n"
        "    if [ -f \"$BACKEND_HEALTH_COUNT\" ]; then count=$(cat \"$BACKEND_HEALTH_COUNT\"); fi\n"
        "    count=$((count + 1))\n"
        "    echo \"$count\" > \"$BACKEND_HEALTH_COUNT\"\n"
        "    if [ \"$count\" -lt 2 ]; then exit 22; fi\n"
        "    echo '{\"status\":\"ok\"}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:5174*) echo '<html></html>'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_HEALTH_COUNT": str(backend_health_count),
            "BACKEND_STARTED": str(backend_started),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "backend http://127.0.0.1:18090/health: ok" in result.stdout
    assert "failed; restarting backend" not in result.stdout
    launchctl_calls = launchctl_log.read_text()
    assert "kickstart gui/" in launchctl_calls
    assert "kickstart -k gui/" not in launchctl_calls


def test_services_ensure_reports_unstable_frontend_after_http_recovery(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    frontend_restarted = tmp_path / "frontend-restarted"
    frontend_crashed = tmp_path / "frontend-crashed"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *kickstart*javhub.frontend*) touch \"$FRONTEND_RESTARTED\" ;;\n"
        "esac\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = running'; echo 'pid = 123'; exit 0 ;;\n"
        "    *javhub.frontend*)\n"
        "      if [ -f \"$FRONTEND_CRASHED\" ]; then\n"
        "        echo 'state = spawn scheduled'\n"
        "      else\n"
        "        echo 'state = running'\n"
        "        echo 'pid = 200'\n"
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 100 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *-iTCP:5174*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ ! -f \"$FRONTEND_CRASHED\" ]; then\n"
        "      echo 'node 200 test 15u IPv4 0xabc 0t0 TCP *:5174 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 200' ]; then\n"
        "  echo ' 200'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:5174*)\n"
        "    if [ ! -f \"$FRONTEND_RESTARTED\" ]; then exit 22; fi\n"
        "    touch \"$FRONTEND_CRASHED\"\n"
        "    echo '<html></html>'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health/readiness*) echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "esac\n"
        "exit 22\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "FRONTEND_CRASHED": str(frontend_crashed),
            "FRONTEND_RESTARTED": str(frontend_restarted),
            "JAVHUB_RESTART_STABILITY_DELAY": "0",
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "javhub-frontend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "javhub-frontend.launchd.err.log"
    assert result.returncode == 1
    assert "frontend http://127.0.0.1:5174: failed; restarting frontend" in result.stdout
    assert "frontend http://127.0.0.1:5174: recovered" in result.stdout
    assert "frontend http://127.0.0.1:5174: unstable after restart" in result.stdout
    assert "frontend launchd: not running (state = spawn scheduled)" in result.stdout
    assert "frontend port 5174: no listener" in result.stdout
    assert f"frontend stdout: {stdout_log}" in result.stdout
    assert f"frontend stderr: {stderr_log}" in result.stdout


def test_services_ensure_reclaims_project_owned_stale_backend_listener(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    kill_log = tmp_path / "kill.log"
    backend_started = tmp_path / "backend-started"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *kickstart*javhub.backend*) touch \"$BACKEND_STARTED\" ;;\n"
        "esac\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*)\n"
        "      if [ -f \"$BACKEND_STARTED\" ]; then\n"
        "        echo 'state = running'\n"
        "        echo 'pid = 123'\n"
        "      else\n"
        "        echo 'state = spawn scheduled'\n"
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "    *javhub.frontend*) echo 'state = running'; echo 'pid = 200'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ ! -f \"$KILL_LOG\" ]; then\n"
        "      echo 'Python  321 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    elif [ -f \"$BACKEND_STARTED\" ]; then\n"
        "      echo 'Python  123 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 321' ]; then\n"
        "  echo ' 1'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$*\" = '-o command= -p 321' ]; then\n"
        f"  echo '{Path.cwd()}/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 18090'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "fake-kill",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$KILL_LOG\"\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*) echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_STARTED": str(backend_started),
            "CURL_LOG": str(curl_log),
            "KILL_LOG": str(kill_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "JAVHUB_KILL_BIN": str(bin_dir / "fake-kill"),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "backend port 18090: reclaimed stale listener pid(s) 321" in result.stdout
    assert kill_log.read_text().splitlines() == ["-TERM 321"]
    launchctl_calls = launchctl_log.read_text()
    assert "kickstart gui/" in launchctl_calls
    assert "com.kongmei.javhub.backend" in launchctl_calls


def test_services_restart_backend_reclaims_project_owned_stale_listener(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    kill_log = tmp_path / "kill.log"
    backend_started = tmp_path / "backend-started"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *kickstart*javhub.backend*) touch \"$BACKEND_STARTED\" ;;\n"
        "esac\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*)\n"
        "      if [ -f \"$BACKEND_STARTED\" ]; then\n"
        "        echo 'state = running'\n"
        "        echo 'pid = 123'\n"
        "      else\n"
        "        echo 'state = spawn scheduled'\n"
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ ! -f \"$KILL_LOG\" ]; then\n"
        "      echo 'Python  321 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    elif [ -f \"$BACKEND_STARTED\" ]; then\n"
        "      echo 'Python  123 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 321' ]; then\n"
        "  echo ' 1'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$*\" = '-o command= -p 321' ]; then\n"
        f"  echo '{Path.cwd()}/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 18090'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "fake-kill",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$KILL_LOG\"\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*) echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'; exit 0 ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "backend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_STARTED": str(backend_started),
            "CURL_LOG": str(curl_log),
            "KILL_LOG": str(kill_log),
            "JAVHUB_RESTART_STABILITY_DELAY": "0",
            "LAUNCHCTL_LOG": str(launchctl_log),
            "JAVHUB_KILL_BIN": str(bin_dir / "fake-kill"),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "backend port 18090: reclaimed stale listener pid(s) 321" in result.stdout
    assert kill_log.read_text().splitlines() == ["-TERM 321"]
    launchctl_calls = launchctl_log.read_text()
    assert "bootout gui/" in launchctl_calls
    assert "bootstrap gui/" in launchctl_calls
    assert "kickstart -k gui/" in launchctl_calls


def test_services_restart_backend_reports_health_failure_with_log_paths(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 123'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 123 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health*) exit 22 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "backend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 1
    assert "backend http://127.0.0.1:18090/health: failed after restart" in result.stdout
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout


def test_services_restart_backend_reports_readiness_failure_with_log_paths(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 123'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 123 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*)\n"
        "    echo '{\"status\":\"degraded\",\"database\":{\"connectable\":false,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"connection refused\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "backend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 1
    assert "backend http://127.0.0.1:18090/health: ok after restart" in result.stdout
    assert "backend readiness: degraded" in result.stdout
    assert "database: failed (localhost:5432/javhub) connection refused" in result.stdout
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout


def test_services_restart_backend_reports_unstable_service_after_readiness_success(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    backend_crashed = tmp_path / "backend-crashed"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*)\n"
        "      if [ -f \"$BACKEND_CRASHED\" ]; then\n"
        "        echo 'state = spawn scheduled'\n"
        "        exit 0\n"
        "      fi\n"
        "      echo 'state = running'\n"
        "      echo 'pid = 123'\n"
        "      exit 0\n"
        "      ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    if [ ! -f \"$BACKEND_CRASHED\" ]; then\n"
        "      echo 'Python 123 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    fi\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:18090/health/readiness*)\n"
        "    touch \"$BACKEND_CRASHED\"\n"
        "    echo '{\"status\":\"ok\",\"database\":{\"connectable\":true,\"host\":\"localhost\",\"port\":5432,\"database\":\"javhub\",\"error\":\"\"},\"javinfo\":{\"reachable\":true,\"api_url\":\"http://127.0.0.1:8080\",\"error\":\"\"},\"cache\":{\"backend\":\"redis\",\"error\":\"\"}}'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *127.0.0.1:18090/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "backend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "BACKEND_CRASHED": str(backend_crashed),
            "CURL_LOG": str(curl_log),
            "JAVHUB_RESTART_STABILITY_DELAY": "0",
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    stdout_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.log"
    stderr_log = Path(__file__).resolve().parents[1] / "backend" / "javhub-backend.launchd.err.log"
    assert result.returncode == 1
    assert "backend http://127.0.0.1:18090/health: unstable after restart" in result.stdout
    assert "backend launchd: not running (state = spawn scheduled)" in result.stdout
    assert "backend port 18090: no listener" in result.stdout
    assert f"backend stdout: {stdout_log}" in result.stdout
    assert f"backend stderr: {stderr_log}" in result.stdout


def test_services_rebuild_javinfo_reports_health_failure_with_log_paths(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    go_log = tmp_path / "go.log"
    curl_log = tmp_path / "curl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "go",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$GO_LOG\"\n"
        "touch JavInfoApi\n"
        "chmod +x JavInfoApi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 123'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) exit 22 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "rebuild-javinfo"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "GO_LOG": str(go_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert go_log.read_text().splitlines() == ["build -o JavInfoApi ./cmd/javinfoapi"]
    assert "javinfo http://127.0.0.1:8080/health: failed after restart" in result.stdout
    assert f"javinfo stdout: {javinfo_dir / 'javinfoapi.launchd.log'}" in result.stdout
    assert f"javinfo stderr: {javinfo_dir / 'javinfoapi.launchd.err.log'}" in result.stdout


def test_services_rebuild_javinfo_reports_healthy_restart(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    go_log = tmp_path / "go.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "go",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$GO_LOG\"\n"
        "touch JavInfoApi\n"
        "chmod +x JavInfoApi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  echo 'state = running'\n"
        "  echo 'pid = 123'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:8080*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'JavInfoApi 123 test 15u IPv4 0xabc 0t0 TCP *:8080 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *127.0.0.1:8080/health*) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "rebuild-javinfo"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "GO_LOG": str(go_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert go_log.read_text().splitlines() == ["build -o JavInfoApi ./cmd/javinfoapi"]
    assert "javinfo http://127.0.0.1:8080/health: ok after restart" in result.stdout
    launchctl_calls = launchctl_log.read_text()
    assert "bootout gui/" in launchctl_calls
    assert "bootstrap gui/" in launchctl_calls
    assert "kickstart -k gui/" in launchctl_calls


def test_services_rebuild_javinfo_rejects_extra_arguments_before_side_effects(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    go_log = tmp_path / "go.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "go",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$GO_LOG\"\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "rebuild-javinfo", "extra"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "GO_LOG": str(go_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Usage: scripts/services.sh rebuild-javinfo" in result.stderr
    assert not go_log.exists() or go_log.read_text() == ""
    assert not launchctl_log.exists() or launchctl_log.read_text() == ""
    assert not (home_dir / "Library" / "LaunchAgents").exists()


def test_services_ensure_does_not_kill_unknown_backend_port_listener(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    curl_log = tmp_path / "curl.log"
    kill_log = tmp_path / "kill.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_executable(javinfo_dir / "JavInfoApi", "#!/bin/sh\nexit 0\n")

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in\n"
        "    *javhub.backend*) echo 'state = spawn scheduled'; exit 0 ;;\n"
        "    *) echo 'state = running'; echo 'pid = 100'; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Other   321 test 15u IPv4 0xabc      0t0  TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o ppid= -p 321' ]; then\n"
        "  echo ' 1'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$*\" = '-o command= -p 321' ]; then\n"
        "  echo '/Applications/Other.app/Contents/MacOS/Other --port 18090'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    write_executable(
        bin_dir / "fake-kill",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$KILL_LOG\"\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$CURL_LOG\"\n"
        "exit 0\n",
    )
    write_executable(bin_dir / "npm", "#!/bin/sh\nexit 0\n")

    result = subprocess.run(
        ["bash", "scripts/services.sh", "ensure"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "CURL_LOG": str(curl_log),
            "KILL_LOG": str(kill_log),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "JAVHUB_KILL_BIN": str(bin_dir / "fake-kill"),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert (
        "backend port 18090: blocked by non-JavHub listener pid(s) 321; not starting"
        in result.stdout
    )
    assert (
        "pid 321 command: /Applications/Other.app/Contents/MacOS/Other --port 18090"
        in result.stdout
    )
    assert not kill_log.exists() or kill_log.read_text() == ""
    launchctl_calls = launchctl_log.read_text()
    assert "kickstart gui/" not in launchctl_calls


def test_services_stop_backend_reports_stuck_port_listener(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *-iTCP:18090*)\n"
        "    echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "    echo 'Python 321 test 15u IPv4 0xabc 0t0 TCP *:18090 (LISTEN)'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *) echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'; exit 0 ;;\n"
        "esac\n",
    )
    write_executable(
        bin_dir / "ps",
        "#!/bin/sh\n"
        "if [ \"$*\" = '-o command= -p 321' ]; then\n"
        "  echo '/Users/kongmei/Code/JavHub/.venv/bin/uvicorn main:app --port 18090'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "stop", "backend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "backend port 18090: still has listener pid(s) 321 after stop" in result.stdout
    assert "pid 321 command: /Users/kongmei/Code/JavHub/.venv/bin/uvicorn main:app --port 18090" in result.stdout
    assert "bootout gui/" in launchctl_log.read_text()


def test_services_stop_backend_reports_released_port(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )
    write_executable(
        bin_dir / "lsof",
        "#!/bin/sh\n"
        "echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "stop", "backend"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "backend port 18090: stopped" in result.stdout
    assert "bootout gui/" in launchctl_log.read_text()


def test_services_restart_rejects_extra_service_arguments(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "backend", "extra"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Usage: scripts/services.sh restart" in result.stderr
    assert not launchctl_log.exists() or launchctl_log.read_text() == ""


def test_services_stop_rejects_extra_service_arguments(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "stop", "backend", "extra"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Usage: scripts/services.sh stop" in result.stderr
    assert not launchctl_log.exists() or launchctl_log.read_text() == ""


def test_services_restart_rejects_unknown_service_before_side_effects(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "restart", "nope"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Unknown service" in result.stderr
    assert not launchctl_log.exists() or launchctl_log.read_text() == ""
    assert not (home_dir / "Library" / "LaunchAgents").exists()


def test_services_stop_rejects_unknown_service_before_side_effects(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "stop", "nope"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Unknown service" in result.stderr
    assert not launchctl_log.exists() or launchctl_log.read_text() == ""
    assert not (home_dir / "Library" / "LaunchAgents").exists()


def test_services_render_plists_escapes_proxy_url_xml_special_characters(tmp_path):
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "proxy:\n"
        "  enabled: true\n"
        "  http_url: 'http://proxy.local:8080/?a=1&b=<tag>\"quote\"'\n"
        "  https_url: ''\n"
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "render-plists"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "JAVHUB_CONFIG_PATH": str(config_path),
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    javinfo_plist = home_dir / "Library" / "LaunchAgents" / "com.kongmei.javinfoapi.plist"
    contents = javinfo_plist.read_text()
    assert (
        "<string>http://proxy.local:8080/?a=1&amp;b=&lt;tag&gt;&quot;quote&quot;</string>"
        in contents
    )


def test_services_render_plists_does_not_call_launchctl(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    write_executable(
        bin_dir / "launchctl",
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$LAUNCHCTL_LOG\"\n"
        "exit 0\n",
    )

    result = subprocess.run(
        ["bash", "scripts/services.sh", "render-plists"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "HOME": str(home_dir),
            "JAVINFO_DIR": str(javinfo_dir),
            "LAUNCHCTL_LOG": str(launchctl_log),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not launchctl_log.exists() or launchctl_log.read_text() == ""
