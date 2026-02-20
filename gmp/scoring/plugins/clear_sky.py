"""gmp/scoring/plugins/clear_sky.py — 晴天评分 Plugin

ClearSkyPlugin 是 L1 Plugin，仅需本地天气数据。
当平均总云量低于触发阈值时，综合评估云量、降水和能见度来判定晴天质量。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gmp.core.models import ScoreResult, score_to_status
from gmp.scoring.models import DataRequirement

if TYPE_CHECKING:
    from gmp.scoring.models import DataContext


class ClearSkyPlugin:
    """晴天评分 — L1 Plugin，仅需本地天气"""

    def __init__(self, config: dict) -> None:
        self._config = config
        self._weights = config.get("weights", {
            "cloud_cover": 50, "precipitation": 25, "visibility": 25,
        })
        self._thresholds = config.get("thresholds", {})

    @property
    def event_type(self) -> str:
        return "clear_sky"

    @property
    def display_name(self) -> str:
        return "晴天"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement(
            needs_l2_target=False,
            needs_l2_light_path=False,
            needs_astro=False,
        )

    def dimensions(self) -> list[str]:
        return ["cloud_cover", "precipitation", "visibility"]

    def score(self, context: DataContext) -> ScoreResult | None:
        """评分逻辑:
        1. 计算日间平均总云量，≥ trigger.max_cloud_cover 返回 None
        2. 按 cloud_cover / precipitation / visibility 三维度打分
        3. 加权求和
        """
        weather = context.local_weather.copy()

        if weather.empty:
            return None

        # ── 触发判定 ──
        trigger = self._config.get("trigger", {})
        max_cloud = trigger.get("max_cloud_cover", 80)
        avg_cloud = weather["cloud_cover_total"].mean()

        if avg_cloud >= max_cloud:
            return None

        # ── 各维度评分 ──
        cloud_score = self._score_cloud(avg_cloud)
        precip_score = self._score_precipitation(weather)
        vis_score = self._score_visibility(weather)

        total = cloud_score + precip_score + vis_score

        breakdown = {
            "cloud_cover": {
                "score": cloud_score,
                "max": self._weights["cloud_cover"],
                "detail": f"avg_cloud={avg_cloud:.1f}%",
            },
            "precipitation": {
                "score": precip_score,
                "max": self._weights["precipitation"],
                "detail": "precipitation probability scoring",
            },
            "visibility": {
                "score": vis_score,
                "max": self._weights["visibility"],
                "detail": "visibility scoring",
            },
        }

        return ScoreResult(
            event_type="clear_sky",
            total_score=total,
            status=score_to_status(total),
            time_window="06:00 - 18:00",
            breakdown=breakdown,
        )

    # ── 私有评分方法 ──

    def _score_cloud(self, avg_cloud: float) -> int:
        """云量阶梯评分: 云量越低越好"""
        breakpoints = self._thresholds.get("cloud_pct", [10, 30, 50, 70])
        scores = self._thresholds.get("cloud_scores", [50, 40, 25, 10, 0])

        for i, bp in enumerate(breakpoints):
            if avg_cloud <= bp:
                return scores[i]
        return scores[-1]

    def _score_precipitation(self, weather) -> int:
        """降水概率阶梯评分: 降水越低越好"""
        avg_precip = weather["precipitation_probability"].mean()
        breakpoints = self._thresholds.get("precip_pct", [10, 30, 50])
        scores = self._thresholds.get("precip_scores", [25, 20, 10, 0])

        for i, bp in enumerate(breakpoints):
            if avg_precip <= bp:
                return scores[i]
        return scores[-1]

    def _score_visibility(self, weather) -> int:
        """能见度阶梯评分: 能见度越高越好 (降序阈值)"""
        avg_vis_km = weather["visibility"].mean() / 1000.0
        breakpoints = self._thresholds.get("visibility_km", [30, 15, 5])
        scores = self._thresholds.get("visibility_scores", [25, 20, 10, 5])

        for i, bp in enumerate(breakpoints):
            if avg_vis_km >= bp:
                return scores[i]
        return scores[-1]
