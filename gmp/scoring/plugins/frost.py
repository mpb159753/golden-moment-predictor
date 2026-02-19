"""gmp/scoring/plugins/frost.py — 雾凇评分 Plugin

FrostPlugin 是 L1 Plugin，仅需本地天气数据。
当温度低于触发阈值时，综合评估温度、湿度、风速和云量来判定雾凇形成概率。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gmp.core.models import ScoreResult, score_to_status
from gmp.scoring.models import DataRequirement

if TYPE_CHECKING:
    from gmp.scoring.models import DataContext


class FrostPlugin:
    """雾凇评分 Plugin"""

    def __init__(self, config: dict) -> None:
        self._config = config
        self._weights = config.get("weights", {
            "temperature": 40, "moisture": 30, "wind": 20, "cloud": 10,
        })
        self._thresholds = config.get("thresholds", {})

    @property
    def event_type(self) -> str:
        return "frost"

    @property
    def display_name(self) -> str:
        return "雾凇"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement(
            needs_l2_target=False,
            needs_l2_light_path=False,
            needs_astro=False,
        )

    def dimensions(self) -> list[str]:
        return ["temperature", "moisture", "wind", "cloud"]

    def score(self, context: DataContext) -> ScoreResult | None:
        """评分入口

        1. 安全检查 (剔除降水/能见度不合格的时段)
        2. 触发判定 (温度 < trigger.max_temperature)
        3. 各维度评分
        4. 返回 ScoreResult
        """
        weather = context.local_weather.copy()

        # ── 安全检查 ──
        safety = self._config.get("safety", {})
        precip_thresh = safety.get("precip_threshold", 30)
        vis_thresh = safety.get("visibility_threshold", 1)

        # 降水概率筛选
        if "precipitation_probability" in weather.columns:
            weather = weather[
                weather["precipitation_probability"] <= precip_thresh
            ]

        # 能见度筛选 (阈值单位 km, 数据单位 m)
        if "visibility" in weather.columns:
            weather = weather[
                weather["visibility"] >= vis_thresh * 1000
            ]

        if weather.empty:
            return None

        # ── 触发判定 ──
        trigger = self._config.get("trigger", {})
        max_temp = trigger.get("max_temperature", 2.0)
        avg_temp = weather["temperature_2m"].mean()

        if avg_temp >= max_temp:
            return None

        # ── 各维度评分 ──
        temp_score = self._score_temperature(avg_temp)
        moisture_score = self._score_moisture(weather)
        wind_score = self._score_wind(weather)
        cloud_score = self._score_cloud(weather)

        total = temp_score + moisture_score + wind_score + cloud_score

        breakdown = {
            "temperature": {
                "score": temp_score,
                "max": self._weights["temperature"],
                "detail": f"avg_temp={avg_temp:.1f}°C",
            },
            "moisture": {
                "score": moisture_score,
                "max": self._weights["moisture"],
                "detail": "visibility-based",
            },
            "wind": {
                "score": wind_score,
                "max": self._weights["wind"],
                "detail": "wind speed scoring",
            },
            "cloud": {
                "score": cloud_score,
                "max": self._weights["cloud"],
                "detail": "cloud cover scoring",
            },
        }

        return ScoreResult(
            event_type="frost",
            total_score=total,
            status=score_to_status(total),
            time_window="06:00 - 12:00",
            breakdown=breakdown,
        )

    # ── 私有评分方法 ──

    def _score_temperature(self, temp: float) -> int:
        """温度区间评分 (半开区间: lo <= temp < hi)"""
        temp_ranges = self._thresholds.get("temp_ranges", {})
        for _name, cfg in temp_ranges.items():
            lo, hi = cfg["range"]
            if lo <= temp < hi:
                return cfg["score"]
        return 0

    def _score_moisture(self, weather) -> int:
        """能见度/湿度评分: 低能见度 = 高湿度 = 利于雾凇"""
        avg_vis_km = weather["visibility"].mean() / 1000.0
        breakpoints = self._thresholds.get("visibility_km", [5, 10, 20])
        scores = self._thresholds.get("visibility_scores", [30, 20, 10, 5])

        for i, bp in enumerate(breakpoints):
            if avg_vis_km < bp:
                return scores[i]
        return scores[-1]

    def _score_wind(self, weather) -> int:
        """风速评分: 低风速利于雾凇"""
        avg_wind = weather["wind_speed_10m"].mean()
        breakpoints = self._thresholds.get("wind_speed", [3, 5, 10])
        scores = self._thresholds.get("wind_scores", [20, 15, 10, 0])

        for i, bp in enumerate(breakpoints):
            if avg_wind < bp:
                return scores[i]
        return scores[-1]

    def _score_cloud(self, weather) -> int:
        """云量评分"""
        avg_cloud = weather["cloud_cover_low"].mean()
        cloud_pct = self._thresholds.get("cloud_pct", {})

        for _name, cfg in cloud_pct.items():
            lo, hi = cfg["range"]
            if lo <= avg_cloud <= hi:
                return cfg["score"]
        return 0
