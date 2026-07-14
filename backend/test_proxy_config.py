from __future__ import annotations

import pytest

from modules.proxy_config import effective_proxy_url


def test_disabled_proxy_has_no_effective_url():
    proxy = {
        "enabled": False,
        "http_url": "http://proxy.example:8080",
        "https_url": "https://proxy.example:8443",
    }

    assert effective_proxy_url(proxy) == ""


def test_http_proxy_prefers_http_url():
    proxy = {
        "enabled": True,
        "http_url": "  http://primary.example:8080  ",
        "https_url": "https://fallback.example:8443",
    }

    assert effective_proxy_url(proxy) == "http://primary.example:8080"


def test_http_proxy_falls_back_to_https_url():
    proxy = {
        "enabled": True,
        "http_url": "",
        "https_url": "  https://fallback.example:8443  ",
    }

    assert effective_proxy_url(proxy) == "https://fallback.example:8443"


def test_http_proxy_treats_whitespace_only_http_url_as_empty():
    proxy = {
        "enabled": True,
        "http_url": "   ",
        "https_url": "  https://fallback.example:8443  ",
    }

    assert effective_proxy_url(proxy) == "https://fallback.example:8443"


def test_vless_proxy_normalizes_advertise_host_whitespace():
    proxy = {"enabled": True, "mode": "vless", "singbox_port": 17890}

    assert (
        effective_proxy_url(proxy, advertise_host="  javhub.internal  ")
        == "socks5://javhub.internal:17890"
    )


def test_vless_advertise_host_is_keyword_only():
    proxy = {"enabled": True, "mode": "vless", "singbox_port": 17890}

    with pytest.raises(TypeError):
        effective_proxy_url(proxy, "javhub.internal")


@pytest.mark.parametrize(
    ("port", "expected"),
    [
        (1080, "socks5://127.0.0.1:1080"),
        ("17891", "socks5://127.0.0.1:17891"),
    ],
)
def test_vless_proxy_preserves_valid_ports(port, expected):
    proxy = {"enabled": True, "mode": "vless", "singbox_port": port}

    assert effective_proxy_url(proxy) == expected


@pytest.mark.parametrize("port", [None, "", "bad", 0, -1, 65536, True, False])
def test_vless_proxy_falls_back_for_invalid_ports(port):
    proxy = {"enabled": True, "mode": "vless", "singbox_port": port}

    assert effective_proxy_url(proxy) == "socks5://127.0.0.1:17890"


@pytest.mark.parametrize("host", [None, "", "   "])
def test_vless_proxy_falls_back_for_empty_advertise_host(host):
    proxy = {"enabled": True, "mode": "vless", "singbox_port": 17890}

    assert effective_proxy_url(proxy, advertise_host=host) == "socks5://127.0.0.1:17890"
