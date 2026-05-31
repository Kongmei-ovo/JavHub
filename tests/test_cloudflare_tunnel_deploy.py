from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_cloudflare_compose_adds_token_based_tunnel_without_exposing_javhub():
    compose_path = ROOT / "docker-compose.cloudflare.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    service = compose["services"]["cloudflared"]

    assert service["image"] == "cloudflare/cloudflared:${CLOUDFLARED_IMAGE_TAG:-latest}"
    assert service["command"] == "tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN:?set CLOUDFLARE_TUNNEL_TOKEN}"
    assert service["restart"] == "unless-stopped"
    assert service["depends_on"]["javhub"]["condition"] == "service_started"
    assert service["networks"] == ["default"]
    assert "ports" not in service
    assert "volumes" not in service


def test_cloudflare_access_doc_covers_public_deploy_safety_steps():
    doc = (ROOT / "docs" / "cloudflare-access-tunnel.md").read_text(encoding="utf-8")

    required_phrases = [
        "Cloudflare Access",
        "Cloudflare Tunnel",
        "CLOUDFLARE_TUNNEL_TOKEN",
        "JAVHUB_PORT=127.0.0.1:3000",
        "JAVINFOAPI_PORT=127.0.0.1:18080",
        "docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d",
        "只放行你的邮箱",
        "不要把 JavHub 端口直接暴露到公网",
        "不要把 JavInfoApi 端口直接暴露到公网",
        "origin",
        "http://javhub:80",
    ]
    for phrase in required_phrases:
        assert phrase in doc
