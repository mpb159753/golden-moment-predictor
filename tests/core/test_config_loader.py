"""测试 gmp.core.config_loader 配置加载器"""

import os
from pathlib import Path

import pytest

from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.core.exceptions import ViewpointNotFoundError
from gmp.core.models import Location, Target, Viewpoint

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 测试 fixture 目录
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

# 实际配置目录
CONFIG_DIR = PROJECT_ROOT / "gmp" / "config"


class TestViewpointConfig:
    def test_load_viewpoint_yaml(self):
        """YAML → Viewpoint 对象正确映射"""
        vc = ViewpointConfig()
        vc.load(FIXTURES_DIR)

        vp = vc.get("test_viewpoint")
        assert isinstance(vp, Viewpoint)
        assert vp.id == "test_viewpoint"
        assert vp.name == "测试观景台"
        assert isinstance(vp.location, Location)
        assert vp.location.lat == 29.75
        assert vp.location.lon == 102.35
        assert vp.location.altitude == 3660
        assert "sunrise" in vp.capabilities
        assert len(vp.targets) == 2

        # 验证 Target 解析
        primary = vp.targets[0]
        assert isinstance(primary, Target)
        assert primary.name == "测试目标A"
        assert primary.weight == "primary"
        assert primary.applicable_events is None

        secondary = vp.targets[1]
        assert secondary.weight == "secondary"
        assert secondary.applicable_events == ["sunset"]

    def test_load_actual_viewpoint_config(self):
        """加载实际的 niubei_gongga.yaml 配置"""
        vc = ViewpointConfig()
        vc.load(CONFIG_DIR / "viewpoints")

        vp = vc.get("niubei_gongga")
        assert vp.name == "牛背山"
        assert vp.location.altitude == 3660
        assert "cloud_sea" in vp.capabilities
        assert len(vp.targets) == 2
        assert vp.targets[0].name == "贡嘎主峰"
        assert vp.targets[0].altitude == 7556

    def test_viewpoint_not_found(self):
        """查询不存在 ID 抛出异常"""
        vc = ViewpointConfig()
        vc.load(FIXTURES_DIR)

        with pytest.raises(ViewpointNotFoundError) as exc_info:
            vc.get("nonexistent_viewpoint")

        assert exc_info.value.viewpoint_id == "nonexistent_viewpoint"

    def test_list_all_pagination(self):
        """分页逻辑正确"""
        vc = ViewpointConfig()
        vc.load(FIXTURES_DIR)

        result = vc.list_all(page=1, page_size=10)
        assert "viewpoints" in result
        assert "pagination" in result
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["total"] >= 1
        assert result["pagination"]["total_pages"] >= 1
        assert len(result["viewpoints"]) <= 10

        # 所有返回的都是 Viewpoint 实例
        for vp in result["viewpoints"]:
            assert isinstance(vp, Viewpoint)

    def test_list_all_pagination_boundary(self):
        """分页边界条件"""
        vc = ViewpointConfig()
        vc.load(FIXTURES_DIR)

        # 每页 1 个
        result = vc.list_all(page=1, page_size=1)
        assert len(result["viewpoints"]) == 1
        assert result["pagination"]["total_pages"] >= 1

        # 超出范围的页码返回空列表
        result = vc.list_all(page=999, page_size=10)
        assert len(result["viewpoints"]) == 0

    def test_load_empty_directory(self, tmp_path):
        """加载空目录不报错"""
        vc = ViewpointConfig()
        vc.load(tmp_path)

        result = vc.list_all()
        assert result["pagination"]["total"] == 0

    def test_load_nonexistent_directory(self):
        """加载不存在的目录不报错"""
        vc = ViewpointConfig()
        vc.load("/nonexistent/path")

        result = vc.list_all()
        assert result["pagination"]["total"] == 0


class TestEngineConfig:
    def test_load_engine_config(self):
        """engine_config.yaml 正确加载"""
        config = EngineConfig.from_yaml(CONFIG_DIR / "engine_config.yaml")

        # 缓存配置
        assert config.memory_cache_ttl_seconds == 300
        assert config.db_cache_ttl_seconds == 3600
        assert config.db_path == "db/gmp_cache.db"

        # 坐标精度
        assert config.coord_precision == 2

        # 安全阈值
        assert config.precip_threshold == 50.0
        assert config.visibility_threshold == 1000
        assert config.local_cloud_threshold == 30
        assert config.target_cloud_threshold == 30
        assert config.light_path_threshold == 50
        assert config.wind_threshold == 20
        assert config.frost_temp_threshold == 2.0

        # 光路计算
        assert config.light_path_count == 10
        assert config.light_path_interval_km == 10

        # 评分权重
        assert config.golden_score_weights["light_path"] == 35
        assert config.golden_score_weights["target_visible"] == 40
        assert config.golden_score_weights["local_clear"] == 25

        # 摘要与分页
        assert config.summary_mode == "rule"
        assert config.default_page_size == 20
        assert config.max_page_size == 100

    def test_engine_config_defaults(self):
        """未指定字段使用 dataclass 默认值"""
        config = EngineConfig()
        assert config.db_path == "gmp_cache.db"
        assert config.memory_cache_ttl_seconds == 300
        assert config.coord_precision == 2
        assert config.summary_mode == "rule"

    def test_engine_config_missing_file(self, tmp_path):
        """加载不存在的文件返回默认配置"""
        config = EngineConfig.from_yaml(tmp_path / "nonexistent.yaml")
        assert config.db_path == "gmp_cache.db"
        assert config.precip_threshold == 50.0

    def test_engine_config_partial_yaml(self, tmp_path):
        """部分 YAML 加载，其余字段使用默认值"""
        partial_yaml = tmp_path / "partial.yaml"
        partial_yaml.write_text(
            "cache:\n  memory_ttl_seconds: 600\ncoord_precision: 3\n",
            encoding="utf-8",
        )
        config = EngineConfig.from_yaml(partial_yaml)
        assert config.memory_cache_ttl_seconds == 600
        assert config.coord_precision == 3
        # 未指定字段保持默认
        assert config.precip_threshold == 50.0
        assert config.default_page_size == 20
