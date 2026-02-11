"""SnowTreePlugin 单元测试

测试用例来自 implementation-plans/module-05-scorer-simple.md
"""

from datetime import date

import pandas as pd
import pytest

from gmp.core.models import DataContext, Location, Viewpoint
from gmp.scorer.snow_tree import SnowTreePlugin


@pytest.fixture
def plugin():
    return SnowTreePlugin()


@pytest.fixture
def viewpoint():
    return Viewpoint(
        id="niubei",
        name="牛背山",
        location=Location(lat=29.6, lon=102.4, altitude=3660),
        capabilities=["snow_tree"],
        targets=[],
    )


def _make_context(viewpoint, **overrides):
    df = pd.DataFrame([overrides])
    return DataContext(date=date(2026, 2, 11), viewpoint=viewpoint, local_weather=df)


# ==================== check_trigger ====================


class TestCheckTrigger:
    def test_trigger_fresh_path(self, plugin):
        """近12h雪0.5cm, 距今6h, 当前晴 → True"""
        l1 = {
            "recent_snowfall_12h_cm": 0.5,
            "recent_snowfall_24h_cm": 0.5,
            "hours_since_last_snow": 6,
            "weather_code": 0,
            "cloud_cover_total": 20,
            "precip_prob": 10,
            "snowfall_duration_h_24h": 2,
            "subzero_hours_since_last_snow": 6,
            "max_temp_since_last_snow": -1.0,
        }
        assert plugin.check_trigger(l1) is True

    def test_trigger_retention_path(self, plugin):
        """近24h雪2cm, 时段4h, 零下10h, 最高0°C, 距今18h, 晴 → True"""
        l1 = {
            "recent_snowfall_12h_cm": 0.0,
            "recent_snowfall_24h_cm": 2.0,
            "hours_since_last_snow": 18,
            "snowfall_duration_h_24h": 4,
            "subzero_hours_since_last_snow": 10,
            "max_temp_since_last_snow": 0.0,
            "weather_code": 1,
            "cloud_cover_total": 30,
            "precip_prob": 15,
        }
        assert plugin.check_trigger(l1) is True

    def test_trigger_no_snow(self, plugin):
        """无近期降雪 → False"""
        l1 = {
            "recent_snowfall_12h_cm": 0.0,
            "recent_snowfall_24h_cm": 0.0,
            "hours_since_last_snow": 999,
            "weather_code": 0,
            "cloud_cover_total": 10,
            "precip_prob": 5,
        }
        assert plugin.check_trigger(l1) is False

    def test_trigger_not_clear(self, plugin):
        """有雪但当前不晴 → False"""
        l1 = {
            "recent_snowfall_12h_cm": 1.0,
            "hours_since_last_snow": 3,
            "weather_code": 61,  # 降雨
            "cloud_cover_total": 80,
            "precip_prob": 70,
        }
        assert plugin.check_trigger(l1) is False

    def test_trigger_retention_path_too_warm(self, plugin):
        """留存路径但最高温过高 → False"""
        l1 = {
            "recent_snowfall_12h_cm": 0.0,
            "recent_snowfall_24h_cm": 2.0,
            "hours_since_last_snow": 18,
            "snowfall_duration_h_24h": 4,
            "subzero_hours_since_last_snow": 10,
            "max_temp_since_last_snow": 3.0,  # > 1.5
            "weather_code": 0,
            "cloud_cover_total": 15,
            "precip_prob": 5,
        }
        assert plugin.check_trigger(l1) is False


# ==================== score ====================


class TestScore:
    def test_score_fresh_snow(self, plugin, viewpoint):
        """大雪3cm, 距今3h, 晴朗, 低温 → score≥80"""
        ctx = _make_context(
            viewpoint,
            recent_snowfall_24h_cm=3.0,
            snowfall_duration_h_24h=5,
            weather_code=0,
            cloud_cover_total=10,
            wind_speed_10m=5.0,
            hours_since_last_snow=3.0,
            max_temp_since_last_snow=-3.0,
            sunshine_hours_since_snow=0.0,
            max_wind_since_last_snow=10.0,
        )
        result = plugin.score(ctx)
        # snow: 3cm>=2.5 且 5h>=4 → 60
        # clear: code=0 且 cloud<=20 → 20
        # stable: wind 5 <12 → 20
        # age: 3h ≤3 → 0
        # temp: -3 ≤-2 → 0
        # sun: 0 → 0
        # wind: 10 ≤30 → 0
        # total = 60+20+20 = 100
        assert result.total_score >= 80
        assert result.status in ("Perfect", "Recommended")

    def test_score_sun_destruction(self, plugin, viewpoint):
        """大雪3cm, 距今19h, 暴晒8h, 升温2°C → score=46"""
        ctx = _make_context(
            viewpoint,
            recent_snowfall_24h_cm=3.0,
            snowfall_duration_h_24h=5,
            weather_code=0,
            cloud_cover_total=10,
            wind_speed_10m=5.0,
            hours_since_last_snow=19.0,
            max_temp_since_last_snow=2.1,
            sunshine_hours_since_snow=8.5,
            max_wind_since_last_snow=15.0,
        )
        result = plugin.score(ctx)
        # snow: 60, clear: 20, stable: 20
        # age ≤20 → 12, temp ≤2.5 → 12, sun >8 → 30, wind ≤30 → 0
        # total = 100 - 12 - 12 - 30 = 46
        assert result.total_score == 46
        assert result.status == "Not Recommended"

    def test_score_wind_destruction(self, plugin, viewpoint):
        """大雪3cm, 历史大风35km/h → 大幅扣分"""
        ctx = _make_context(
            viewpoint,
            recent_snowfall_24h_cm=3.0,
            snowfall_duration_h_24h=5,
            weather_code=0,
            cloud_cover_total=10,
            wind_speed_10m=5.0,
            hours_since_last_snow=3.0,
            max_temp_since_last_snow=-3.0,
            sunshine_hours_since_snow=0.0,
            max_wind_since_last_snow=35.0,
        )
        result = plugin.score(ctx)
        # snow: 60, clear: 20, stable: 20
        # age: 0, temp: 0, sun: 0, wind >30 → 20
        # total = 100 - 20 = 80
        assert result.total_score == 80
        assert result.breakdown["wind_deduction"]["score"] == -20

    def test_score_extreme_wind(self, plugin, viewpoint):
        """历史大风55km/h → -50 直接吹秃"""
        ctx = _make_context(
            viewpoint,
            recent_snowfall_24h_cm=3.0,
            snowfall_duration_h_24h=5,
            weather_code=0,
            cloud_cover_total=10,
            wind_speed_10m=5.0,
            hours_since_last_snow=3.0,
            max_temp_since_last_snow=-3.0,
            sunshine_hours_since_snow=0.0,
            max_wind_since_last_snow=55.0,
        )
        result = plugin.score(ctx)
        # total = 100 - 50 = 50
        assert result.total_score == 50
        assert result.breakdown["wind_deduction"]["score"] == -50


# ==================== dimensions ====================


class TestDimensions:
    def test_dimensions(self, plugin):
        assert plugin.dimensions() == [
            "snow_signal",
            "clear_weather",
            "stability",
            "age_deduction",
            "temp_deduction",
            "sun_deduction",
            "wind_deduction",
        ]
