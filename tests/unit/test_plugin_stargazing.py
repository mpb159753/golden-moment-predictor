"""StargazingPlugin 单元测试

测试用例来源: implementation-plans/module-06-scorer-complex.md
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from gmp.core.models import (
    DataContext,
    Location,
    MoonStatus,
    StargazingWindow,
    SunEvents,
    Viewpoint,
)
from gmp.scorer.stargazing import StargazingPlugin


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def plugin() -> StargazingPlugin:
    return StargazingPlugin()


@pytest.fixture
def viewpoint() -> Viewpoint:
    return Viewpoint(
        id="niubei",
        name="牛背山",
        location=Location(lat=29.83, lon=102.35, altitude=3660),
        capabilities=["stargazing"],
    )


def _make_night_weather_df(
    night_cloud: float = 3.0,
    night_wind: float = 2.8,
) -> pd.DataFrame:
    """构建含夜间小时 (20-05) 的天气 DataFrame."""
    rows = []
    for hour in range(24):
        if hour >= 20 or hour <= 5:
            rows.append({
                "forecast_hour": hour,
                "cloud_cover_total": night_cloud,
                "wind_speed_10m": night_wind,
            })
        else:
            rows.append({
                "forecast_hour": hour,
                "cloud_cover_total": 30,  # 白天云量不影响
                "wind_speed_10m": 5.0,
            })
    return pd.DataFrame(rows)


def _make_context(
    viewpoint: Viewpoint,
    *,
    quality: str = "optimal",
    moon_phase: int = 5,
    night_cloud: float = 3.0,
    night_wind: float = 2.8,
) -> DataContext:
    """快速构建观星 DataContext."""
    return DataContext(
        date=date(2026, 2, 11),
        viewpoint=viewpoint,
        local_weather=_make_night_weather_df(night_cloud, night_wind),
        stargazing_window=StargazingWindow(
            optimal_start=datetime(2026, 2, 11, 19, 55),
            optimal_end=datetime(2026, 2, 12, 3, 15),
            quality=quality,
        ),
        moon_status=MoonStatus(
            phase=moon_phase,
            elevation=-30.0,
            moonrise=datetime(2026, 2, 12, 3, 15),
            moonset=datetime(2026, 2, 11, 13, 40),
        ),
    )


# ======================================================================
# check_trigger 测试
# ======================================================================


class TestCheckTrigger:
    """StargazingPlugin.check_trigger 测试."""

    def test_trigger_positive(self, plugin: StargazingPlugin):
        """夜间云量20% < 70% → True."""
        assert plugin.check_trigger({"night_cloud_cover": 20}) is True

    def test_trigger_overcast(self, plugin: StargazingPlugin):
        """夜间云量75% ≥ 70% → False."""
        assert plugin.check_trigger({"night_cloud_cover": 75}) is False

    def test_trigger_boundary_69(self, plugin: StargazingPlugin):
        """夜间云量69% < 70% → True."""
        assert plugin.check_trigger({"night_cloud_cover": 69}) is True

    def test_trigger_boundary_70(self, plugin: StargazingPlugin):
        """夜间云量70% 不 < 70% → False."""
        assert plugin.check_trigger({"night_cloud_cover": 70}) is False

    def test_trigger_default(self, plugin: StargazingPlugin):
        """无 night_cloud_cover 字段，默认100 → False."""
        assert plugin.check_trigger({}) is False


# ======================================================================
# score 测试
# ======================================================================


class TestScore:
    """StargazingPlugin.score 评分测试."""

    def test_score_perfect(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """设计文档示例: optimal暗夜, 云量3%, 风2.8 → score=98, Perfect.

        Base=100, 云量扣分=round(3*0.8)=2, 风速≤20无扣分
        Total = 100 - 2 - 0 = 98
        """
        ctx = _make_context(
            viewpoint,
            quality="optimal",
            moon_phase=5,
            night_cloud=3.0,
            night_wind=2.8,
        )
        result = plugin.score(ctx)

        assert result.total_score == 98
        assert result.status == "Perfect"
        assert result.breakdown["base"]["score"] == 100
        assert result.breakdown["cloud"]["score"] == -2
        assert result.breakdown["wind"]["score"] == 0

    def test_score_good(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """good窗口, 云量10%, 微风 → 82 ≤ score ≤ 90.

        Base=90, 云量扣分=round(10*0.8)=8, 风速≤20无扣分
        Total = 90 - 8 - 0 = 82
        """
        ctx = _make_context(
            viewpoint,
            quality="good",
            moon_phase=30,
            night_cloud=10.0,
            night_wind=5.0,
        )
        result = plugin.score(ctx)

        assert 82 <= result.total_score <= 90
        assert result.total_score == 82
        assert result.breakdown["base"]["score"] == 90

    def test_score_poor(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """poor(满月100%), 云量50% → score ≤ 30.

        Base = max(0, 100 - 100*0.8) = 20
        云量扣分 = round(50*0.8) = 40
        Total = max(0, 20 - 40 - 0) = 0
        """
        ctx = _make_context(
            viewpoint,
            quality="poor",
            moon_phase=100,
            night_cloud=50.0,
            night_wind=5.0,
        )
        result = plugin.score(ctx)

        assert result.total_score <= 30
        assert result.total_score == 0

    def test_wind_penalty_strong(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """optimal, 云量0%, 风45km/h → 扣30分.

        Base=100, 云量扣分=0, 风速扣分=30
        Total = 100 - 0 - 30 = 70
        """
        ctx = _make_context(
            viewpoint,
            quality="optimal",
            moon_phase=5,
            night_cloud=0.0,
            night_wind=45.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 70
        assert result.breakdown["wind"]["score"] == -30

    def test_moderate_wind(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """optimal, 云量0%, 风25km/h → 扣10分.

        Base=100, 云量扣分=0, 风速扣分=10
        Total = 100 - 0 - 10 = 90
        """
        ctx = _make_context(
            viewpoint,
            quality="optimal",
            moon_phase=5,
            night_cloud=0.0,
            night_wind=25.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 90
        assert result.breakdown["wind"]["score"] == -10

    def test_partial_quality(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """partial窗口, 云量5%, 微风 → base=70.

        Base=70, 云量扣分=round(5*0.8)=4, 风速0
        Total = 70 - 4 - 0 = 66
        """
        ctx = _make_context(
            viewpoint,
            quality="partial",
            moon_phase=60,
            night_cloud=5.0,
            night_wind=3.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 66
        assert result.breakdown["base"]["score"] == 70

    def test_no_stargazing_window(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """无观星窗口 → 降级为 poor 计算."""
        ctx = DataContext(
            date=date(2026, 2, 11),
            viewpoint=viewpoint,
            local_weather=_make_night_weather_df(5.0, 3.0),
            stargazing_window=None,
            moon_status=MoonStatus(phase=80, elevation=-10.0),
        )
        result = plugin.score(ctx)

        # Base = max(0, 100 - 80*0.8) = 36
        # Cloud = round(5*0.8) = 4
        # Total = 36 - 4 - 0 = 32
        assert result.total_score == 32

    def test_score_clamped_at_zero(self, plugin: StargazingPlugin, viewpoint: Viewpoint):
        """极端情况: 分数不会为负."""
        ctx = _make_context(
            viewpoint,
            quality="poor",
            moon_phase=100,
            night_cloud=90.0,
            night_wind=50.0,
        )
        result = plugin.score(ctx)
        assert result.total_score >= 0


# ======================================================================
# 基准分测试
# ======================================================================


class TestBaseScore:
    """验证四种窗口质量的基准分."""

    @pytest.mark.parametrize(
        "quality,expected_base",
        [
            ("optimal", 100),
            ("good", 90),
            ("partial", 70),
        ],
    )
    def test_fixed_quality_base(
        self, plugin: StargazingPlugin, viewpoint: Viewpoint, quality: str, expected_base: int
    ):
        ctx = _make_context(viewpoint, quality=quality, night_cloud=0, night_wind=0)
        result = plugin.score(ctx)
        assert result.breakdown["base"]["score"] == expected_base

    @pytest.mark.parametrize(
        "moon_phase,expected_base",
        [
            (0, 100),     # 新月: 100 - 0 = 100
            (50, 60),     # 半月: 100 - 40 = 60
            (100, 20),    # 满月: 100 - 80 = 20
        ],
    )
    def test_poor_quality_base(
        self, plugin: StargazingPlugin, viewpoint: Viewpoint, moon_phase: int, expected_base: int
    ):
        ctx = _make_context(
            viewpoint, quality="poor", moon_phase=moon_phase, night_cloud=0, night_wind=0
        )
        result = plugin.score(ctx)
        assert result.breakdown["base"]["score"] == expected_base


class TestDimensions:
    def test_dimensions(self, plugin: StargazingPlugin):
        assert plugin.dimensions() == ["base", "cloud", "wind"]


class TestEventType:
    def test_event_type(self, plugin: StargazingPlugin):
        assert plugin.event_type == "stargazing"

    def test_display_name(self, plugin: StargazingPlugin):
        assert plugin.display_name == "观星"
