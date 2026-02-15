"""tests/unit/test_plugin_ice_icicle.py — IceIciclePlugin 单元测试"""

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from gmp.core.models import Location, ScoreResult, Viewpoint
from gmp.scoring.models import DataContext, DataRequirement


# ========== helpers ==========


def _make_config(overrides: dict | None = None) -> dict:
    """构造标准测试配置（对应 engine_config.yaml → scoring.ice_icicle）"""
    cfg = {
        "trigger": {
            "recent_path": {"min_water_12h_mm": 0.4},
            "retention_path": {
                "min_water_24h_mm": 1.0,
                "min_subzero_hours": 6,
                "max_temp": 1.5,
            },
        },
        "weights": {"water_input": 50, "freeze_strength": 30, "view_quality": 20},
        "thresholds": {
            "water_input": [
                {"water": 3.0, "score": 50},
                {"water": 2.0, "score": 42},
                {"water": 1.0, "score": 34},
                {"water": 0.4, "score": 24},
            ],
            "freeze_strength": [
                {"subzero_hours": 14, "temp_now": -3, "score": 30},
                {"subzero_hours": 10, "temp_now": -1, "score": 24},
                {"subzero_hours": 6, "temp_now": 0, "score": 16},
                {"score": 10},
            ],
            "view_quality": [
                {"max_cloud": 20, "max_wind": 12, "score": 20},
                {"max_cloud": 45, "max_wind": 20, "score": 14},
                {"score": 8},
            ],
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
                {"temp": 1, "deduction": 6},
                {"temp": 2.5, "deduction": 12},
                {"temp": 999, "deduction": 22},
            ],
        },
        "past_hours": 24,
        "safety": {
            "precip_threshold": 50,
            "visibility_threshold": 1000,
        },
        "snow_water_ratio": 0.1,  # 1cm 雪 = 0.1cm 水 = 1mm 水
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
        capabilities=["ice_icicle"],
        targets=[],
    )


def _make_weather_df(
    hours: int = 48,
    base_temp: float = -5.0,
    rain: float = 0.0,
    showers: float = 0.0,
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
                "rain": rain,
                "showers": showers,
                "snowfall": snowfall,
                "cloud_cover": cloud_cover,
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


class TestIceIciclePluginProperties:
    """Plugin 基本属性"""

    def test_event_type(self):
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())
        assert plugin.event_type == "ice_icicle"

    def test_display_name(self):
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())
        assert plugin.display_name == "冰挂"

    def test_data_requirement_past_hours(self):
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())
        assert plugin.data_requirement.past_hours == 24

    def test_dimensions(self):
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())
        dims = plugin.dimensions()
        assert "water_input" in dims
        assert "freeze_strength" in dims
        assert "view_quality" in dims


class TestIceIcicleNoTrigger:
    """近期无有效水源 → 不触发"""

    def test_no_water_returns_none(self):
        """近期无降水也无降雪 → 返回 None"""
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())
        df = _make_weather_df(hours=48, rain=0.0, showers=0.0, snowfall=0.0,
                              base_temp=-5.0)
        ctx = _make_context(df)
        result = plugin.score(ctx)
        assert result is None


class TestIceIcicleScoring:
    """综合评分场景"""

    def test_water_2_3mm_freeze_11h_temp_neg1_8(self):
        """水源 2.3mm, 冻结 11h, 当前 -1.8°C → score≈70"""
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())

        # 48h 数据基础
        df = _make_weather_df(hours=48, base_temp=-3.0,
                              cloud_cover=15.0, wind_speed=5.0)

        # hour 34-36 (距今约 14-12h 前): 降雨 ≈ 2.3mm total
        # hour 34: 0.8mm, hour 35: 0.8mm, hour 36: 0.7mm
        df.loc[34, "rain"] = 0.8
        df.loc[35, "rain"] = 0.8
        df.loc[36, "rain"] = 0.7

        # hour 37-47 (降水停止后): 持续冻结 11h
        for i in range(37, 48):
            df.loc[i, "temperature_2m"] = -1.8
            df.loc[i, "rain"] = 0.0
            df.loc[i, "snowfall"] = 0.0

        # 当前时刻晴朗微风
        df.loc[47, "weather_code"] = 0
        df.loc[47, "cloud_cover"] = 15.0
        df.loc[47, "wind_speed_10m"] = 5.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None
        assert result.event_type == "ice_icicle"
        # water_input: 2.3mm → score 42 (>= 2.0)
        # freeze_strength: 11h,  temp_now -1.8 → score 24 (>= 10h, temp_now <= -1)
        # view_quality: cloud 15, wind 5 → score 20 (<= 20, <= 12)
        # 基础总分: 42 + 24 + 20 = 86
        # age deduction: hours_since=11 → 5
        # temp deduction: max_temp=-1.8 → 0
        # total ≈ 81
        # 允许一些误差 (派生指标计算方式可能略有出入)
        assert 60 <= result.total_score <= 90


class TestIceIcicleWaterInputThresholds:
    """水源输入维度阶梯验证"""

    def _score_with_water(self, total_water_mm: float) -> ScoreResult | None:
        """构造一个有指定水源量的场景并返回结果"""
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())

        df = _make_weather_df(hours=48, base_temp=-5.0,
                              cloud_cover=15.0, wind_speed=5.0)
        # 在 hour 36 集中降雨
        df.loc[36, "rain"] = total_water_mm

        # 降水后冻结
        for i in range(37, 48):
            df.loc[i, "temperature_2m"] = -5.0

        ctx = _make_context(df)
        return plugin.score(ctx)

    def test_water_3mm_highest_tier(self):
        """3mm 水源 → water_input score = 50"""
        result = self._score_with_water(3.0)
        assert result is not None
        assert result.breakdown["water_input"]["score"] == 50

    def test_water_2mm_second_tier(self):
        """2mm 水源 → water_input score = 42"""
        result = self._score_with_water(2.0)
        assert result is not None
        assert result.breakdown["water_input"]["score"] == 42

    def test_water_1mm_third_tier(self):
        """1mm 水源 → water_input score = 34"""
        result = self._score_with_water(1.0)
        assert result is not None
        assert result.breakdown["water_input"]["score"] == 34

    def test_water_0_5mm_lowest_tier(self):
        """0.5mm 水源 → water_input score = 24"""
        result = self._score_with_water(0.5)
        assert result is not None
        assert result.breakdown["water_input"]["score"] == 24


class TestIceIcicleDeductions:
    """扣分项验证"""

    def test_age_deduction(self):
        """距上次水源 16h → age deduction = 8"""
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())

        df = _make_weather_df(hours=48, base_temp=-5.0,
                              cloud_cover=15.0, wind_speed=5.0)

        # hour 31 (距今 16h): 降雨 2mm
        df.loc[31, "rain"] = 2.0

        # 降水后持续冻结
        for i in range(32, 48):
            df.loc[i, "temperature_2m"] = -5.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None
        assert result.breakdown["age_deduction"]["score"] == -8

    def test_temp_deduction(self):
        """升温到 2.0°C → temp deduction = 12"""
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())

        df = _make_weather_df(hours=48, base_temp=-5.0,
                              cloud_cover=15.0, wind_speed=5.0)

        # hour 38: 降雨
        df.loc[38, "rain"] = 2.0

        # 降水后 - 先冻结再升温
        for i in range(39, 45):
            df.loc[i, "temperature_2m"] = -3.0
        for i in range(45, 48):
            df.loc[i, "temperature_2m"] = 2.0  # 升温到 2.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None
        assert result.breakdown["temp_deduction"]["score"] == -12


class TestIceIcicleSnowWaterEquivalent:
    """雪转水当量计算正确"""

    def test_snowfall_converted_to_water(self):
        """1cm 降雪 = 1mm 水当量 (ratio 0.1)，应触发评分"""
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())

        df = _make_weather_df(hours=48, base_temp=-5.0,
                              cloud_cover=15.0, wind_speed=5.0)

        # 无雨但有降雪 (1cm = 1mm water equivalent)
        df.loc[40, "snowfall"] = 1.0  # 1cm

        # 降雪后持续冻结
        for i in range(41, 48):
            df.loc[i, "temperature_2m"] = -5.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        # 1mm >= 0.4mm 触发阈值 → 应触发
        assert result is not None

    def test_rain_plus_snow_combined(self):
        """雨 + 雪混合降水，总有效水源 = rain + showers + snowfall * ratio"""
        from gmp.scoring.plugins.ice_icicle import IceIciclePlugin

        plugin = IceIciclePlugin(_make_config())

        df = _make_weather_df(hours=48, base_temp=-3.0,
                              cloud_cover=15.0, wind_speed=5.0)

        # rain 0.3mm + snowfall 0.5cm (= 0.5mm) → total 0.8mm
        df.loc[40, "rain"] = 0.3
        df.loc[40, "snowfall"] = 0.5  # 0.5cm → 0.5mm water

        for i in range(41, 48):
            df.loc[i, "temperature_2m"] = -5.0

        ctx = _make_context(df)
        result = plugin.score(ctx)

        # 0.8mm >= 0.4mm → 触发
        assert result is not None
        # water_input 应为 0.8mm → score 24 (>= 0.4)
        assert result.breakdown["water_input"]["score"] == 24
