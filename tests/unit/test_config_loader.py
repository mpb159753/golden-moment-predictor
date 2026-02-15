"""tests/unit/test_config_loader.py — ConfigManager 单元测试

测试引擎配置的加载、访问、错误处理和默认值。
"""

import os
import tempfile

import pytest
import yaml

from gmp.core.config_loader import ConfigManager, EngineConfig


# ==================== Fixtures ====================


@pytest.fixture
def engine_config_yaml() -> dict:
    """完整的引擎配置字典，用于生成测试 YAML 文件。"""
    return {
        "cache": {
            "db_path": "data/gmp.db",
            "freshness": {
                "forecast_valid_hours": 24,
                "archive_never_stale": True,
            },
        },
        "safety": {
            "precip_threshold": 50,
            "visibility_threshold": 1000,
        },
        "analysis": {
            "local_cloud_max": 30,
            "target_cloud_max": 30,
            "light_path_cloud_max": 50,
            "wind_speed_max": 20,
            "frost_temperature": 2.0,
        },
        "retention": {
            "max_temp": 2.5,
            "max_sun_hours": 5,
            "max_wind": 30.0,
        },
        "light_path": {
            "count": 10,
            "interval_km": 10,
        },
        "scoring": {
            "golden_mountain": {
                "trigger": {"max_cloud_cover": 80},
                "weights": {
                    "light_path": 35,
                    "target_visible": 40,
                    "local_clear": 25,
                },
                "thresholds": {
                    "light_path_cloud": [10, 20, 30, 50],
                    "target_cloud": [10, 20, 30, 50],
                    "local_cloud": [15, 30, 50],
                },
                "veto_threshold": 0,
            },
            "cloud_sea": {
                "weights": {"gap": 50, "density": 30, "wind": 20},
                "thresholds": {
                    "gap_meters": [800, 500, 200],
                    "density_pct": [80, 50, 30],
                    "wind_speed": [3, 5, 8],
                    "mid_cloud_penalty": [30, 60],
                },
            },
        },
        "confidence": {
            "high": [1, 2],
            "medium": [3, 4],
            "low": [5, 16],
        },
        "summary": {"mode": "rule"},
        "backtest": {
            "max_history_days": 365,
            "archive_api_base": "https://archive-api.open-meteo.com/v1/archive",
        },
    }


@pytest.fixture
def config_file(engine_config_yaml, tmp_path) -> str:
    """写入临时 YAML 文件并返回路径。"""
    config_path = tmp_path / "engine_config.yaml"
    config_path.write_text(yaml.dump(engine_config_yaml, allow_unicode=True))
    return str(config_path)


# ==================== 加载有效配置 ====================


class TestConfigManagerLoad:
    """ConfigManager 正常加载测试。"""

    def test_load_valid_yaml(self, config_file):
        """加载有效 YAML → EngineConfig 属性正确。"""
        mgr = ConfigManager(config_path=config_file)
        cfg = mgr.config

        assert isinstance(cfg, EngineConfig)
        assert cfg.db_path == "data/gmp.db"
        assert cfg.light_path_count == 10
        assert cfg.light_path_interval_km == 10.0
        assert cfg.summary_mode == "rule"
        assert cfg.backtest_max_history_days == 365

    def test_load_data_freshness(self, config_file):
        """data_freshness 字段正确加载。"""
        mgr = ConfigManager(config_path=config_file)
        assert mgr.config.data_freshness["forecast_valid_hours"] == 24
        assert mgr.config.data_freshness["archive_never_stale"] is True

    def test_load_safety(self, config_file):
        """safety 字段正确加载。"""
        mgr = ConfigManager(config_path=config_file)
        assert mgr.config.safety["precip_threshold"] == 50
        assert mgr.config.safety["visibility_threshold"] == 1000

    def test_load_scoring(self, config_file):
        """scoring 字段正确加载。"""
        mgr = ConfigManager(config_path=config_file)
        gm = mgr.config.scoring["golden_mountain"]
        assert gm["weights"]["light_path"] == 35
        assert gm["thresholds"]["light_path_cloud"] == [10, 20, 30, 50]

    def test_load_confidence(self, config_file):
        """confidence 字段正确加载。"""
        mgr = ConfigManager(config_path=config_file)
        assert mgr.config.confidence == {
            "high": [1, 2],
            "medium": [3, 4],
            "low": [5, 16],
        }


# ==================== 便捷访问方法 ====================


class TestConfigManagerAccessors:
    """ConfigManager 便捷访问方法测试。"""

    def test_get_plugin_config_exists(self, config_file):
        """get_plugin_config('golden_mountain') 返回正确的 weights/thresholds。"""
        mgr = ConfigManager(config_path=config_file)
        plugin_cfg = mgr.get_plugin_config("golden_mountain")

        assert plugin_cfg["weights"]["light_path"] == 35
        assert plugin_cfg["weights"]["target_visible"] == 40
        assert plugin_cfg["thresholds"]["local_cloud"] == [15, 30, 50]
        assert plugin_cfg["veto_threshold"] == 0

    def test_get_plugin_config_not_exists(self, config_file):
        """get_plugin_config('不存在的plugin') 返回空 dict。"""
        mgr = ConfigManager(config_path=config_file)
        result = mgr.get_plugin_config("不存在的plugin")
        assert result == {}

    def test_get_safety_config(self, config_file):
        """get_safety_config() 返回 precip_threshold 和 visibility_threshold。"""
        mgr = ConfigManager(config_path=config_file)
        safety = mgr.get_safety_config()
        assert safety["precip_threshold"] == 50
        assert safety["visibility_threshold"] == 1000

    def test_get_light_path_config(self, config_file):
        """get_light_path_config() 返回光路参数。"""
        mgr = ConfigManager(config_path=config_file)
        lp = mgr.get_light_path_config()
        assert lp["count"] == 10
        assert lp["interval_km"] == 10

    def test_get_confidence_config(self, config_file):
        """get_confidence_config() 返回置信度映射。"""
        mgr = ConfigManager(config_path=config_file)
        conf = mgr.get_confidence_config()
        assert conf["high"] == [1, 2]
        assert conf["medium"] == [3, 4]
        assert conf["low"] == [5, 16]

    def test_get_output_config(self, config_file):
        """get_output_config() 返回输出路径配置。"""
        mgr = ConfigManager(config_path=config_file)
        out = mgr.get_output_config()
        assert "output_dir" in out
        assert "archive_dir" in out


# ==================== 错误处理 ====================


class TestConfigManagerErrors:
    """ConfigManager 错误处理测试。"""

    def test_file_not_found(self):
        """配置文件不存在 → 合理错误。"""
        with pytest.raises(FileNotFoundError):
            ConfigManager(config_path="/nonexistent/path.yaml")

    def test_invalid_yaml(self, tmp_path):
        """YAML 格式错误 → 合理错误提示。"""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{ invalid yaml: [")
        with pytest.raises(ValueError, match="YAML"):
            ConfigManager(config_path=str(bad_file))


# ==================== 默认值 ====================


class TestConfigManagerDefaults:
    """ConfigManager 默认值测试 — 缺少字段时使用 dataclass 默认值。"""

    def test_missing_fields_use_defaults(self, tmp_path):
        """最小化配置文件 → 缺失字段使用默认值。"""
        minimal = {"cache": {"db_path": "test.db"}}
        config_path = tmp_path / "minimal.yaml"
        config_path.write_text(yaml.dump(minimal))

        mgr = ConfigManager(config_path=str(config_path))
        cfg = mgr.config

        # 明确指定的值
        assert cfg.db_path == "test.db"
        # 使用默认值
        assert cfg.output_dir == "public/data"
        assert cfg.archive_dir == "archive"
        assert cfg.log_level == "INFO"
        assert cfg.forecast_days == 7
        assert cfg.light_path_count == 10
        assert cfg.light_path_interval_km == 10.0
        assert cfg.summary_mode == "rule"
        assert cfg.backtest_max_history_days == 365
