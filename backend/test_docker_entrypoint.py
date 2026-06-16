from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "docker-entrypoint.sh"


def _run_entrypoint(tmp_path: Path, config_path: Path) -> subprocess.CompletedProcess[str]:
    example = tmp_path / "config.yaml.example"
    example.write_text("server:\n  port: 3000\n", encoding="utf-8")
    env = {
        **os.environ,
        "JAVHUB_ENTRYPOINT_INIT_ONLY": "1",
        "JAVHUB_CONFIG_PATH": str(config_path),
        "JAVHUB_CONFIG_EXAMPLE": str(example),
    }
    return subprocess.run(
        ["sh", str(ENTRYPOINT)],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_entrypoint_creates_missing_config_file(tmp_path: Path):
    config_path = tmp_path / "config" / "config.yaml"

    result = _run_entrypoint(tmp_path, config_path)

    assert result.returncode == 0, result.stderr
    assert config_path.read_text(encoding="utf-8") == "server:\n  port: 3000\n"


def test_entrypoint_rejects_config_path_directory(tmp_path: Path):
    config_path = tmp_path / "config" / "config.yaml"
    config_path.mkdir(parents=True)

    result = _run_entrypoint(tmp_path, config_path)

    assert result.returncode != 0
    assert "is a directory" in result.stderr
