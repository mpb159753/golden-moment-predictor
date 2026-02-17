"""tests/integration/test_config_consistency.py — 配置-代码一致性测试

验证实际 engine_config.yaml 中每个 Plugin 的配置项能被代码完整读取，
使用合成天气数据强制触发所有 Plugin 的完整评分路径。

背景:
  单元测试使用硬编码 fixture，E2E 测试依赖真实天气（季节性 Plugin 可能未触发）。
  两者都无法检测"实际配置文件缺少代码所需键"的问题。
  本测试用合成的极端天气数据确保所有 Plugin 在真实配置下走完完整评分链路。
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from gmp.core.config_loader import ConfigManager
from gmp.core.models import (
    Location,
    MoonStatus,
    StargazingWindow,
    SunEvents,
    Target,
    Viewpoint,
)
from gmp.scoring.models import DataContext
from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin
from gmp.scoring.plugins.frost import FrostPlugin
from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin
from gmp.scoring.plugins.ice_icicle import IceIciclePlugin
from gmp.scoring.plugins.snow_tree import SnowTreePlugin
from gmp.scoring.plugins.stargazing import StargazingPlugin


CONFIG_PATH = "config/engine_config.yaml"


@pytest.fixture(scope="module")
def config():
    """加载真实配置文件"""
    return ConfigManager(CONFIG_PATH)


def _make_viewpoint() -> Viewpoint:
    """构造测试用观景台（模拟牛背山）"""
    return Viewpoint(
        id="test_vp",
        name="测试观景台",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=[
            "sunrise", "sunset", "stargazing",
            "cloud_sea", "frost", "snow_tree", "ice_icicle",
        ],
        targets=[
            Target(
                name="贡嘎主峰", lat=29.58, lon=101.88,
                altitude=7556, weight="primary",
                # 显式声明适用事件，避免方位角自动匹配的不确定性
                applicable_events=["sunrise", "sunset"],
            ),
        ],
    )


def _make_weather_df(hours: int = 25, **overrides) -> pd.DataFrame:
    """构造合成天气 DataFrame，包含所有 Plugin 所需的列。

    默认天气: 低温(-3°C)、有降雪、低云量、低风速、高能见度。
    """
    defaults = {
        "temperature_2m": -3.0,
        "cloud_cover_total": 15.0,
        "cloud_cover_low": 80.0,
        "cloud_cover_medium": 10.0,
        "cloud_cover_high": 5.0,
        "cloud_base_altitude": 2500.0,  # CloudSeaPlugin 需要此列
        "wind_speed_10m": 5.0,
        "visibility": 20000,
        "precipitation_probability": 10,
        "weather_code": 0,
        "snowfall": 0.5,
        "rain": 0.3,
        "showers": 0.0,
        "relative_humidity_2m": 90.0,
    }
    defaults.update(overrides)
    data = {k: [v] * hours for k, v in defaults.items()}
    return pd.DataFrame(data)


def _make_sun_events() -> SunEvents:
    """构造太阳事件数据"""
    return SunEvents(
        sunrise=datetime(2026, 2, 10, 7, 20, tzinfo=timezone.utc),
        sunset=datetime(2026, 2, 10, 18, 30, tzinfo=timezone.utc),
        sunrise_azimuth=110.0,
        sunset_azimuth=250.0,
        astronomical_dawn=datetime(2026, 2, 10, 5, 50, tzinfo=timezone.utc),
        astronomical_dusk=datetime(2026, 2, 10, 20, 0, tzinfo=timezone.utc),
    )


def _make_stargazing_window() -> StargazingWindow:
    """构造观星窗口数据（最优条件）"""
    return StargazingWindow(
        optimal_start=datetime(2026, 2, 10, 20, 0, tzinfo=timezone.utc),
        optimal_end=datetime(2026, 2, 11, 5, 30, tzinfo=timezone.utc),
        good_start=datetime(2026, 2, 10, 19, 30, tzinfo=timezone.utc),
        good_end=datetime(2026, 2, 11, 6, 0, tzinfo=timezone.utc),
        quality="optimal",
    )


def _make_moon_status() -> MoonStatus:
    """构造月亮状态（新月，利于观星）"""
    return MoonStatus(
        phase=5,
        elevation=-30.0,
        moonrise=None,
        moonset=None,
    )


def _make_context(
    df: pd.DataFrame,
    *,
    sun_events: SunEvents | None = None,
    stargazing_window: StargazingWindow | None = None,
    moon_status: MoonStatus | None = None,
    target_weather: dict | None = None,
    light_path_weather: list | None = None,
) -> DataContext:
    """构造 DataContext"""
    return DataContext(
        date=date(2026, 2, 10),
        viewpoint=_make_viewpoint(),
        local_weather=df,
        sun_events=sun_events,
        stargazing_window=stargazing_window,
        moon_status=moon_status,
        target_weather=target_weather,
        light_path_weather=light_path_weather,
    )


class TestPluginConfigConsistency:
    """使用真实 engine_config.yaml 和合成触发数据，验证每个 Plugin 完整评分链路。

    目的: 检测配置文件与代码之间的键名不一致问题，
    这类问题不会被单元测试（硬编码 fixture）或 E2E 测试（天气未触发）发现。
    """

    def test_snow_tree_with_real_config(self, config):
        """SnowTreePlugin: 合成降雪天气 → 应走完评分 + 扣分全链路"""
        plugin_cfg = config.get_plugin_config("snow_tree")
        plugin = SnowTreePlugin(plugin_cfg)

        df = _make_weather_df(hours=25, snowfall=1.0, temperature_2m=-5.0)
        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None, (
            "SnowTreePlugin 应在有降雪条件下被触发，检查 trigger 配置"
        )
        assert result.event_type == "snow_tree"
        assert 0 <= result.total_score <= 100
        assert "snow_signal" in result.breakdown
        assert "stability" in result.breakdown

    def test_ice_icicle_with_real_config(self, config):
        """IceIciclePlugin: 合成降雨+低温 → 应走完评分全链路"""
        plugin_cfg = config.get_plugin_config("ice_icicle")
        plugin = IceIciclePlugin(plugin_cfg)

        df = _make_weather_df(hours=25, rain=0.5, temperature_2m=-3.0)
        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None, (
            "IceIciclePlugin 应在有水源+低温下被触发"
        )
        assert result.event_type == "ice_icicle"
        assert 0 <= result.total_score <= 100
        assert "water_input" in result.breakdown
        assert "freeze_strength" in result.breakdown

    def test_frost_with_real_config(self, config):
        """FrostPlugin: 合成低温天气 → 应走完评分全链路"""
        plugin_cfg = config.get_plugin_config("frost")
        plugin = FrostPlugin(plugin_cfg)

        df = _make_weather_df(hours=25, temperature_2m=-2.0, visibility=15000)
        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None, (
            "FrostPlugin 应在低温条件下被触发"
        )
        assert result.event_type == "frost"
        assert 0 <= result.total_score <= 100

    def test_cloud_sea_with_real_config(self, config):
        """CloudSeaPlugin: 合成低云天气 → 应走完评分全链路"""
        plugin_cfg = config.get_plugin_config("cloud_sea")
        safety_cfg = config.get_safety_config()
        plugin = CloudSeaPlugin(plugin_cfg, safety_cfg)

        df = _make_weather_df(
            hours=25,
            cloud_cover_low=90.0,
            cloud_cover_medium=5.0,
            cloud_cover_high=5.0,
            cloud_base_altitude=2500.0,  # 低于观景台海拔 3660m
            wind_speed_10m=2.0,
        )
        ctx = _make_context(df)
        result = plugin.score(ctx)

        assert result is not None, (
            "CloudSeaPlugin 应在高低云量+低云底高度条件下被触发"
        )
        assert result.event_type == "cloud_sea"
        assert 0 <= result.total_score <= 100

    def test_stargazing_with_real_config(self, config):
        """StargazingPlugin: 合成晴朗夜空 → 应走完评分全链路"""
        plugin_cfg = config.get_plugin_config("stargazing")
        plugin = StargazingPlugin(plugin_cfg)

        df = _make_weather_df(
            hours=25,
            cloud_cover_total=10.0,
            wind_speed_10m=3.0,
        )
        ctx = _make_context(
            df,
            stargazing_window=_make_stargazing_window(),
            moon_status=_make_moon_status(),
        )
        result = plugin.score(ctx)

        assert result is not None, (
            "StargazingPlugin 应在晴朗夜空+有观星窗口下被触发"
        )
        assert result.event_type == "stargazing"
        assert 0 <= result.total_score <= 100

    def test_golden_mountain_sunrise_with_real_config(self, config):
        """GoldenMountainPlugin(sunrise): 合成晴天 → 应走完评分全链路"""
        plugin_cfg = config.get_plugin_config("golden_mountain")
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", plugin_cfg)

        df = _make_weather_df(
            hours=25,
            cloud_cover_total=5.0,
            cloud_cover_low=3.0,
            cloud_cover_medium=2.0,
            cloud_cover_high=2.0,
        )
        # 提供目标山峰天气和光路天气以覆盖更多代码路径
        target_df = _make_weather_df(
            hours=25,
            cloud_cover_high=5.0,
            cloud_cover_medium=3.0,
        )
        ctx = _make_context(
            df,
            sun_events=_make_sun_events(),
            target_weather={"贡嘎主峰": target_df},
            light_path_weather=[{
                "azimuth": 110.0,
                "points": [(29.6, 102.0)],
                "weather": {(29.6, 102.0): target_df},
            }],
        )
        result = plugin.score(ctx)

        assert result is not None, (
            "sunrise_golden_mountain: 应在低云量条件下被触发"
        )
        assert result.event_type == "sunrise_golden_mountain"
        assert 0 <= result.total_score <= 100
        assert "light_path" in result.breakdown
        assert "target_visible" in result.breakdown
        assert "local_clear" in result.breakdown

    def test_golden_mountain_sunset_with_real_config(self, config):
        """GoldenMountainPlugin(sunset): 合成晴天 → 应走完评分全链路"""
        plugin_cfg = config.get_plugin_config("golden_mountain")
        plugin = GoldenMountainPlugin("sunset_golden_mountain", plugin_cfg)

        df = _make_weather_df(
            hours=25,
            cloud_cover_total=5.0,
            cloud_cover_low=3.0,
            cloud_cover_medium=2.0,
            cloud_cover_high=2.0,
        )
        target_df = _make_weather_df(
            hours=25,
            cloud_cover_high=5.0,
            cloud_cover_medium=3.0,
        )
        ctx = _make_context(
            df,
            sun_events=_make_sun_events(),
            target_weather={"贡嘎主峰": target_df},
            light_path_weather=[{
                "azimuth": 250.0,
                "points": [(29.6, 102.0)],
                "weather": {(29.6, 102.0): target_df},
            }],
        )
        result = plugin.score(ctx)

        assert result is not None, (
            "sunset_golden_mountain: 应在低云量条件下被触发"
        )
        assert result.event_type == "sunset_golden_mountain"
        assert 0 <= result.total_score <= 100
