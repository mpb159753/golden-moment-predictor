"""tests/unit/test_plugin_golden_mountain.py — GoldenMountainPlugin 单元测试"""

from datetime import date, datetime

import pandas as pd
import pytest

from gmp.core.models import Location, ScoreResult, SunEvents, Target, Viewpoint
from gmp.scoring.models import DataContext, DataRequirement


# ==================== helpers ====================

DEFAULT_CONFIG: dict = {
    "trigger": {
        "max_cloud_cover": 80,
    },
    "weights": {
        "light_path": 35,
        "target_visible": 40,
        "local_clear": 25,
    },
    "thresholds": {
        "light_path_cloud": [10, 20, 30, 50],
        "light_path_scores": [35, 30, 20, 10, 0],
        "target_cloud": [10, 20, 30, 50],
        "target_scores": [40, 35, 25, 10, 0],
        "local_cloud": [15, 30, 50],
        "local_scores": [25, 20, 10, 0],
    },
    "veto_threshold": 0,
}


def _sun_events(
    sunrise_azimuth: float = 108.5,
    sunset_azimuth: float = 251.5,
) -> SunEvents:
    """创建测试用天文事件"""
    return SunEvents(
        sunrise=datetime(2026, 1, 15, 7, 30),
        sunset=datetime(2026, 1, 15, 17, 45),
        sunrise_azimuth=sunrise_azimuth,
        sunset_azimuth=sunset_azimuth,
        astronomical_dawn=datetime(2026, 1, 15, 5, 30),
        astronomical_dusk=datetime(2026, 1, 15, 19, 45),
    )


def _viewpoint(
    lat: float = 29.64,
    lon: float = 102.36,
    altitude: int = 3660,
) -> Viewpoint:
    """创建测试用观景台 — 含贡嘎和雅拉两个目标"""
    return Viewpoint(
        id="vp_niubeishan",
        name="牛背山",
        location=Location(lat=lat, lon=lon, altitude=altitude),
        capabilities=["sunrise", "sunset"],
        targets=[
            Target(
                name="贡嘎",
                lat=29.6,
                lon=101.87,
                altitude=7556,
                weight="primary",
                applicable_events=None,  # 自动计算
            ),
            Target(
                name="雅拉",
                lat=30.1,
                lon=101.8,
                altitude=5884,
                weight="secondary",
                applicable_events=["sunset"],  # 仅 sunset
            ),
        ],
    )


def _viewpoint_no_match() -> Viewpoint:
    """创建无匹配目标的观景台"""
    return Viewpoint(
        id="vp_none",
        name="无目标观景台",
        location=Location(lat=29.64, lon=102.36, altitude=3660),
        capabilities=["sunrise"],
        targets=[],
    )


def _local_weather(
    *,
    cloud_cover: float = 30.0,
    hours: int = 3,
) -> pd.DataFrame:
    """创建本地天气 DataFrame"""
    return pd.DataFrame(
        {
            "cloud_cover_total": [cloud_cover] * hours,
        }
    )


def _target_weather(
    *,
    target_name: str = "贡嘎",
    high_cloud: float = 10.0,
    mid_cloud: float = 5.0,
    hours: int = 3,
) -> dict[str, pd.DataFrame]:
    """创建目标天气数据"""
    return {
        target_name: pd.DataFrame(
            {
                "cloud_cover_high": [high_cloud] * hours,
                "cloud_cover_medium": [mid_cloud] * hours,
            }
        ),
    }


def _light_path_weather(
    *,
    low_cloud: float = 5.0,
    mid_cloud: float = 3.0,
    n_points: int = 10,
    hours: int = 3,
) -> list[dict]:
    """创建光路天气数据 — 10个检查点"""
    return [
        {
            "coord": (30.0 + i * 0.1, 101.5 + i * 0.1),
            "weather": pd.DataFrame(
                {
                    "cloud_cover_low": [low_cloud] * hours,
                    "cloud_cover_medium": [mid_cloud] * hours,
                }
            ),
        }
        for i in range(n_points)
    ]


def _context(
    *,
    viewpoint: Viewpoint | None = None,
    local_weather: pd.DataFrame | None = None,
    sun_events: SunEvents | None = None,
    target_weather: dict[str, pd.DataFrame] | None = None,
    light_path_weather: list[dict] | None = None,
) -> DataContext:
    """创建测试用 DataContext"""
    return DataContext(
        date=date(2026, 1, 15),
        viewpoint=viewpoint if viewpoint is not None else _viewpoint(),
        local_weather=local_weather if local_weather is not None else _local_weather(),
        sun_events=sun_events if sun_events is not None else _sun_events(),
        target_weather=target_weather if target_weather is not None else _target_weather(),
        light_path_weather=light_path_weather if light_path_weather is not None else _light_path_weather(),
    )


# ==================== Tests: 元数据 ====================


class TestGoldenMountainMetadata:
    """Plugin 元数据"""

    def test_event_type_sunrise(self):
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        assert plugin.event_type == "sunrise_golden_mountain"

    def test_event_type_sunset(self):
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunset_golden_mountain", DEFAULT_CONFIG)
        assert plugin.event_type == "sunset_golden_mountain"

    def test_data_requirement_l2(self):
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        req = plugin.data_requirement
        assert req.needs_l2_target is True
        assert req.needs_l2_light_path is True
        assert req.needs_astro is True


# ==================== Tests: 触发判定 ====================


class TestGoldenMountainTrigger:
    """触发判定"""

    def test_high_cloud_cover_returns_none(self):
        """总云量 ≥ 80% → None"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context(local_weather=_local_weather(cloud_cover=80.0))
        result = plugin.score(ctx)
        assert result is None

    def test_no_matching_target_returns_none(self):
        """无匹配 Target → None"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context(viewpoint=_viewpoint_no_match())
        result = plugin.score(ctx)
        assert result is None

    def test_normal_scenario_returns_score(self):
        """正常场景 → ScoreResult"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context()
        result = plugin.score(ctx)
        assert result is not None
        assert isinstance(result, ScoreResult)


# ==================== Tests: 方位角匹配 ====================


class TestGoldenMountainTargetMatching:
    """Target 方位角匹配"""

    def test_sunrise_gongg_auto_match(self):
        """sunrise 事件: 贡嘎 bearing≈245°, sunrise_azimuth≈108.5° → 匹配

        贡嘎在观景台的西南方，日出在东南方，
        is_opposite_direction(245, 108.5) 应为 True
        """
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        # 贡嘎 applicable_events=None，走自动计算
        ctx = _context()
        result = plugin.score(ctx)
        assert result is not None

    def test_sunset_yala_explicit_match(self):
        """sunset 事件: 雅拉 applicable_events=["sunset"] → 匹配"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunset_golden_mountain", DEFAULT_CONFIG)
        # 雅拉 applicable_events=["sunset"]
        # 构造只有雅拉目标的 viewpoint
        vp = Viewpoint(
            id="vp_yala",
            name="雅拉观景台",
            location=Location(lat=29.64, lon=102.36, altitude=3660),
            capabilities=["sunset"],
            targets=[
                Target(
                    name="雅拉",
                    lat=30.1,
                    lon=101.8,
                    altitude=5884,
                    weight="primary",
                    applicable_events=["sunset"],
                ),
            ],
        )
        ctx = _context(
            viewpoint=vp,
            target_weather=_target_weather(target_name="雅拉"),
        )
        result = plugin.score(ctx)
        assert result is not None

    def test_sunrise_yala_explicit_no_match(self):
        """sunrise 事件: 雅拉 applicable_events=["sunset"] → 不匹配"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        vp = Viewpoint(
            id="vp_yala",
            name="雅拉观景台",
            location=Location(lat=29.64, lon=102.36, altitude=3660),
            capabilities=["sunrise"],
            targets=[
                Target(
                    name="雅拉",
                    lat=30.1,
                    lon=101.8,
                    altitude=5884,
                    weight="primary",
                    applicable_events=["sunset"],  # 仅 sunset
                ),
            ],
        )
        ctx = _context(
            viewpoint=vp,
            target_weather=_target_weather(target_name="雅拉"),
        )
        result = plugin.score(ctx)
        assert result is None  # 无匹配目标


# ==================== Tests: 评分计算 ====================


class TestGoldenMountainScoring:
    """评分计算"""

    def test_good_conditions_score_90(self):
        """光路 8%, 目标 13%, 本地 22% → score=90, Recommended

        阶梯评分:
        - light_path 8% ≤10 → 35
        - target (h+m)=13% ≤20 → 35
        - local 22% ≤30 → 20
        - total = 35 + 35 + 20 = 90
        """
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context(
            light_path_weather=_light_path_weather(low_cloud=5.0, mid_cloud=3.0),
            target_weather=_target_weather(high_cloud=8.0, mid_cloud=5.0),
            local_weather=_local_weather(cloud_cover=22.0),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 90
        assert result.status == "Recommended"

    def test_perfect_conditions_score_100(self):
        """光路 0%, 目标 5%, 本地 10% → score=100, Perfect

        阶梯评分:
        - light_path 0% ≤10 → 35
        - target 5% ≤10 → 40
        - local 10% ≤15 → 25
        - total = 35 + 40 + 25 = 100
        """
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context(
            light_path_weather=_light_path_weather(low_cloud=0.0, mid_cloud=0.0),
            target_weather=_target_weather(high_cloud=3.0, mid_cloud=2.0),
            local_weather=_local_weather(cloud_cover=10.0),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 100
        assert result.status == "Perfect"

    def test_veto_light_path_cloud_60(self):
        """光路 60% → S_light=0, 一票否决, 总分=0"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context(
            light_path_weather=_light_path_weather(low_cloud=40.0, mid_cloud=20.0),
            target_weather=_target_weather(high_cloud=3.0, mid_cloud=2.0),
            local_weather=_local_weather(cloud_cover=10.0),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 0

    def test_veto_target_cloud_55(self):
        """目标 55% → S_target=0, 一票否决, 总分=0"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context(
            light_path_weather=_light_path_weather(low_cloud=0.0, mid_cloud=0.0),
            target_weather=_target_weather(high_cloud=30.0, mid_cloud=25.0),
            local_weather=_local_weather(cloud_cover=10.0),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 0

    def test_veto_local_cloud_55(self):
        """本地 55% → S_local=0, 一票否决, 总分=0"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _context(
            light_path_weather=_light_path_weather(low_cloud=0.0, mid_cloud=0.0),
            target_weather=_target_weather(high_cloud=3.0, mid_cloud=2.0),
            local_weather=_local_weather(cloud_cover=55.0),
        )
        result = plugin.score(ctx)
        assert result is not None
        assert result.total_score == 0


# ==================== Tests: 双实例 ====================


class TestGoldenMountainDualInstance:
    """双实例"""

    def test_sunrise_and_sunset_independent(self):
        """sunrise 和 sunset 实例独立评分"""
        from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

        sunrise_plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        sunset_plugin = GoldenMountainPlugin("sunset_golden_mountain", DEFAULT_CONFIG)

        assert sunrise_plugin.event_type == "sunrise_golden_mountain"
        assert sunset_plugin.event_type == "sunset_golden_mountain"

        # 两者可以同时注册
        assert sunrise_plugin.event_type != sunset_plugin.event_type
