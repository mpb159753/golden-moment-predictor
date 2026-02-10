import unittest
import os
import tempfile
from pathlib import Path
from gmp.core.config_loader import load_engine_config, EngineConfig

class TestConfigLoader(unittest.TestCase):
    def test_load_default_config(self):
        # Only works if config file doesn't exist or we pass non-existent path
        config = load_engine_config("non_existent_config.yaml")
        # Should return default config
        self.assertEqual(config.db_path, "gmp_cache.db")
        self.assertEqual(config.coord_precision, 2)

    def test_load_valid_yaml(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml") as tmp:
            tmp.write("db_path: 'test_db.sqlite'\ncoord_precision: 4\n")
            tmp_path = tmp.name
        
        try:
            config = load_engine_config(tmp_path)
            self.assertEqual(config.db_path, "test_db.sqlite")
            self.assertEqual(config.coord_precision, 4)
            # Check default values are preserved for missing fields
            self.assertEqual(config.memory_cache_ttl_seconds, 300)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
