"""tests/unit/test_plugin_cloud_sea.py — CloudSeaPlugin 单元测试"""

from datetime import date

import pandas as pd
import pytest

from gmp.core.models import Location, ScoreResult, Viewpoint
from gmp.scoring.models import DataContext, DataRequirement


# ==================== helpers ====================

DEFAULT_CONFIG: dict = {
    "trigger": {},
    "weights": {"gap": 50, "density": 30, "wind": 20},
    "thresholds": {
        "gap_meters": [800, 500, 200],
        "gap_scores": [50, 40, 20, 10],
        "density_pct": [80, 50, 30],
        "density_scores": [30, 20, 10, 5],
        "wind_speed": [3, 5, 8],
        "wind_scores": [20, 15, 10, 5],
        "mid_cloud_penalty": [30, 60],
        "mid_cloud_factors": [1.0, 0.7, 0.3],
    },
}

SAFETY_CONFIG: dict = {
    "precip_threshold": 50,
    "visibility_threshold": 1000,
}


def _viewpoint(altitude: int = 2000) -> Viewpoint:
    """创建测试用观景台"""
    return Viewpoint(
        id="vp_test",
        name="测试观景台",
        location=Location(lat=30.0, lon=100.0, altitude=altitude),
        capabilities=["cloud_sea"],
        targets=[],
    )


def _weather_df(
    *,
    cloud_base: float = 1000.0,
    low_cloud: float = 75.0,
    mid_cloud: float = 5.0,
    wind: float = 2.8,
    precip_prob: float = 0.0,
    visibility: float = 10000.0,
    hours: int = 3,
) -> pd.DataFrame:
    """创建测试用天气 DataFrame，模拟关注时段的多行数据"""
    return pd.DataFrame(
        {
            "cloud_base_altitude": [cloud_base] * hours,
            "low_cloud_cover": [low_cloud] * hours,
            "mid_cloud_cover": [mid_cloud] * hours,
            "wind_speed_10m": [wind] * hours,
            "precipitation_probability": [precip_prob] * hours,
            "visibility": [visibility] * hours,
        }
    )


def _context(
    viewpoint: Viewpoint | None = None,
    weather: pd.DataFrame | None = None,
) -> DataContext:
    """创建测试用 DataContext"""
    return DataContext(
        date=date(2026, 1, 15),
        viewpoint=viewpoint if viewpoint is not None else _viewpoint(),
        local_weather=weather if weather is not None else _weather_df(),
    )


# ==================== Tests ====================


class TestCloudSeaPluginMetadata:
    """Plugin 元数据"""

    def test_event_type(self):
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        assert plugin.event_type == "cloud_sea"

    def test_display_name(self):
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        assert plugin.display_name == "云海"

    def test_data_requirement_l1_only(self):
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        req = plugin.data_requirement
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False

    def test_dimensions(self):
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        assert plugin.dimensions() == ["gap", "density", "mid_structure", "wind"]


class TestCloudSeaTrigger:
    """触发判定"""

    def test_cloud_above_viewpoint_returns_none(self):
        """云底高度 > 站点海拔 → 返回 None (未触发)"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # 站点海拔 2000m，云底 2500m → 云在头顶，不是云海
        ctx = _context(
            viewpoint=_viewpoint(altitude=2000),
            weather=_weather_df(cloud_base=2500.0),
        )
        result = plugin.score(ctx)
        assert result is None

    def test_cloud_below_viewpoint_triggers(self):
        """云底高度 < 站点海拔 → 触发评分"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # 站点海拔 2000m，云底 1000m → 云在脚下，云海！
        ctx = _context(
            viewpoint=_viewpoint(altitude=2000),
            weather=_weather_df(cloud_base=1000.0),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert isinstance(result, ScoreResult)


class TestCloudSeaScoring:
    """评分计算"""

    def test_typical_scenario(self):
        """Gap=1060m, 低云75%, 中云5%, 风2.8km/h → score≈90"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # 站点 2060m，云底 1000m → gap=1060m (>800 → gap_score=50)
        # 低云 75% (>50% → density_score=20)
        # 中云 5% (≤30% → factor=1.0)
        # 风 2.8km/h (<3 → wind_score=20)
        # Score = (50 + 20) × 1.0 + 20 = 90
        ctx = _context(
            viewpoint=_viewpoint(altitude=2060),
            weather=_weather_df(
                cloud_base=1000.0,
                low_cloud=75.0,
                mid_cloud=5.0,
                wind=2.8,
            ),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 90
        assert result.event_type == "cloud_sea"

    def test_perfect_score(self):
        """极大 Gap(>800) + 高密度(>80%) + 极低风(<3) + 低中云(≤30%) → 满分"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # gap=1500 (>800 → 50), density=90% (>80% → 30),
        # mid_cloud=10% (≤30% → factor=1.0), wind=1.0 (<3 → 20)
        # Score = (50 + 30) × 1.0 + 20 = 100
        ctx = _context(
            viewpoint=_viewpoint(altitude=2500),
            weather=_weather_df(
                cloud_base=1000.0,
                low_cloud=90.0,
                mid_cloud=10.0,
                wind=1.0,
            ),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 100

    def test_small_gap_low_score(self):
        """极小 Gap (<200m) → gap 维度低分"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # 站点 1150m，云底 1000m → gap=150m (≤200 → gap_score=10)
        # 低云 90% (>80% → density_score=30)
        # 中云 10% (≤30% → factor=1.0)
        # 风 1.0 (<3 → wind_score=20)
        # Score = (10 + 30) × 1.0 + 20 = 60
        ctx = _context(
            viewpoint=_viewpoint(altitude=1150),
            weather=_weather_df(
                cloud_base=1000.0,
                low_cloud=90.0,
                mid_cloud=10.0,
                wind=1.0,
            ),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 60

    def test_high_mid_cloud_heavy_penalty(self):
        """中云 >60% → factor=0.3 大幅扣分"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # gap=1000 (>800 → 50), density=90% (>80% → 30),
        # mid_cloud=70% (>60% → factor=0.3), wind=1.0 (<3 → 20)
        # Score = (50 + 30) × 0.3 + 20 = 24 + 20 = 44
        ctx = _context(
            viewpoint=_viewpoint(altitude=2000),
            weather=_weather_df(
                cloud_base=1000.0,
                low_cloud=90.0,
                mid_cloud=70.0,
                wind=1.0,
            ),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 44

    def test_moderate_mid_cloud_penalty(self):
        """中云 30-60% → factor=0.7"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # gap=1000 (>800 → 50), density=90% (>80% → 30),
        # mid_cloud=45% (>30% 且 ≤60% → factor=0.7), wind=1.0 (<3 → 20)
        # Score = (50 + 30) × 0.7 + 20 = 56 + 20 = 76
        ctx = _context(
            viewpoint=_viewpoint(altitude=2000),
            weather=_weather_df(
                cloud_base=1000.0,
                low_cloud=90.0,
                mid_cloud=45.0,
                wind=1.0,
            ),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 76


class TestCloudSeaSafety:
    """安全检查"""

    def test_high_precip_filters_out_rows(self):
        """关注时段有降水概率超阈值 → 剔除对应行"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        # 3行数据，其中2行降水概率超过 50% → 只剩1行有效
        weather = pd.DataFrame(
            {
                "cloud_base_altitude": [1000.0, 1000.0, 1000.0],
                "low_cloud_cover": [90.0, 90.0, 90.0],
                "mid_cloud_cover": [10.0, 10.0, 10.0],
                "wind_speed_10m": [1.0, 1.0, 1.0],
                "precipitation_probability": [0.0, 60.0, 80.0],
                "visibility": [10000.0, 10000.0, 10000.0],
            }
        )
        ctx = _context(
            viewpoint=_viewpoint(altitude=2000),
            weather=weather,
        )
        result = plugin.score(ctx)
        # 仍然应该能评分（有1行安全数据），但结果基于安全行
        assert result is not None

    def test_all_rows_unsafe_returns_none(self):
        """所有时段都不安全 → 返回 None"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        weather = pd.DataFrame(
            {
                "cloud_base_altitude": [1000.0, 1000.0],
                "low_cloud_cover": [90.0, 90.0],
                "mid_cloud_cover": [10.0, 10.0],
                "wind_speed_10m": [1.0, 1.0],
                "precipitation_probability": [60.0, 80.0],
                "visibility": [10000.0, 10000.0],
            }
        )
        ctx = _context(
            viewpoint=_viewpoint(altitude=2000),
            weather=weather,
        )
        result = plugin.score(ctx)
        assert result is None

    def test_low_visibility_filters_out_rows(self):
        """能见度低于阈值 → 剔除该行"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        plugin = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        weather = pd.DataFrame(
            {
                "cloud_base_altitude": [1000.0, 1000.0],
                "low_cloud_cover": [90.0, 90.0],
                "mid_cloud_cover": [10.0, 10.0],
                "wind_speed_10m": [1.0, 1.0],
                "precipitation_probability": [0.0, 0.0],
                "visibility": [500.0, 500.0],  # 低于 1000m
            }
        )
        ctx = _context(
            viewpoint=_viewpoint(altitude=2000),
            weather=weather,
        )
        result = plugin.score(ctx)
        assert result is None


class TestCloudSeaConfigDriven:
    """配置驱动"""

    def test_different_thresholds_change_score(self):
        """修改阈值后评分结果变化"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin

        # 使用更宽松的 gap 阈值：>500 即满分
        custom_config = {
            "trigger": {},
            "weights": {"gap": 50, "density": 30, "wind": 20},
            "thresholds": {
                "gap_meters": [500, 300, 100],  # 降低阈值
                "gap_scores": [50, 40, 20, 10],
                "density_pct": [80, 50, 30],
                "density_scores": [30, 20, 10, 5],
                "wind_speed": [3, 5, 8],
                "wind_scores": [20, 15, 10, 5],
                "mid_cloud_penalty": [30, 60],
                "mid_cloud_factors": [1.0, 0.7, 0.3],
            },
        }
        plugin_default = CloudSeaPlugin(DEFAULT_CONFIG, SAFETY_CONFIG)
        plugin_custom = CloudSeaPlugin(custom_config, SAFETY_CONFIG)

        # gap=400m: 默认阈值下 >200 → 20; 自定义阈值下 >300 → 40
        ctx = _context(
            viewpoint=_viewpoint(altitude=1400),
            weather=_weather_df(
                cloud_base=1000.0,
                low_cloud=90.0,
                mid_cloud=10.0,
                wind=1.0,
            ),
        )
        result_default = plugin_default.score(ctx)
        result_custom = plugin_custom.score(ctx)
        assert result_default is not None
        assert result_custom is not None
        assert result_custom.total_score > result_default.total_score
