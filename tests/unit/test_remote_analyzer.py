"""L2 远程滤网 (RemoteAnalyzer) 单元测试

验证:
- 目标可见性判定
- 光路通畅度判定
- 综合评分计算
"""

import pandas as pd
import pytest

from gmp.analyzer.remote_analyzer import RemoteAnalyzer
from gmp.core.config_loader import EngineConfig


@pytest.fixture
def config() -> EngineConfig:
    """默认引擎配置"""
    return EngineConfig()


@pytest.fixture
def analyzer(config: EngineConfig) -> RemoteAnalyzer:
    """默认 RemoteAnalyzer 实例"""
    return RemoteAnalyzer(config)


def _make_target_df(
    hour: int = 7,
    cloud_cover_high: float = 5,
    cloud_cover_medium: float = 5,
    **kwargs,
) -> pd.DataFrame:
    """创建目标天气 DataFrame"""
    row = {
        "forecast_hour": hour,
        "cloud_cover_high": cloud_cover_high,
        "cloud_cover_medium": cloud_cover_medium,
        "cloud_cover_low": 10,
        "cloud_cover_total": 20,
        "temperature_2m": -5.0,
    }
    row.update(kwargs)
    return pd.DataFrame([row])


def _make_light_path_points(
    count: int = 10,
    low_cloud: float = 5,
    mid_cloud: float = 3,
) -> list[dict]:
    """创建光路检查点数据"""
    return [
        {
            "point_name": f"LP_{i+1}",
            "low_cloud": low_cloud,
            "mid_cloud": mid_cloud,
            "combined": low_cloud + mid_cloud,
        }
        for i in range(count)
    ]


# ============================================================
# 目标可见性测试
# ============================================================


class TestTargetVisibility:
    """目标可见性测试"""

    def test_target_visible(self, analyzer: RemoteAnalyzer):
        """高+中云13% < 30% → visible=True"""
        target_df = _make_target_df(cloud_cover_high=8, cloud_cover_medium=5)
        context = {
            "target_weather": {"贡嘎主峰": target_df},
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": _make_light_path_points(),
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)

        targets = result.details["targets"]
        assert len(targets) == 1
        assert targets[0]["visible"] is True
        assert targets[0]["combined_cloud"] == pytest.approx(13.0)

    def test_target_obscured(self, analyzer: RemoteAnalyzer):
        """高+中云85% → visible=False"""
        target_df = _make_target_df(cloud_cover_high=50, cloud_cover_medium=35)
        context = {
            "target_weather": {"贡嘎主峰": target_df},
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": _make_light_path_points(),
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)

        targets = result.details["targets"]
        assert targets[0]["visible"] is False
        assert targets[0]["combined_cloud"] == pytest.approx(85.0)
        assert targets[0]["status"] == "遮挡"

    def test_target_borderline(self, analyzer: RemoteAnalyzer):
        """高+中云恰好 30% (不 < 30) → visible=False"""
        target_df = _make_target_df(cloud_cover_high=15, cloud_cover_medium=15)
        context = {
            "target_weather": {"贡嘎主峰": target_df},
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": _make_light_path_points(),
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)
        targets = result.details["targets"]
        assert targets[0]["visible"] is False

    def test_multiple_targets(self, analyzer: RemoteAnalyzer):
        """多目标: primary 可见, secondary 不可见"""
        context = {
            "target_weather": {
                "贡嘎主峰": _make_target_df(cloud_cover_high=5, cloud_cover_medium=5),
                "爱德嘉峰": _make_target_df(cloud_cover_high=40, cloud_cover_medium=30),
            },
            "target_weights": {
                "贡嘎主峰": "primary",
                "爱德嘉峰": "secondary",
            },
            "light_path_weather": _make_light_path_points(),
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)

        targets = {t["name"]: t for t in result.details["targets"]}
        assert targets["贡嘎主峰"]["visible"] is True
        assert targets["爱德嘉峰"]["visible"] is False

    def test_empty_target_data(self, analyzer: RemoteAnalyzer):
        """空目标数据 → visible=False"""
        result_info = analyzer._check_target_visibility(pd.DataFrame(), 7)
        assert result_info["visible"] is False
        assert result_info["status"] == "无数据"


# ============================================================
# 光路通畅度测试
# ============================================================


class TestLightPath:
    """光路通畅度测试"""

    def test_light_path_clear(self, analyzer: RemoteAnalyzer):
        """10点均值8% → clear=True"""
        light_points = _make_light_path_points(count=10, low_cloud=5, mid_cloud=3)
        context = {
            "target_weather": {"贡嘎主峰": _make_target_df()},
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": light_points,
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)

        lp = result.details["light_path"]
        assert lp["clear"] is True
        assert lp["avg_combined_cloud"] == pytest.approx(8.0)
        assert lp["status"] == "通畅"

    def test_light_path_blocked(self, analyzer: RemoteAnalyzer):
        """10点均值60% → clear=False"""
        light_points = _make_light_path_points(count=10, low_cloud=35, mid_cloud=25)
        context = {
            "target_weather": {"贡嘎主峰": _make_target_df()},
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": light_points,
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)

        lp = result.details["light_path"]
        assert lp["clear"] is False
        assert lp["avg_combined_cloud"] == pytest.approx(60.0)
        assert lp["status"] == "受阻"

    def test_light_path_borderline(self, analyzer: RemoteAnalyzer):
        """均值恰好 50% (不 < 50) → clear=False"""
        light_points = _make_light_path_points(count=10, low_cloud=25, mid_cloud=25)
        result_info = analyzer._check_light_path(light_points)
        assert result_info["clear"] is False

    def test_light_path_partially_clear(self, analyzer: RemoteAnalyzer):
        """基本通畅: 均值 30% → clear=True, status='基本通畅'"""
        light_points = _make_light_path_points(count=10, low_cloud=15, mid_cloud=15)
        result_info = analyzer._check_light_path(light_points)
        assert result_info["clear"] is True
        assert result_info["status"] == "基本通畅"

    def test_light_path_empty(self, analyzer: RemoteAnalyzer):
        """无光路数据 → clear=False"""
        result_info = analyzer._check_light_path([])
        assert result_info["clear"] is False
        assert result_info["status"] == "无光路数据"

    def test_light_path_max(self, analyzer: RemoteAnalyzer):
        """max_combined_cloud 正确计算"""
        light_points = _make_light_path_points(count=10, low_cloud=5, mid_cloud=3)
        # 第 5 个点设为高云量
        light_points[4] = {
            "point_name": "LP_5",
            "low_cloud": 40,
            "mid_cloud": 30,
            "combined": 70,
        }

        result_info = analyzer._check_light_path(light_points)
        assert result_info["max_combined_cloud"] == pytest.approx(70.0)
        # 均值 = (8*9 + 70) / 10 = (72 + 70) / 10 = 14.2
        assert result_info["avg_combined_cloud"] == pytest.approx(14.2)


# ============================================================
# 综合评分测试
# ============================================================


class TestRemoteScore:
    """L2 综合评分测试"""

    def test_perfect_conditions(self, analyzer: RemoteAnalyzer):
        """所有条件最优 → 高分"""
        context = {
            "target_weather": {
                "贡嘎主峰": _make_target_df(cloud_cover_high=3, cloud_cover_medium=2),
            },
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": _make_light_path_points(
                count=10, low_cloud=3, mid_cloud=2,
            ),
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)

        # 20 (基础) + 40 (光路 avg 5% < 25) + 25 (primary 可见) = 85
        # 无 secondary → 0 额外
        assert result.score >= 80

    def test_no_data(self, analyzer: RemoteAnalyzer):
        """无远程数据 → passed=False"""
        context = {
            "target_weather": {},
            "light_path_weather": [],
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)
        assert result.passed is False

    def test_primary_blocked_reduces_score(self, analyzer: RemoteAnalyzer):
        """primary 不可见 → 评分降低"""
        context_visible = {
            "target_weather": {
                "贡嘎主峰": _make_target_df(cloud_cover_high=5, cloud_cover_medium=5),
            },
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": _make_light_path_points(),
            "target_hour": 7,
        }

        context_blocked = {
            "target_weather": {
                "贡嘎主峰": _make_target_df(cloud_cover_high=50, cloud_cover_medium=40),
            },
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": _make_light_path_points(),
            "target_hour": 7,
        }

        result_good = analyzer.analyze(pd.DataFrame(), context_visible)
        result_bad = analyzer.analyze(pd.DataFrame(), context_blocked)

        assert result_good.score > result_bad.score

    def test_reason_includes_issues(self, analyzer: RemoteAnalyzer):
        """不通畅时 reason 包含问题描述"""
        context = {
            "target_weather": {
                "贡嘎主峰": _make_target_df(cloud_cover_high=50, cloud_cover_medium=40),
            },
            "target_weights": {"贡嘎主峰": "primary"},
            "light_path_weather": _make_light_path_points(
                count=10, low_cloud=30, mid_cloud=25,
            ),
            "target_hour": 7,
        }

        result = analyzer.analyze(pd.DataFrame(), context)
        assert "不可见" in result.reason
        assert "不通畅" in result.reason
