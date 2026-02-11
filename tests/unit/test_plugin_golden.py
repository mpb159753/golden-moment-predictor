"""GoldenMountainPlugin 单元测试

测试用例来源: implementation-plans/module-06-scorer-complex.md
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from gmp.core.models import (
    DataContext,
    Location,
    MoonStatus,
    ScoreResult,
    StargazingWindow,
    SunEvents,
    Target,
    Viewpoint,
)
from gmp.scorer.golden_mountain import GoldenMountainPlugin


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def plugin() -> GoldenMountainPlugin:
    """默认 sunrise 模式实例."""
    return GoldenMountainPlugin("sunrise_golden_mountain")


@pytest.fixture
def sunset_plugin() -> GoldenMountainPlugin:
    """sunset 模式实例."""
    return GoldenMountainPlugin("sunset_golden_mountain")


@pytest.fixture
def viewpoint() -> Viewpoint:
    """牛背山观景台 (含贡嘎 primary + 雅拉 secondary)."""
    return Viewpoint(
        id="niubei",
        name="牛背山",
        location=Location(lat=29.83, lon=102.35, altitude=3660),
        capabilities=["sunrise_golden_mountain", "sunset_golden_mountain", "stargazing"],
        targets=[
            Target(
                name="贡嘎",
                lat=29.60,
                lon=101.88,
                altitude=7556,
                weight="primary",
            ),
            Target(
                name="雅拉神山",
                lat=30.14,
                lon=101.77,
                altitude=5820,
                weight="secondary",
            ),
        ],
    )


def _make_context(
    viewpoint: Viewpoint,
    *,
    local_cloud: float = 20.0,
    light_path_combined: float = 8.0,
    target_high_cloud: float = 5.0,
    target_mid_cloud: float = 8.0,
) -> DataContext:
    """快速构建 DataContext 测试数据."""
    # 本地天气 DataFrame
    local_df = pd.DataFrame(
        [{"cloud_cover_total": local_cloud, "forecast_hour": 7}]
    )

    # 10 个光路检查点
    light_path = [
        {"low_cloud": light_path_combined * 0.4, "mid_cloud": light_path_combined * 0.6, "combined": light_path_combined}
        for _ in range(10)
    ]

    # 目标天气
    target_weather = {
        "贡嘎": pd.DataFrame(
            [{"high_cloud": target_high_cloud, "mid_cloud": target_mid_cloud}]
        ),
    }

    return DataContext(
        date=date(2026, 2, 11),
        viewpoint=viewpoint,
        local_weather=local_df,
        light_path_weather=light_path,
        target_weather=target_weather,
    )


# ======================================================================
# check_trigger 测试
# ======================================================================


class TestCheckTrigger:
    """GoldenMountainPlugin.check_trigger 测试."""

    def test_trigger_positive(self, plugin: GoldenMountainPlugin):
        """总云22%, 有 matched_targets → True."""
        l1_data = {
            "cloud_cover_total": 22,
            "matched_targets": [{"name": "贡嘎"}],
        }
        assert plugin.check_trigger(l1_data) is True

    def test_trigger_no_target(self, plugin: GoldenMountainPlugin):
        """总云22%, matched_targets=[] → False."""
        l1_data = {
            "cloud_cover_total": 22,
            "matched_targets": [],
        }
        assert plugin.check_trigger(l1_data) is False

    def test_trigger_overcast(self, plugin: GoldenMountainPlugin):
        """总云85% → False."""
        l1_data = {
            "cloud_cover_total": 85,
            "matched_targets": [{"name": "贡嘎"}],
        }
        assert plugin.check_trigger(l1_data) is False

    def test_trigger_boundary_79(self, plugin: GoldenMountainPlugin):
        """总云79% (刚好 < 80) → True."""
        l1_data = {
            "cloud_cover_total": 79,
            "matched_targets": [{"name": "贡嘎"}],
        }
        assert plugin.check_trigger(l1_data) is True

    def test_trigger_boundary_80(self, plugin: GoldenMountainPlugin):
        """总云80% (不 < 80) → False."""
        l1_data = {
            "cloud_cover_total": 80,
            "matched_targets": [{"name": "贡嘎"}],
        }
        assert plugin.check_trigger(l1_data) is False


# ======================================================================
# score 测试
# ======================================================================


class TestScore:
    """GoldenMountainPlugin.score 评分测试."""

    def test_score_recommended(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """设计文档示例: 光路8%, 目标13%, 本地22% → score=87, Recommended."""
        ctx = _make_context(
            viewpoint,
            light_path_combined=8.0,
            target_high_cloud=5.0,
            target_mid_cloud=8.0,  # 合计 13%
            local_cloud=22.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 87  # 35+32+20
        assert result.status == "Recommended"
        assert result.breakdown["light_path"]["score"] == 35
        assert result.breakdown["target_visible"]["score"] == 32
        assert result.breakdown["local_clear"]["score"] == 20

    def test_score_perfect(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """光路0%, 目标5%, 本地10% → score=100, Perfect."""
        ctx = _make_context(
            viewpoint,
            light_path_combined=0.0,
            target_high_cloud=2.0,
            target_mid_cloud=3.0,  # 合计 5%
            local_cloud=10.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 100  # 35+40+25
        assert result.status == "Perfect"

    def test_veto_light_path(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """光路60% → S_light=0 → 总分0 (光路否决)."""
        ctx = _make_context(
            viewpoint,
            light_path_combined=60.0,
            target_high_cloud=2.0,
            target_mid_cloud=3.0,
            local_cloud=10.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 0
        assert result.breakdown["light_path"]["score"] == 0

    def test_veto_target(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """目标50% (>30%) → S_target=0 → 总分0 (目标否决)."""
        ctx = _make_context(
            viewpoint,
            light_path_combined=5.0,
            target_high_cloud=30.0,
            target_mid_cloud=20.0,  # 合计 50%
            local_cloud=10.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 0
        assert result.breakdown["target_visible"]["score"] == 0

    def test_veto_local(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """本地90% (>80%) → S_local=0 → 总分0 (本地否决)."""
        ctx = _make_context(
            viewpoint,
            light_path_combined=5.0,
            target_high_cloud=2.0,
            target_mid_cloud=3.0,
            local_cloud=90.0,
        )
        result = plugin.score(ctx)

        assert result.total_score == 0
        assert result.breakdown["local_clear"]["score"] == 0

    def test_sunset_variant(self, sunset_plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """sunset 模式: event_type 正确，评分逻辑相同."""
        assert sunset_plugin.event_type == "sunset_golden_mountain"

        ctx = _make_context(
            viewpoint,
            light_path_combined=8.0,
            target_high_cloud=5.0,
            target_mid_cloud=8.0,
            local_cloud=22.0,
        )
        result = sunset_plugin.score(ctx)

        # 同一数据，评分结果应与 sunrise 相同
        assert result.total_score == 87
        assert result.status == "Recommended"

    def test_no_light_path_data(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """无光路数据 → 光路得分0 → 总分0."""
        ctx = DataContext(
            date=date(2026, 2, 11),
            viewpoint=viewpoint,
            local_weather=pd.DataFrame(
                [{"cloud_cover_total": 10, "forecast_hour": 7}]
            ),
            light_path_weather=None,
            target_weather={
                "贡嘎": pd.DataFrame([{"high_cloud": 5, "mid_cloud": 3}])
            },
        )
        result = plugin.score(ctx)
        assert result.total_score == 0

    def test_no_primary_target(self, plugin: GoldenMountainPlugin):
        """无 primary 目标 → 目标得分0 → 总分0."""
        vp = Viewpoint(
            id="test",
            name="测试点",
            location=Location(lat=29.83, lon=102.35, altitude=3660),
            capabilities=["sunrise_golden_mountain"],
            targets=[
                Target(name="雅拉", lat=30.14, lon=101.77, altitude=5820, weight="secondary"),
            ],
        )
        ctx = _make_context(vp, light_path_combined=5.0, local_cloud=10.0)
        result = plugin.score(ctx)
        assert result.total_score == 0


# ======================================================================
# 维度得分阶梯测试
# ======================================================================


class TestLightPathThresholds:
    """光路通畅阶梯映射验证."""

    def test_le_10_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, light_path_combined=10.0)
        result = plugin.score(ctx)
        assert result.breakdown["light_path"]["score"] == 35

    def test_10_to_20_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, light_path_combined=15.0)
        result = plugin.score(ctx)
        assert result.breakdown["light_path"]["score"] == 30

    def test_20_to_30_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, light_path_combined=25.0)
        result = plugin.score(ctx)
        assert result.breakdown["light_path"]["score"] == 20

    def test_30_to_50_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, light_path_combined=40.0)
        result = plugin.score(ctx)
        assert result.breakdown["light_path"]["score"] == 10

    def test_over_50_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, light_path_combined=55.0)
        result = plugin.score(ctx)
        assert result.breakdown["light_path"]["score"] == 0


class TestTargetVisibleThresholds:
    """目标可见阶梯映射验证 (T1 修复)."""

    def test_le_10_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """高+中云 ≤10% → 40."""
        ctx = _make_context(viewpoint, target_high_cloud=3.0, target_mid_cloud=5.0)  # 合计 8%
        result = plugin.score(ctx)
        assert result.breakdown["target_visible"]["score"] == 40

    def test_10_to_20_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """高+中云 15% (10-20%) → 32."""
        ctx = _make_context(viewpoint, target_high_cloud=7.0, target_mid_cloud=8.0)  # 合计 15%
        result = plugin.score(ctx)
        assert result.breakdown["target_visible"]["score"] == 32

    def test_20_to_30_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """高+中云 25% (20-30%) → 22."""
        ctx = _make_context(viewpoint, target_high_cloud=12.0, target_mid_cloud=13.0)  # 合计 25%
        result = plugin.score(ctx)
        assert result.breakdown["target_visible"]["score"] == 22

    def test_over_30_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        """高+中云 35% (>30%) → 0."""
        ctx = _make_context(viewpoint, target_high_cloud=20.0, target_mid_cloud=15.0)  # 合计 35%
        result = plugin.score(ctx)
        assert result.breakdown["target_visible"]["score"] == 0


class TestLocalClearThresholds:
    """本地通透阶梯映射验证."""

    def test_le_15_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, local_cloud=15.0)
        result = plugin.score(ctx)
        assert result.breakdown["local_clear"]["score"] == 25

    def test_15_to_30_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, local_cloud=25.0)
        result = plugin.score(ctx)
        assert result.breakdown["local_clear"]["score"] == 20

    def test_30_to_50_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, local_cloud=40.0)
        result = plugin.score(ctx)
        assert result.breakdown["local_clear"]["score"] == 12

    def test_50_to_80_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, local_cloud=60.0)
        result = plugin.score(ctx)
        assert result.breakdown["local_clear"]["score"] == 5

    def test_over_80_percent(self, plugin: GoldenMountainPlugin, viewpoint: Viewpoint):
        ctx = _make_context(viewpoint, local_cloud=85.0)
        result = plugin.score(ctx)
        assert result.breakdown["local_clear"]["score"] == 0


class TestDimensions:
    def test_dimensions(self, plugin: GoldenMountainPlugin):
        assert plugin.dimensions() == ["light_path", "target_visible", "local_clear"]
