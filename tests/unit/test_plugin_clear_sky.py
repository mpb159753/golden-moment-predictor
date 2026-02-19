"""tests/unit/test_plugin_clear_sky.py — ClearSkyPlugin 单元测试"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from gmp.core.models import Location, Viewpoint
from gmp.scoring.models import DataContext
from gmp.scoring.plugins.clear_sky import ClearSkyPlugin


# ── 默认配置 ────────────────────────────────────────


def _default_config() -> dict:
    """返回实施计划中定义的 ClearSkyPlugin 默认配置"""
    return {
        "trigger": {"max_cloud_cover": 80},
        "weights": {
            "cloud_cover": 50,
            "precipitation": 25,
            "visibility": 25,
        },
        "thresholds": {
            "cloud_pct": [10, 30, 50, 70],
            "cloud_scores": [50, 40, 25, 10, 0],
            "precip_pct": [10, 30, 50],
            "precip_scores": [25, 20, 10, 0],
            "visibility_km": [30, 15, 5],
            "visibility_scores": [25, 20, 10, 5],
        },
    }


def _make_viewpoint() -> Viewpoint:
    """创建测试用的 Viewpoint"""
    return Viewpoint(
        id="test-vp",
        name="Test Viewpoint",
        location=Location(lat=30.0, lon=120.0, altitude=3000),
        capabilities=["clear_sky"],
        targets=[],
    )


def _make_weather(
    cloud_cover: float,
    precip_prob: float = 0.0,
    visibility_km: float = 30.0,
    *,
    hours: int = 24,
) -> pd.DataFrame:
    """创建均匀的天气 DataFrame (所有小时使用相同值)"""
    return pd.DataFrame({
        "time": pd.date_range("2025-06-15T00:00", periods=hours, freq="h"),
        "cloud_cover": [cloud_cover] * hours,
        "precipitation_probability": [precip_prob] * hours,
        "visibility": [visibility_km * 1000] * hours,  # km → m
    })


def _make_context(weather: pd.DataFrame) -> DataContext:
    """创建 DataContext"""
    return DataContext(
        date=date(2025, 6, 15),
        viewpoint=_make_viewpoint(),
        local_weather=weather,
    )


# ── 属性和元信息测试 ────────────────────────────────


class TestClearSkyPluginProperties:
    """测试 Plugin 的基本属性"""

    def test_event_type(self):
        plugin = ClearSkyPlugin(_default_config())
        assert plugin.event_type == "clear_sky"

    def test_display_name(self):
        plugin = ClearSkyPlugin(_default_config())
        assert plugin.display_name == "晴天"

    def test_data_requirement_l1_only(self):
        plugin = ClearSkyPlugin(_default_config())
        req = plugin.data_requirement
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False

    def test_dimensions(self):
        plugin = ClearSkyPlugin(_default_config())
        assert plugin.dimensions() == ["cloud_cover", "precipitation", "visibility"]


# ── 触发判定测试 ────────────────────────────────────


class TestClearSkyTrigger:
    """测试触发条件: 平均总云量 ≥ 80% → 返回 None"""

    def test_overcast_returns_none(self):
        """云量 85% → 返回 None (未触发)"""
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=85)
        ctx = _make_context(weather)
        assert plugin.score(ctx) is None

    def test_exactly_at_trigger_returns_none(self):
        """云量 = 80% → 返回 None (边界)"""
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=80)
        ctx = _make_context(weather)
        assert plugin.score(ctx) is None

    def test_below_trigger_returns_result(self):
        """云量 79% → 返回评分结果"""
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=79)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None


# ── 综合评分测试 ────────────────────────────────────


class TestClearSkyScoring:
    """测试评分计算"""

    def test_clear_sky_high_score(self):
        """晴天（云量 10%）→ 高分 (~90+)"""
        plugin = ClearSkyPlugin(_default_config())
        # 云量 10% → cloud_scores: 10 在阈值 [10,30,50,70] 中,
        #   10 <= 10 → 第一档 cloud_scores[0]=50
        # 降水 0% → precip_scores: 0 < 10 → 第一档 25
        # 能见度 30km → vis 30*1000=30000m, 30km >= 30 → 第一档 25
        # total = 50+25+25 = 100
        weather = _make_weather(cloud_cover=10, precip_prob=0, visibility_km=30)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score >= 90

    def test_partly_cloudy_medium_score(self):
        """多云（云量 50%）→ 中等分 (~40-60)"""
        plugin = ClearSkyPlugin(_default_config())
        # 云量 50% → 在 [10,30,50,70]: 50 <= 50 → 第三档 cloud_scores[2]=25
        # 降水 20% → 在 [10,30,50]: 20 <= 30 → 第二档 precip_scores[1]=20
        # 能见度 15km → 15 >= 15 → 第二档 visibility_scores[1]=20
        # total = 25+20+20 = 65 (但我们要的范围 40-60, 需要调一下条件)
        weather = _make_weather(cloud_cover=50, precip_prob=30, visibility_km=10)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert 30 <= result.total_score <= 60

    def test_heavy_rain_low_score(self):
        """暴雨（降水概率 90%）→ 低分"""
        plugin = ClearSkyPlugin(_default_config())
        # 云量 70% (刚触发)
        # 降水 90% → 90 > 50 → 第四档 precip_scores[3]=0
        # 能见度 3km → 3 < 5 → 第四档 visibility_scores[3]=5
        weather = _make_weather(cloud_cover=70, precip_prob=90, visibility_km=3)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score <= 20

    def test_perfect_conditions_max_score(self):
        """完美条件（0% 云量 + 0% 降水 + 高能见度）→ 100 分"""
        plugin = ClearSkyPlugin(_default_config())
        # 云量 0% → 0 < 10 → 第一档 cloud_scores[0]=50
        # 降水 0% → 0 < 10 → 第一档 precip_scores[0]=25
        # 能见度 50km → 50 >= 30 → 第一档 visibility_scores[0]=25
        # total = 50+25+25 = 100
        weather = _make_weather(cloud_cover=0, precip_prob=0, visibility_km=50)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 100


# ── 维度细分评分测试 ────────────────────────────────


class TestCloudCoverDimension:
    """测试云量维度的阶梯评分"""

    @pytest.mark.parametrize(
        "cloud_pct, expected_score",
        [
            (5, 50),    # < 10 → 50
            (10, 50),   # <= 10 → 50
            (20, 40),   # <= 30 → 40
            (45, 25),   # <= 50 → 25
            (60, 10),   # <= 70 → 10
            (75, 0),    # > 70 → 0
        ],
    )
    def test_cloud_cover_scores(self, cloud_pct: float, expected_score: int):
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=cloud_pct, precip_prob=0, visibility_km=50)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        if result is None:
            # cloud_pct >= 80 triggers None
            assert cloud_pct >= 80
            return
        assert result.breakdown["cloud_cover"]["score"] == expected_score


class TestPrecipDimension:
    """测试降水维度的阶梯评分"""

    @pytest.mark.parametrize(
        "precip_pct, expected_score",
        [
            (5, 25),    # < 10 → 25
            (10, 25),   # <= 10 → 25
            (20, 20),   # <= 30 → 20
            (40, 10),   # <= 50 → 10
            (60, 0),    # > 50 → 0
        ],
    )
    def test_precip_scores(self, precip_pct: float, expected_score: int):
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=10, precip_prob=precip_pct, visibility_km=50)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.breakdown["precipitation"]["score"] == expected_score


class TestVisibilityDimension:
    """测试能见度维度的阶梯评分"""

    @pytest.mark.parametrize(
        "vis_km, expected_score",
        [
            (40, 25),   # >= 30 → 25
            (30, 25),   # >= 30 → 25
            (20, 20),   # >= 15 → 20
            (10, 10),   # >= 5 → 10
            (3, 5),     # < 5 → 5
        ],
    )
    def test_visibility_scores(self, vis_km: float, expected_score: int):
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=10, precip_prob=0, visibility_km=vis_km)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.breakdown["visibility"]["score"] == expected_score


# ── ScoreResult 结构测试 ────────────────────────────


class TestScoreResultStructure:
    """测试返回的 ScoreResult 结构"""

    def test_result_has_correct_event_type(self):
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=10)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.event_type == "clear_sky"

    def test_result_has_breakdown_keys(self):
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=10)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert set(result.breakdown.keys()) == {
            "cloud_cover", "precipitation", "visibility",
        }

    def test_breakdown_has_score_max_detail(self):
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=10)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        for dim_name, dim_data in result.breakdown.items():
            assert "score" in dim_data
            assert "max" in dim_data
            assert "detail" in dim_data

    def test_result_has_valid_status(self):
        plugin = ClearSkyPlugin(_default_config())
        weather = _make_weather(cloud_cover=0, precip_prob=0, visibility_km=50)
        ctx = _make_context(weather)
        result = plugin.score(ctx)
        assert result is not None
        assert result.status in ("Perfect", "Recommended", "Possible", "Not Recommended")
