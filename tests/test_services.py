import subprocess
from pathlib import Path


def test_services_render_plists_injects_javinfo_source_proxy(tmp_path):
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
    javinfo_plist = home_dir / "Library" / "LaunchAgents" / "com.kongmei.javinfoapi.plist"
    assert javinfo_plist.exists()
    contents = javinfo_plist.read_text()
    assert "<key>JAVINFO_SOURCE_PROXY_URL</key>" in contents
    assert "<string>http://127.0.0.1:1082</string>" in contents
