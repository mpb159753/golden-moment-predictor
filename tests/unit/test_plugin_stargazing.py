"""tests/unit/test_plugin_stargazing.py — StargazingPlugin 单元测试"""

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from gmp.core.models import (
    Location,
    MoonStatus,
    ScoreResult,
    StargazingWindow,
    Viewpoint,
)
from gmp.scoring.models import DataContext, DataRequirement


# ========== helpers ==========


def _make_config(overrides: dict | None = None) -> dict:
    """构造标准测试配置（对应 engine_config.yaml → scoring.stargazing）"""
    cfg = {
        "trigger": {
            "max_night_cloud_cover": 70,
        },
        "base_optimal": 100,
        "base_good": 90,
        "base_partial": 70,
        "base_poor": 100,
        "cloud_penalty_factor": 0.8,
        "wind_thresholds": {
            "severe": {"speed": 40, "penalty": 30},
            "moderate": {"speed": 20, "penalty": 10},
        },
    }
    if overrides:
        _deep_update(cfg, overrides)
    return cfg


def _deep_update(d: dict, u: dict) -> dict:
    for k, v in u.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict):
            _deep_update(d[k], v)
        else:
            d[k] = v
    return d


def _make_viewpoint() -> Viewpoint:
    return Viewpoint(
        id="test_vp",
        name="测试观景台",
        location=Location(lat=29.6, lon=102.2, altitude=3666),
        capabilities=["stargazing"],
        targets=[],
    )


def _make_weather_df(
    hours: int = 24,
    cloud_cover: float = 10.0,
    wind_speed: float = 5.0,
) -> pd.DataFrame:
    """创建标准天气 DataFrame（夜间时段）"""
    base_time = datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc)
    rows = []
    for i in range(hours):
        t = base_time + pd.Timedelta(hours=i)
        rows.append(
            {
                "time": t,
                "temperature_2m": -5.0,
                "cloud_cover": cloud_cover,
                "wind_speed_10m": wind_speed,
            }
        )
    return pd.DataFrame(rows)


def _make_stargazing_window(
    quality: str = "optimal",
) -> StargazingWindow:
    """创建标准观星窗口"""
    return StargazingWindow(
        optimal_start=datetime(2026, 2, 10, 22, 0, tzinfo=timezone.utc),
        optimal_end=datetime(2026, 2, 11, 4, 0, tzinfo=timezone.utc),
        good_start=datetime(2026, 2, 10, 20, 0, tzinfo=timezone.utc),
        good_end=datetime(2026, 2, 11, 5, 0, tzinfo=timezone.utc),
        quality=quality,
    )


def _make_moon_status(phase: int = 5) -> MoonStatus:
    return MoonStatus(
        phase=phase,
        elevation=-30.0,
        moonrise=None,
        moonset=None,
    )


def _make_context(
    weather_df: pd.DataFrame,
    window: StargazingWindow | None = None,
    moon: MoonStatus | None = None,
) -> DataContext:
    return DataContext(
        date=date(2026, 2, 11),
        viewpoint=_make_viewpoint(),
        local_weather=weather_df,
        stargazing_window=window or _make_stargazing_window(),
        moon_status=moon or _make_moon_status(),
    )


# ========== tests ==========


class TestStargazingPluginProperties:
    """Plugin 基本属性"""

    def test_event_type(self):
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        assert plugin.event_type == "stargazing"

    def test_display_name(self):
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        assert plugin.display_name == "观星"

    def test_data_requirement_needs_astro(self):
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        assert plugin.data_requirement.needs_astro is True

    def test_dimensions(self):
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        dims = plugin.dimensions()
        assert "base" in dims
        assert "cloud" in dims
        assert "wind" in dims


class TestStargazingTrigger:
    """触发判定"""

    def test_high_cloud_cover_returns_none(self):
        """夜间总云量 ≥ 70% → None"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=75.0)
        ctx = _make_context(df)
        result = plugin.score(ctx)
        assert result is None

    def test_no_stargazing_window_returns_none(self):
        """stargazing_window 为 None → None"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=10.0)
        ctx = _make_context(df, window=None)
        # 手动把 window 设为 None
        ctx.stargazing_window = None
        result = plugin.score(ctx)
        assert result is None


class TestStargazingScoring:
    """评分计算"""

    def test_optimal_dark_night(self):
        """optimal 暗夜, 云量 2%, 风 2.8km/h → base=100 - 1.6 - 0 ≈ 98"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=2.0, wind_speed=2.8)
        window = _make_stargazing_window(quality="optimal")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        assert result.event_type == "stargazing"
        assert result.total_score == 98
        assert result.status == "Perfect"

    def test_good_window(self):
        """good 窗口, 云量 10%, 风 25km/h → base=90 - 8 - 10 = 72"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=10.0, wind_speed=25.0)
        window = _make_stargazing_window(quality="good")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        assert result.total_score == 72
        assert result.status == "Possible"

    def test_partial_window(self):
        """partial 窗口, 云量 30% → base=70 - 24 - 0 = 46"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=30.0, wind_speed=5.0)
        window = _make_stargazing_window(quality="partial")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        assert result.total_score == 46
        assert result.status == "Not Recommended"

    def test_poor_window_high_moon(self):
        """poor 窗口, 月相 95%, 云量 50% → base=100-76 - 40 ≈ 极低, clamp 到 0"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=50.0, wind_speed=5.0)
        window = _make_stargazing_window(quality="poor")
        moon = _make_moon_status(phase=95)
        ctx = _make_context(df, window=window, moon=moon)
        result = plugin.score(ctx)

        assert result is not None
        # base = 100 - 95 * 0.8 = 100 - 76 = 24
        # cloud_deduction = 50 * 0.8 = 40
        # score = 24 - 40 = -16 → clamp to 0
        assert result.total_score == 0


class TestStargazingWindDeduction:
    """风速扣分"""

    def test_severe_wind(self):
        """风速 > 40km/h → -30"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=2.0, wind_speed=45.0)
        window = _make_stargazing_window(quality="optimal")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        # base=100 - cloud_ded=1.6 - wind_ded=30 ≈ 68
        assert result.total_score == 68

    def test_moderate_wind(self):
        """风速 > 20km/h → -10"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=2.0, wind_speed=25.0)
        window = _make_stargazing_window(quality="optimal")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        # base=100 - cloud_ded=1.6 - wind_ded=10 ≈ 88
        assert result.total_score == 88

    def test_calm_wind(self):
        """风速 ≤ 20km/h → 0"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=2.0, wind_speed=15.0)
        window = _make_stargazing_window(quality="optimal")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        # base=100 - cloud_ded=1.6 - wind_ded=0 ≈ 98
        assert result.total_score == 98


class TestStargazingScoreClamping:
    """分数钳制"""

    def test_score_clamped_to_zero(self):
        """极端场景: 分数 clamp 到 0"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        # poor window + high moon + high cloud + severe wind
        df = _make_weather_df(cloud_cover=60.0, wind_speed=45.0)
        window = _make_stargazing_window(quality="poor")
        moon = _make_moon_status(phase=95)
        ctx = _make_context(df, window=window, moon=moon)
        result = plugin.score(ctx)

        assert result is not None
        assert result.total_score == 0

    def test_score_clamped_to_hundred(self):
        """分数不超过 100"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        # optimal + 0% cloud + calm wind → 100 - 0 - 0 = 100
        df = _make_weather_df(cloud_cover=0.0, wind_speed=0.0)
        window = _make_stargazing_window(quality="optimal")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        assert result.total_score == 100


class TestStargazingTimeWindow:
    """时间窗口输出"""

    def test_time_window_from_optimal(self):
        """主窗口应来自 optimal_start ~ optimal_end"""
        from gmp.scoring.plugins.stargazing import StargazingPlugin

        plugin = StargazingPlugin(_make_config())
        df = _make_weather_df(cloud_cover=2.0, wind_speed=2.8)
        window = _make_stargazing_window(quality="optimal")
        ctx = _make_context(df, window=window)
        result = plugin.score(ctx)

        assert result is not None
        assert result.time_window != ""
        assert "22:00" in result.time_window
        assert "04:00" in result.time_window
