"""CloudSeaPlugin 单元测试

测试用例来自 implementation-plans/module-05-scorer-simple.md
"""

from datetime import date

import pandas as pd
import pytest

from gmp.core.models import DataContext, Location, Viewpoint
from gmp.scorer.cloud_sea import CloudSeaPlugin


@pytest.fixture
def plugin():
    return CloudSeaPlugin()


@pytest.fixture
def viewpoint():
    return Viewpoint(
        id="niubei",
        name="牛背山",
        location=Location(lat=29.6, lon=102.4, altitude=3660),
        capabilities=["cloud_sea"],
        targets=[],
    )


def _make_context(viewpoint, **overrides):
    """构造 DataContext, 将 overrides 作为 DataFrame 的列."""
    df = pd.DataFrame([overrides])
    return DataContext(date=date(2026, 2, 11), viewpoint=viewpoint, local_weather=df)


# ==================== check_trigger ====================


class TestCheckTrigger:
    def test_trigger_positive(self, plugin):
        """云底2600m, 站点3660m → True"""
        l1 = {"cloud_base_altitude": 2600, "site_altitude": 3660}
        assert plugin.check_trigger(l1) is True

    def test_trigger_negative(self, plugin):
        """云底5000m, 站点3660m → False"""
        l1 = {"cloud_base_altitude": 5000, "site_altitude": 3660}
        assert plugin.check_trigger(l1) is False

    def test_trigger_equal(self, plugin):
        """云底 == 站点 → False (要求严格 <)"""
        l1 = {"cloud_base_altitude": 3660, "site_altitude": 3660}
        assert plugin.check_trigger(l1) is False

    def test_trigger_default(self, plugin):
        """无云底数据 → 默认 inf, False"""
        l1 = {"site_altitude": 3660}
        assert plugin.check_trigger(l1) is False


# ==================== score ====================


class TestScore:
    def test_score_perfect(self, plugin, viewpoint):
        """Gap1060m, 低云90%, 中云15%, 风2.8 → 100, Perfect"""
        ctx = _make_context(
            viewpoint,
            cloud_base_altitude=2600,
            cloud_cover_low=90,
            cloud_cover_mid=15,
            wind_speed_10m=2.8,
        )
        result = plugin.score(ctx)
        assert result.total_score == 100
        assert result.status == "Perfect"
        # 验证 breakdown
        assert result.breakdown["gap"]["score"] == 50
        assert result.breakdown["density"]["score"] == 30
        assert result.breakdown["mid_structure"]["factor"] == 1.0
        assert result.breakdown["wind"]["score"] == 20

    def test_score_thick_mid_cloud(self, plugin, viewpoint):
        """Gap500m, 低云80%, 中云65% → 0.3 因子, 大幅降低"""
        ctx = _make_context(
            viewpoint,
            cloud_base_altitude=3160,  # gap=500
            cloud_cover_low=80,
            cloud_cover_mid=65,
            wind_speed_10m=5,
        )
        result = plugin.score(ctx)
        # (40+20)*0.3 + 20 = 18+20 = 38
        assert result.total_score < 50
        assert result.status == "Not Recommended"

    def test_score_high_wind(self, plugin, viewpoint):
        """Gap800m, 低云85%, 中云20%, 风25km/h → 风速扣分"""
        ctx = _make_context(
            viewpoint,
            cloud_base_altitude=2860,  # gap=800 (恰好 800, 不满足 >800, 属于 >500 档 → 40)
            cloud_cover_low=85,
            cloud_cover_mid=20,
            wind_speed_10m=25,
        )
        result = plugin.score(ctx)
        # gap=800 → 属于 >500 档 → 40, density >80 → 30, mid ≤30 → 1.0
        # wind: 25km/h → 0 分
        # total = (40+30)*1.0 + 0 = 70
        assert result.total_score == 70
        assert result.breakdown["wind"]["score"] == 0

    def test_score_small_gap(self, plugin, viewpoint):
        """Gap100m → gap=10分"""
        ctx = _make_context(
            viewpoint,
            cloud_base_altitude=3560,  # gap=100
            cloud_cover_low=60,
            cloud_cover_mid=25,
            wind_speed_10m=8,
        )
        result = plugin.score(ctx)
        # gap <=200 but >0 → 10
        assert result.breakdown["gap"]["score"] == 10


# ==================== dimensions ====================


class TestDimensions:
    def test_dimensions(self, plugin):
        assert plugin.dimensions() == ["gap", "density", "mid_structure", "wind"]
