"""gmp/scoring/plugins/stargazing.py — 观星评分 Plugin

StargazingPlugin 是 L2 Plugin，需要天文数据 (needs_astro)。
基于月相、云量、风速等天文气象数据计算观星条件评分。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gmp.core.models import ScoreResult, score_to_status
from gmp.scoring.models import DataRequirement

if TYPE_CHECKING:
    from gmp.scoring.models import DataContext


class StargazingPlugin:
    """观星评分 Plugin"""

    def __init__(self, config: dict) -> None:
        self._config = config

    @property
    def event_type(self) -> str:
        return "stargazing"

    @property
    def display_name(self) -> str:
        return "观星"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement(needs_astro=True)

    def dimensions(self) -> list[str]:
        return ["base", "cloud", "wind"]

    def score(self, context: DataContext) -> ScoreResult | None:
        """评分入口

        1. 防御性检查 stargazing_window
        2. 夜间平均云量触发判定
        3. 基准分（按 quality）
        4. 云量扣分
        5. 风速扣分
        6. 钳制 [0, 100]
        """
        # ── 防御性检查 ──
        window = context.stargazing_window
        if window is None:
            return None

        weather = context.local_weather

        # ── 夜间平均云量触发判定 ──
        trigger = self._config.get("trigger", {})
        max_cloud = trigger.get("max_night_cloud_cover", 70)
        avg_cloud = weather["cloud_cover"].mean()

        if avg_cloud >= max_cloud:
            return None

        # ── 基准分 ──
        base = self._get_base_score(window.quality, context)

        # ── 云量扣分 ──
        cloud_factor = self._config.get("cloud_penalty_factor", 0.8)
        cloud_deduction = avg_cloud * cloud_factor

        # ── 风速扣分 ──
        wind_deduction = self._get_wind_deduction(weather)

        # ── 最终分数 ──
        raw_score = base - cloud_deduction - wind_deduction
        total = max(0, min(100, int(raw_score)))

        # ── 时间窗口 ──
        time_window = self._format_time_window(window)

        breakdown = {
            "base": {
                "score": int(base),
                "max": 100,
                "detail": f"quality={window.quality}",
            },
            "cloud": {
                "score": int(-cloud_deduction),
                "max": 0,
                "detail": f"avg_cloud={avg_cloud:.1f}%",
            },
            "wind": {
                "score": int(-wind_deduction),
                "max": 0,
                "detail": "wind deduction",
            },
        }

        return ScoreResult(
            event_type="stargazing",
            total_score=total,
            status=score_to_status(total),
            breakdown=breakdown,
            time_window=time_window,
        )

    def _get_base_score(self, quality: str, context: DataContext) -> float:
        """根据 window.quality 获取基准分"""
        if quality == "optimal":
            return self._config.get("base_optimal", 100)
        elif quality == "good":
            return self._config.get("base_good", 90)
        elif quality == "partial":
            return self._config.get("base_partial", 70)
        else:
            # poor: base = base_poor - phase × cloud_penalty_factor
            moon = context.moon_status
            phase = moon.phase if moon else 0
            base_poor = self._config.get("base_poor", 100)
            factor = self._config.get("cloud_penalty_factor", 0.8)
            return base_poor - phase * factor

    def _get_wind_deduction(self, weather) -> float:
        """风速阶梯扣分"""
        avg_wind = weather["wind_speed_10m"].mean()
        thresholds = self._config.get("wind_thresholds", {})

        severe = thresholds.get("severe", {})
        moderate = thresholds.get("moderate", {})

        if avg_wind > severe.get("speed", 40):
            return severe.get("penalty", 30)
        elif avg_wind > moderate.get("speed", 20):
            return moderate.get("penalty", 10)
        return 0

    def _format_time_window(self, window) -> str:
        """格式化时间窗口"""
        if window.optimal_start and window.optimal_end:
            start = window.optimal_start.strftime("%H:%M")
            end = window.optimal_end.strftime("%H:%M")
            return f"{start} - {end}"
        return ""
