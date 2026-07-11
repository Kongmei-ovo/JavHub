import unittest

from services.singbox import SingBoxError, build_config, parse_vless_uri


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
