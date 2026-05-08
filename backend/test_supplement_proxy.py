from __future__ import annotations
import unittest
from unittest.mock import patch


class SupplementConfigTest(unittest.TestCase):
    def test_supplement_admin_token_reads_env_var(self):
        from config import Config
        with patch.dict('os.environ', {'SUPPLEMENT_ADMIN_TOKEN': 'test-secret'}, clear=False):
            cfg = Config.__new__(Config)
            cfg._config = {}
            self.assertEqual(cfg.supplement_admin_token, 'test-secret')

    def test_supplement_admin_token_falls_back_to_config(self):
        from config import Config
        cfg = Config.__new__(Config)
        cfg._config = {'javinfo': {'supplement_admin_token': 'yaml-token'}}
        with patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('SUPPLEMENT_ADMIN_TOKEN', None)
            self.assertEqual(cfg.supplement_admin_token, 'yaml-token')

    def test_supplement_admin_token_defaults_empty(self):
        from config import Config
        cfg = Config.__new__(Config)
        cfg._config = {}
        import os
        os.environ.pop('SUPPLEMENT_ADMIN_TOKEN', None)
        self.assertEqual(cfg.supplement_admin_token, '')


if __name__ == '__main__':
    unittest.main()
