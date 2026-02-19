"""tests/unit/test_golden_mountain_debug.py — debug_score() 单元测试"""

from datetime import date, datetime

import pandas as pd
import pytest

from gmp.core.models import Location, SunEvents, Target, Viewpoint
from gmp.scoring.models import DataContext
from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin


# ==================== helpers ====================

DEFAULT_CONFIG: dict = {
    "trigger": {"max_cloud_cover": 80},
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
    return SunEvents(
        sunrise=datetime(2026, 1, 15, 7, 30),
        sunset=datetime(2026, 1, 15, 17, 45),
        sunrise_azimuth=sunrise_azimuth,
        sunset_azimuth=sunset_azimuth,
        astronomical_dawn=datetime(2026, 1, 15, 5, 30),
        astronomical_dusk=datetime(2026, 1, 15, 19, 45),
    )


def _viewpoint() -> Viewpoint:
    return Viewpoint(
        id="vp_niubeishan",
        name="牛背山",
        location=Location(lat=29.64, lon=102.36, altitude=3660),
        capabilities=["sunrise", "sunset"],
        targets=[
            Target(
                name="贡嘎",
                lat=29.6,
                lon=101.87,
                altitude=7556,
                weight="primary",
                applicable_events=None,
            ),
        ],
    )


def _viewpoint_no_targets() -> Viewpoint:
    return Viewpoint(
        id="vp_none",
        name="无目标",
        location=Location(lat=29.64, lon=102.36, altitude=3660),
        capabilities=["sunrise"],
        targets=[],
    )


def _local_weather(*, cloud_cover: float = 30.0, hours: int = 3) -> pd.DataFrame:
    return pd.DataFrame({"cloud_cover_total": [cloud_cover] * hours})


def _target_weather(
    *, target_name: str = "贡嘎", high_cloud: float = 10.0, mid_cloud: float = 5.0
) -> dict[str, pd.DataFrame]:
    return {
        target_name: pd.DataFrame(
            {"cloud_cover_high": [high_cloud] * 3, "cloud_cover_medium": [mid_cloud] * 3}
        )
    }


def _light_path_weather(
    *, low_cloud: float = 5.0, mid_cloud: float = 3.0
) -> list[dict]:
    points = [(30.0 + i * 0.1, 101.5 + i * 0.1) for i in range(10)]
    weather_dict = {
        coord: pd.DataFrame(
            {"cloud_cover_low": [low_cloud] * 3, "cloud_cover_medium": [mid_cloud] * 3}
        )
        for coord in points
    }
    return [{"azimuth": 90.0, "points": points, "weather": weather_dict}]


def _ctx(**kwargs) -> DataContext:
    defaults = {
        "date": date(2026, 1, 15),
        "viewpoint": _viewpoint(),
        "local_weather": _local_weather(),
        "sun_events": _sun_events(),
        "target_weather": _target_weather(),
        "light_path_weather": _light_path_weather(),
    }
    defaults.update(kwargs)
    return DataContext(**defaults)


# ==================== Tests ====================


class TestDebugScoreRejected:
    """测试 debug_score 的各种拒绝场景"""

    def test_rejected_no_sun_events(self):
        """sun_events=None → rejected"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx(sun_events=None)
        result = plugin.debug_score(ctx)

        assert result["decision"] == "rejected"
        assert "sun_events" in result["reason"]
        assert len(result["steps"]) == 1
        assert result["steps"][0]["step"] == "astro_check"
        assert result["steps"][0]["passed"] is False

    def test_rejected_high_cloud(self):
        """总云量 ≥ 80% → rejected"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx(local_weather=_local_weather(cloud_cover=85.0))
        result = plugin.debug_score(ctx)

        assert result["decision"] == "rejected"
        assert "85" in result["reason"]
        assert "80" in result["reason"]
        # 应有 astro_check(passed) + cloud_trigger(failed)
        assert len(result["steps"]) == 2
        assert result["steps"][0]["passed"] is True
        assert result["steps"][1]["step"] == "cloud_trigger"
        assert result["steps"][1]["passed"] is False

    def test_rejected_no_target_match(self):
        """无匹配 Target → rejected"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx(viewpoint=_viewpoint_no_targets())
        result = plugin.debug_score(ctx)

        assert result["decision"] == "rejected"
        assert "Target" in result["reason"]
        assert len(result["steps"]) == 3
        assert result["steps"][2]["step"] == "target_match"
        assert result["steps"][2]["passed"] is False


class TestDebugScoreVetoed:
    """测试一票否决"""

    def test_vetoed_light_path(self):
        """光路云量 60% → 一票否决"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx(
            light_path_weather=_light_path_weather(low_cloud=40.0, mid_cloud=20.0),
        )
        result = plugin.debug_score(ctx)

        assert result["decision"] == "vetoed"
        assert result["total_score"] == 0
        assert "一票否决" in result["reason"]
        scoring_step = result["steps"][-1]
        assert scoring_step["step"] == "scoring"
        assert scoring_step["vetoed"] is True
        assert len(scoring_step["veto_dims"]) > 0


class TestDebugScoreSuccess:
    """测试正常评分"""

    def test_scored_successfully(self):
        """正常条件 → scored"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx(
            light_path_weather=_light_path_weather(low_cloud=5.0, mid_cloud=3.0),
            target_weather=_target_weather(high_cloud=8.0, mid_cloud=5.0),
            local_weather=_local_weather(cloud_cover=22.0),
        )
        result = plugin.debug_score(ctx)

        assert result["decision"] == "scored"
        assert result["total_score"] == 90
        assert "总分 90" in result["reason"]
        assert len(result["steps"]) == 4  # astro + cloud + target + scoring

    def test_debug_consistent_with_score(self):
        """debug_score 的结果应与 score 一致"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx(
            light_path_weather=_light_path_weather(low_cloud=0.0, mid_cloud=0.0),
            target_weather=_target_weather(high_cloud=3.0, mid_cloud=2.0),
            local_weather=_local_weather(cloud_cover=10.0),
        )

        score_result = plugin.score(ctx)
        debug_result = plugin.debug_score(ctx)

        assert score_result is not None
        assert debug_result["decision"] == "scored"
        assert debug_result["total_score"] == score_result.total_score

    def test_debug_contains_sun_azimuth(self):
        """诊断结果应包含 sun_azimuth"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx()
        result = plugin.debug_score(ctx)

        assert "sun_azimuth" in result
        assert result["sun_azimuth"] == 108.5

    def test_debug_target_details(self):
        """诊断结果应包含 target 匹配细节"""
        plugin = GoldenMountainPlugin("sunrise_golden_mountain", DEFAULT_CONFIG)
        ctx = _ctx()
        result = plugin.debug_score(ctx)

        target_step = next(s for s in result["steps"] if s["step"] == "target_match")
        assert len(target_step["targets"]) == 1
        assert target_step["targets"][0]["name"] == "贡嘎"
        assert "bearing" in target_step["targets"][0]
        assert target_step["targets"][0]["matched"] is True
