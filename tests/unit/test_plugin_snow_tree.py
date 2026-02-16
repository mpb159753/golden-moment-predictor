"""tests/unit/test_plugin_snow_tree.py — SnowTreePlugin 单元测试"""

from datetime import date, datetime, timezone
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from gmp.core.models import Viewpoint, Location, ScoreResult, Target
from gmp.scoring.models import DataContext, DataRequirement


# ========== helpers ==========


def _make_config(overrides: dict | None = None) -> dict:
    """构造标准测试配置（对应 engine_config.yaml → scoring.snow_tree）"""
    cfg = {
        "trigger": {
            "recent_path": {"min_snowfall_12h_cm": 0.2},
            "retention_path": {
                "min_snowfall_24h_cm": 1.5,
                "min_duration_h": 3,
                "min_subzero_hours": 8,
                "max_temp": 1.5,
            },
        },
        "weights": {"snow_signal": 60, "clear_weather": 20, "stability": 20},
        "thresholds": {
            "snow_signal": [
                {"snowfall": 2.5, "duration": 4, "score": 60},
                {"snowfall": 1.5, "duration": 3, "score": 52},
                {"snowfall": 0.8, "duration": 2, "score": 44},
                {"snowfall": 0.2, "duration": 0, "score": 32},
            ],
            "clear_weather": [
                {"weather_code": [0], "max_cloud": 20, "score": 20},
                {"weather_code": [1, 2], "max_cloud": 45, "score": 16},
                {"score": 8},
            ],
            "stability_wind": [12, 20],
            "stability_scores": [20, 14, 8],
        },
        "deductions": {
            "age": [
                {"hours": 3, "deduction": 0},
                {"hours": 8, "deduction": 2},
                {"hours": 12, "deduction": 5},
                {"hours": 16, "deduction": 8},
                {"hours": 20, "deduction": 12},
                {"hours": 999, "deduction": 20},
            ],
            "temp": [
                {"temp": -2, "deduction": 0},
                {"temp": -0.5, "deduction": 2},
                {"temp": 1.0, "deduction": 6},
                {"temp": 2.5, "deduction": 12},
                {"temp": 999, "deduction": 22},
            ],
            "sun": [
                {"sun_score": 2, "deduction": 0},
                {"sun_score": 5, "deduction": 15},
                {"sun_score": 8, "deduction": 30},
            ],
            "wind_severe_threshold": 50,
            "wind_moderate_threshold": 30,
            "wind_severe_deduction": 50,
            "wind_moderate_deduction": 20,
        },
        "past_hours": 24,
        "sunshine": {
            "cloud_thresholds": [10, 30],
            "weights": [2.0, 1.0],
        },
        "safety": {
            "precip_threshold": 50,
            "visibility_threshold": 1000,
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
        capabilities=["snow_tree"],
        targets=[],
    )


def _make_weather_df(
    hours: int = 48,
    base_temp: float = -5.0,
    snowfall: float = 0.0,
    cloud_cover: float = 10.0,
    weather_code: int = 0,
    wind_speed: float = 5.0,
    precipitation_probability: float = 0.0,
    visibility: float = 30000.0,
) -> pd.DataFrame:
    """创建标准天气 DataFrame，所有行使用相同值"""
    base_time = datetime(2026, 2, 10, 0, 0, tzinfo=timezone.utc)
    rows = []
    for i in range(hours):
        t = base_time + pd.Timedelta(hours=i)
        rows.append(
            {
                "time": t,
                "temperature_2m": base_temp,
                "snowfall": snowfall,
                "cloud_cover_total": cloud_cover,
                "weather_code": weather_code,
                "wind_speed_10m": wind_speed,
                "precipitation_probability": precipitation_probability,
                "visibility": visibility,
            }
        )
    return pd.DataFrame(rows)


def _make_context(weather_df: pd.DataFrame) -> DataContext:
    return DataContext(
        date=date(2026, 2, 11),
        viewpoint=_make_viewpoint(),
        local_weather=weather_df,
    )


# ========== tests ==========


class TestSnowTreePluginProperties:
    """Plugin 基本属性"""

    def test_event_type(self):
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())
        assert plugin.event_type == "snow_tree"

    def test_display_name(self):
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())
        assert plugin.display_name == "树挂积雪"

    def test_data_requirement_past_hours(self):
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())
        assert plugin.data_requirement.past_hours == 24

    def test_dimensions(self):
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())
        dims = plugin.dimensions()
        assert "snow_signal" in dims
        assert "clear_weather" in dims
        assert "stability" in dims


class TestSnowTreeNoTrigger:
    """无降雪 → 不触发"""

    def test_no_snowfall_returns_none(self):
        """近期无降雪 → 返回 None"""
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())
        # 48h 无降雪
        df = _make_weather_df(hours=48, snowfall=0.0, base_temp=-5.0)
        ctx = _make_context(df)
        result = plugin.score(ctx)
        assert result is None


class TestSnowTreeRecentPath:
    """常规路径：近 12h 降雪 + 当前晴朗"""

    def test_recent_snow_clear_sky_high_score(self):
        """近 12h 雪 0.5cm, 距今 6h, 晴 → 触发常规路径, score≥70"""
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())

        # 构造 48h 数据：最后 12h 中有降雪
        df = _make_weather_df(hours=48, snowfall=0.0, base_temp=-5.0)

        # 在 hour 36-41 (距当前 12h-7h 前) 设置降雪 ~0.5cm
        # 总共 6h，每小时 0.1cm → 0.6cm (>0.2 触发)
        for i in range(36, 42):
            df.loc[i, "snowfall"] = 0.1

        # hour 42-46: 阴天（避免日照扣分）
        for i in range(42, 47):
            df.loc[i, "weather_code"] = 3
            df.loc[i, "cloud_cover_total"] = 50.0
            df.loc[i, "wind_speed_10m"] = 5.0

        # hour 47: 当前时刻晴朗
        df.loc[47, "weather_code"] = 0
        df.loc[47, "cloud_cover_total"] = 10.0
        df.loc[47, "wind_speed_10m"] = 5.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None
        assert result.event_type == "snow_tree"
        # snow_signal=32(0.6cm) + clear=20 + stable=20 - age=2 = 70
        assert result.total_score >= 70


class TestSnowTreeRetentionPath:
    """留存路径：大雪 + 持续低温 + 暴晒"""

    def test_heavy_snow_with_sun_exposure(self):
        """大雪 3cm, 距今 19h, 暴晒 8h → 触发留存路径, score≈46"""
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())

        # 48h 数据
        df = _make_weather_df(hours=48, snowfall=0.0, base_temp=-3.0)

        # hour 24-28: 大雪 (3cm total, 5h duration, 每小时0.6cm)
        for i in range(24, 29):
            df.loc[i, "snowfall"] = 0.6
            df.loc[i, "temperature_2m"] = -4.0

        # hour 29-47: 停雪后 (19h 距今)
        for i in range(29, 48):
            df.loc[i, "snowfall"] = 0.0

        # hour 29-36: 持续低温
        for i in range(29, 37):
            df.loc[i, "temperature_2m"] = -3.0

        # hour 37-46: 暴晒 (cloud < 10, ~10h 但按 sun_score 只算8h有效)
        for i in range(37, 47):
            df.loc[i, "temperature_2m"] = -1.0  # 升温但仍在零下
            df.loc[i, "cloud_cover_total"] = 5.0  # 强晒
            df.loc[i, "weather_code"] = 0

        # hour 47: 当前时刻
        df.loc[47, "weather_code"] = 0
        df.loc[47, "cloud_cover_total"] = 10.0
        df.loc[47, "wind_speed_10m"] = 5.0
        df.loc[47, "temperature_2m"] = -0.5

        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None
        assert result.event_type == "snow_tree"
        # 积雪信号 60 + 晴朗 20 + 稳定 20 - age_ded - temp_ded - sun_ded
        # score should be around 46 (允许一定误差由具体实现)
        assert 30 <= result.total_score <= 60


class TestSnowTreeDeductions:
    """各扣分项独立验证"""

    def _base_recent_snow_df(self) -> pd.DataFrame:
        """基础数据：近 12h 有 2.5cm 降雪，4h duration，晴，微风，极冷"""
        df = _make_weather_df(hours=48, snowfall=0.0, base_temp=-10.0)
        # hour 42-45: 2.5cm 降雪 (每小时0.625cm, 4h duration)
        for i in range(42, 46):
            df.loc[i, "snowfall"] = 0.625
        # hour 46-47: 晴朗
        for i in range(46, 48):
            df.loc[i, "weather_code"] = 0
            df.loc[i, "cloud_cover_total"] = 10.0
            df.loc[i, "wind_speed_10m"] = 5.0
            df.loc[i, "temperature_2m"] = -10.0
        return df

    def test_wind_severe_deduction(self):
        """历史大风 >50km/h → 大幅扣分 (-50)"""
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())

        df = self._base_recent_snow_df()
        # 降雪后出现过 55km/h 大风
        df.loc[46, "wind_speed_10m"] = 55.0
        # 当前风速恢复正常
        df.loc[47, "wind_speed_10m"] = 5.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None
        # 基础分约 100，风扣 -50 → ≤50
        assert result.total_score <= 50

    def test_wind_moderate_deduction(self):
        """历史大风 >30km/h → 中等扣分 (-20)"""
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())

        df = self._base_recent_snow_df()
        df.loc[46, "wind_speed_10m"] = 35.0
        df.loc[47, "wind_speed_10m"] = 5.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None
        # 基础分约 100，风扣 -20 → ≤80
        assert result.total_score <= 80

    def test_sunshine_deduction(self):
        """累积日照扣分验证"""
        from gmp.scoring.plugins.snow_tree import SnowTreePlugin

        plugin = SnowTreePlugin(_make_config())

        # 构造 48h 数据
        df = _make_weather_df(hours=48, snowfall=0.0, base_temp=-5.0)

        # hour 24-28: 大雪 (3cm, 5h)
        for i in range(24, 29):
            df.loc[i, "snowfall"] = 0.6

        # hour 29-38: 暴晒 10h（强晒：cloud<10%）
        for i in range(29, 39):
            df.loc[i, "cloud_cover_total"] = 5.0
            df.loc[i, "weather_code"] = 0
            df.loc[i, "temperature_2m"] = -3.0

        # 当前晴
        for i in range(39, 48):
            df.loc[i, "weather_code"] = 0
            df.loc[i, "cloud_cover_total"] = 10.0
            df.loc[i, "wind_speed_10m"] = 5.0
            df.loc[i, "temperature_2m"] = -3.0

        ctx = _make_context(df)
        result_with_sun = plugin.score(ctx)

        # 对比无暴晒场景
        df2 = _make_weather_df(hours=48, snowfall=0.0, base_temp=-5.0)
        for i in range(24, 29):
            df2.loc[i, "snowfall"] = 0.6
        for i in range(29, 48):
            df2.loc[i, "cloud_cover_total"] = 80.0  # 多云，不晒
            df2.loc[i, "weather_code"] = 3
            df2.loc[i, "wind_speed_10m"] = 5.0
            df2.loc[i, "temperature_2m"] = -5.0
        # 当前时刻晴
        df2.loc[47, "weather_code"] = 0
        df2.loc[47, "cloud_cover_total"] = 10.0

        ctx2 = _make_context(df2)
        result_no_sun = plugin.score(ctx2)

        assert result_with_sun is not None
        assert result_no_sun is not None
        # 暴晒应该比不晒低分
        assert result_with_sun.total_score < result_no_sun.total_score
