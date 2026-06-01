import subprocess
from pathlib import Path


def write_executable(path, contents):
    path.write_text(contents)
    path.chmod(0o755)


def test_services_render_plists_injects_javinfo_source_proxy(tmp_path):
    javinfo_dir = tmp_path / "JavInfoApi"
    javinfo_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
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
        "exit 0\n",
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
        "echo 'COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME'\n",
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


def test_services_ensure_prints_health_without_restarting_running_services(tmp_path):
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
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
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
