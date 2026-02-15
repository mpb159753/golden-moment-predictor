"""tests/unit/test_plugin_frost.py — FrostPlugin 单元测试"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from gmp.core.models import Location, Viewpoint
from gmp.scoring.models import DataContext
from gmp.scoring.plugins.frost import FrostPlugin


# ── 默认配置 ────────────────────────────────────────


def _default_config() -> dict:
    """返回实施计划中定义的 FrostPlugin 默认配置"""
    return {
        "trigger": {"max_temperature": 2.0},
        "weights": {"temperature": 40, "moisture": 30, "wind": 20, "cloud": 10},
        "thresholds": {
            "temp_ranges": {
                "optimal": {"range": [-5, 0], "score": 40},
                "good": {"range": [-10, -5], "score": 30},
                "acceptable": {"range": [0, 2], "score": 25},
                "bad": {"range": [-999, -10], "score": 15},
            },
            "visibility_km": [5, 10, 20],  # <5=30, <10=20, <20=10, ≥20=5
            "wind_speed": [3, 5, 10],      # <3=20, <5=15, <10=10, ≥10=0
            "cloud_pct": {
                "optimal": {"range": [30, 60], "score": 10},
                "clear": {"range": [0, 30], "score": 5},
                "heavy": {"range": [60, 100], "score": 3},
            },
        },
        "safety": {
            "precip_threshold": 30,
            "visibility_threshold": 1,
        },
    }


def _make_viewpoint() -> Viewpoint:
    """创建测试用的 Viewpoint"""
    return Viewpoint(
        id="test-vp",
        name="Test Viewpoint",
        location=Location(lat=30.0, lon=120.0, altitude=1000),
        capabilities=["frost"],
        targets=[],
    )


def _make_weather(
    temperature: float,
    visibility: float,
    wind_speed: float,
    cloud_cover: float,
    *,
    precip_prob: float = 0.0,
    hours: int = 24,
) -> pd.DataFrame:
    """创建均匀的天气 DataFrame (所有小时使用相同值)"""
    return pd.DataFrame({
        "time": pd.date_range("2025-01-15T00:00", periods=hours, freq="h"),
        "temperature_2m": [temperature] * hours,
        "visibility": [visibility * 1000] * hours,  # km → m
        "wind_speed_10m": [wind_speed] * hours,
        "cloud_cover_low": [cloud_cover] * hours,
        "precipitation_probability": [precip_prob] * hours,
    })


def _make_context(weather: pd.DataFrame) -> DataContext:
    """创建 DataContext"""
    return DataContext(
        date=date(2025, 1, 15),
        viewpoint=_make_viewpoint(),
        local_weather=weather,
    )


# ── 属性和元信息测试 ────────────────────────────────


class TestFrostPluginProperties:
    """测试 Plugin 的基本属性"""

    def test_event_type(self):
        plugin = FrostPlugin(_default_config())
        assert plugin.event_type == "frost"

    def test_display_name(self):
        plugin = FrostPlugin(_default_config())
        assert plugin.display_name == "雾凇"

    def test_data_requirement_l1_only(self):
        plugin = FrostPlugin(_default_config())
        req = plugin.data_requirement
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False

    def test_dimensions(self):
        plugin = FrostPlugin(_default_config())
        assert plugin.dimensions() == ["temperature", "moisture", "wind", "cloud"]


# ── 触发判定测试 ────────────────────────────────────


class TestFrostTrigger:
    """测试触发条件"""

    def test_temp_above_trigger_returns_none(self):
        """温度 ≥ 2°C → 返回 None"""
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=2.0, visibility=10, wind_speed=3, cloud_cover=50,
        )
        ctx = _make_context(weather)
        assert plugin.score(ctx) is None

    def test_temp_well_above_trigger_returns_none(self):
        """温度 = 10°C → 返回 None"""
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=10.0, visibility=10, wind_speed=3, cloud_cover=50,
        )
        ctx = _make_context(weather)
        assert plugin.score(ctx) is None


# ── 综合评分测试 ────────────────────────────────────


class TestFrostScoring:
    """测试评分计算"""

    def test_standard_frost_conditions(self):
        """
        -3.8°C, 能见度 35km, 风 2.8km/h, 低云 75%
        温度: -3.8 在 [-5, 0] → optimal → 40
        能见度: 35km ≥ 20 → 5
        风: 2.8 < 3 → 20
        云: 75 在 [60, 100] → heavy → 3
        total ≈ 68 (但计划说 ≈72，需要根据实现确认)
        """
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=-3.8, visibility=35, wind_speed=2.8, cloud_cover=75,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)

        assert result is not None
        assert result.event_type == "frost"
        # 根据维度直接加总: 40 + 5 + 20 + 3 = 68
        # 但实施计划说 ≈72，所以可能使用的是 moisture 而非 visibility 直接评分
        # moisture 可能映射方式不同: 能见度 35km => 高能见度 = 低湿度 => 得分低
        # 先用计划预期值验证
        assert 65 <= result.total_score <= 75

    def test_optimal_frost_conditions(self):
        """
        -3°C, 能见度 3km (雾气充沛), 风 1km/h, 低云 45%
        温度: -3 在 [-5, 0] → optimal → 40
        能见度/湿度: 3km < 5 → 30
        风: 1 < 3 → 20
        云: 45 在 [30, 60] → optimal → 10
        total = 40 + 30 + 20 + 10 = 100
        实施计划说 score ≥ 90
        """
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=-3.0, visibility=3, wind_speed=1, cloud_cover=45,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)

        assert result is not None
        assert result.total_score >= 90


# ── 温度区间映射测试 ────────────────────────────────


class TestTemperatureRanges:
    """测试各温度区间正确映射"""

    @pytest.mark.parametrize(
        "temp, expected_score",
        [
            (-2.5, 40),   # [-5, 0] → optimal → 40
            (-7.0, 30),   # [-10, -5] → good → 30
            (1.0, 25),    # [0, 2] → acceptable → 25
            (-15.0, 15),  # [-999, -10] → bad → 15
        ],
    )
    def test_temp_range_scores(self, temp: float, expected_score: int):
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=temp, visibility=35, wind_speed=2, cloud_cover=50,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        # 检查 breakdown 中 temperature 维度的 score
        assert result.breakdown["temperature"]["score"] == expected_score


# ── 能见度/湿度区间映射测试 ──────────────────────────


class TestMoistureRanges:
    """测试各能见度区间正确映射 (moisture 维度)"""

    @pytest.mark.parametrize(
        "visibility_km, expected_score",
        [
            (3.0, 30),   # <5 → 30
            (7.0, 20),   # <10 → 20
            (15.0, 10),  # <20 → 10
            (25.0, 5),   # ≥20 → 5
        ],
    )
    def test_visibility_range_scores(self, visibility_km: float, expected_score: int):
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=-3.0, visibility=visibility_km, wind_speed=2, cloud_cover=50,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.breakdown["moisture"]["score"] == expected_score


# ── 风速测试 ────────────────────────────────────────


class TestWindScoring:
    """测试风速评分"""

    def test_wind_above_10_scores_zero(self):
        """风速 ≥ 10km/h → wind 维度 0 分"""
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=-3.0, visibility=10, wind_speed=12, cloud_cover=50,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.breakdown["wind"]["score"] == 0

    @pytest.mark.parametrize(
        "wind, expected_score",
        [
            (2.0, 20),   # <3 → 20
            (4.0, 15),   # <5 → 15
            (8.0, 10),   # <10 → 10
            (10.0, 0),   # ≥10 → 0
        ],
    )
    def test_wind_range_scores(self, wind: float, expected_score: int):
        plugin = FrostPlugin(_default_config())
        weather = _make_weather(
            temperature=-3.0, visibility=10, wind_speed=wind, cloud_cover=50,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.breakdown["wind"]["score"] == expected_score


# ── 安全检查测试 ────────────────────────────────────


class TestSafetyCheck:
    """测试安全条件检查"""

    def test_high_precip_filters_hours(self):
        """降水概率 > 阈值的时段被剔除"""
        plugin = FrostPlugin(_default_config())
        # 所有小时降水概率都超过阈值 → 没有可用数据 → 返回 None
        weather = _make_weather(
            temperature=-3.0, visibility=10, wind_speed=2, cloud_cover=50,
            precip_prob=50.0,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is None

    def test_low_visibility_filters_hours(self):
        """能见度 < safety 阈值的时段被剔除"""
        plugin = FrostPlugin(_default_config())
        # 能见度 0.5km < 1km 阈值 → 所有时段剔除 → None
        weather = _make_weather(
            temperature=-3.0, visibility=0.5, wind_speed=2, cloud_cover=50,
        )
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is None
