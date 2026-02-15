"""tests/unit/test_scoring_models.py — DataRequirement / DataContext 单元测试"""

from datetime import date

import pandas as pd
import pytest

from gmp.core.models import (
    Location,
    MoonStatus,
    StargazingWindow,
    SunEvents,
    Viewpoint,
)
from gmp.scoring.models import DataContext, DataRequirement


# ==================== DataRequirement 测试 ====================


class TestDataRequirement:
    """DataRequirement 默认值与构造测试"""

    def test_default_values(self):
        """所有字段使用默认值构造"""
        req = DataRequirement()
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False
        assert req.past_hours == 0
        assert req.season_months is None

    def test_season_months_none_means_all_year(self):
        """season_months=None 表示全年适用"""
        req = DataRequirement()
        assert req.season_months is None

    def test_custom_values(self):
        """自定义字段值"""
        req = DataRequirement(
            needs_l2_target=True,
            needs_l2_light_path=True,
            needs_astro=True,
            past_hours=24,
            season_months=[10, 11, 12, 1, 2],
        )
        assert req.needs_l2_target is True
        assert req.needs_l2_light_path is True
        assert req.needs_astro is True
        assert req.past_hours == 24
        assert req.season_months == [10, 11, 12, 1, 2]


# ==================== DataContext 测试 ====================


class TestDataContext:
    """DataContext 构建测试"""

    @pytest.fixture
    def viewpoint(self):
        """最小 Viewpoint fixture"""
        return Viewpoint(
            id="niubeishan",
            name="牛背山",
            location=Location(lat=29.6, lon=102.3, altitude=3660),
            capabilities=["sunrise", "cloud_sea"],
            targets=[],
        )

    @pytest.fixture
    def local_weather(self):
        """最小天气 DataFrame fixture"""
        return pd.DataFrame({"temperature_2m": [5.0, 6.0]})

    def test_required_fields(self, viewpoint, local_weather):
        """必填字段正确设置"""
        ctx = DataContext(
            date=date(2026, 2, 11),
            viewpoint=viewpoint,
            local_weather=local_weather,
        )
        assert ctx.date == date(2026, 2, 11)
        assert ctx.viewpoint is viewpoint
        assert len(ctx.local_weather) == 2

    def test_optional_fields_default_none(self, viewpoint, local_weather):
        """可选字段默认 None"""
        ctx = DataContext(
            date=date(2026, 2, 11),
            viewpoint=viewpoint,
            local_weather=local_weather,
        )
        assert ctx.sun_events is None
        assert ctx.moon_status is None
        assert ctx.stargazing_window is None
        assert ctx.target_weather is None
        assert ctx.light_path_weather is None

    def test_data_freshness_default_fresh(self, viewpoint, local_weather):
        """data_freshness 默认 'fresh'"""
        ctx = DataContext(
            date=date(2026, 2, 11),
            viewpoint=viewpoint,
            local_weather=local_weather,
        )
        assert ctx.data_freshness == "fresh"

    def test_data_freshness_custom(self, viewpoint, local_weather):
        """data_freshness 可设为其他值"""
        ctx = DataContext(
            date=date(2026, 2, 11),
            viewpoint=viewpoint,
            local_weather=local_weather,
            data_freshness="degraded",
        )
        assert ctx.data_freshness == "degraded"
