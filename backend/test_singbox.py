import unittest

from services.singbox import SingBoxError, build_config, build_pool_config, parse_subscription, parse_vless_uri


def test_parse_base64_vless_subscription():
    import base64
    uri = "vless://user@example.com:443?security=reality&sni=example.com&pbk=key#Tokyo"
    payload = base64.b64encode((uri + "\n").encode()).decode()
    assert parse_subscription(payload) == [uri]


def test_pool_config_uses_urltest_and_selector():
    uris = [
        "vless://user@example.com:443?security=reality&sni=example.com&pbk=key#Tokyo",
        "vless://user@example.org:443?security=reality&sni=example.org&pbk=key#LA",
    ]
    config, nodes = build_pool_config(uris)
    by_tag = {item["tag"]: item for item in config["outbounds"]}
    assert [node["name"] for node in nodes] == ["Tokyo", "LA"]
    assert by_tag["自动优选"]["type"] == "urltest"
    assert by_tag["proxy"]["type"] == "selector"
    assert config["experimental"]["clash_api"]["external_controller"] == "127.0.0.1:17891"


def test_pool_config_can_listen_on_container_network():
    uri = "vless://user@example.com:443?security=reality&sni=example.com&pbk=key#Tokyo"
    config, _ = build_pool_config([uri], listen_host="0.0.0.0")
    assert config["inbounds"][0]["listen"] == "0.0.0.0"


URI = ("vless://62a47dc6-026d-46e7-9aca-8689f8bb4100@example.com:443"
       "?encryption=none&flow=xtls-rprx-vision&fp=chrome&pbk=public-key"
       "&security=reality&sid=57&sni=www.cloudflare.com&type=tcp#node")


class SingBoxConfigTests(unittest.TestCase):
    def test_parses_reality_vision_link(self):
        node = parse_vless_uri(URI)
        self.assertEqual(node["server"], "example.com")
        self.assertEqual(node["flow"], "xtls-rprx-vision")
        self.assertEqual(node["short_id"], "57")

    def test_builds_local_socks_and_reality_outbound(self):
        cfg = build_config(URI)
        self.assertEqual(cfg["inbounds"][0]["listen"], "127.0.0.1")
        self.assertEqual(cfg["outbounds"][0]["tls"]["reality"]["public_key"], "public-key")
        self.assertEqual(cfg["route"]["final"], "proxy")

    def test_rejects_incomplete_reality_link(self):
        with self.assertRaises(SingBoxError):
            parse_vless_uri("vless://uuid@example.com:443?security=reality")


if __name__ == "__main__":
    unittest.main()
