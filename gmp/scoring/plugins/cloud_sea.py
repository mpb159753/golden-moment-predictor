"""gmp/scoring/plugins/cloud_sea.py — 云海评分 Plugin

L1 Plugin：仅需本地天气数据 (DataContext.local_weather)。
评分公式: Score = (Score_gap + Score_density) × Factor_mid + Score_wind
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from gmp.core.models import ScoreResult, score_to_status
from gmp.scoring.models import DataRequirement

if TYPE_CHECKING:
    from gmp.scoring.models import DataContext


class CloudSeaPlugin:
    """云海评分 Plugin"""

    def __init__(self, config: dict, safety_config: dict) -> None:
        """
        Args:
            config: 来自 engine_config.yaml → scoring.cloud_sea
            safety_config: 来自 engine_config.yaml → safety
        """
        self._config = config
        self._safety = safety_config
        self._weights = config["weights"]
        self._thresholds = config["thresholds"]

    @property
    def event_type(self) -> str:
        return "cloud_sea"

    @property
    def display_name(self) -> str:
        return "云海"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement()

    def dimensions(self) -> list[str]:
        return ["gap", "density", "mid_structure", "wind"]

    def score(self, context: DataContext) -> ScoreResult | None:
        """云海评分主逻辑

        1. 安全检查 — 剔除不安全时段
        2. 触发判定 — 云底必须低于站点海拔
        3. 计算评分
        4. 返回 ScoreResult
        """
        weather = self._apply_safety_filter(context.local_weather)
        if weather.empty:
            return None

        viewpoint_alt = context.viewpoint.location.altitude
        # 使用安全行的平均云底高度做触发判定
        avg_cloud_base = weather["cloud_base_altitude"].mean()

        # 触发判定: 云底必须低于站点
        if avg_cloud_base >= viewpoint_alt:
            return None

        # 计算各子维度（基于安全行均值）
        gap = viewpoint_alt - avg_cloud_base
        low_cloud = weather["cloud_cover_low"].mean()
        mid_cloud = weather["cloud_cover_medium"].mean()
        wind = weather["wind_speed_10m"].mean()

        score_gap = self._score_gap(gap)
        score_density = self._score_density(low_cloud)
        factor_mid = self._mid_cloud_factor(mid_cloud)
        score_wind = self._score_wind(wind)

        total = int(round((score_gap + score_density) * factor_mid + score_wind))
        total = max(0, min(100, total))

        return ScoreResult(
            event_type="cloud_sea",
            total_score=total,
            status=score_to_status(total),
            breakdown={
                "gap": {
                    "score": score_gap,
                    "max": self._weights["gap"],
                    "detail": f"gap={gap:.0f}m",
                },
                "density": {
                    "score": score_density,
                    "max": self._weights["density"],
                    "detail": f"low_cloud={low_cloud:.0f}%",
                },
                "mid_structure": {
                    "score": factor_mid,
                    "max": 1.0,
                    "detail": f"mid_cloud={mid_cloud:.0f}%, factor={factor_mid}",
                },
                "wind": {
                    "score": score_wind,
                    "max": self._weights["wind"],
                    "detail": f"wind={wind:.1f}km/h",
                },
            },
        )

    # ==================== 子维度评分 ====================

    @staticmethod
    def _rated_score(
        value: float,
        thresholds: list[float],
        scores: list[int | float],
        *,
        ascending: bool = False,
    ) -> int | float:
        """通用阶梯评分：按阈值列表 + 分值列表返回得分。

        Args:
            value: 待评分的数值
            thresholds: 阈值列表（降序排列）
            scores: 分值列表，长度 = len(thresholds) + 1（最后一个为兜底）
            ascending: False → value > threshold 命中 (gap/density);
                       True  → value < threshold 命中 (wind)
        """
        for t, s in zip(thresholds, scores):
            if (not ascending and value > t) or (ascending and value < t):
                return s
        return scores[-1]

    def _score_gap(self, gap: float) -> int:
        """高差 → gap 维度得分"""
        return self._rated_score(
            gap,
            self._thresholds["gap_meters"],
            self._thresholds["gap_scores"],
        )

    def _score_density(self, low_cloud_pct: float) -> int:
        """低云密度 → density 维度得分"""
        return self._rated_score(
            low_cloud_pct,
            self._thresholds["density_pct"],
            self._thresholds["density_scores"],
        )

    def _mid_cloud_factor(self, mid_cloud_pct: float) -> float:
        """中云覆盖 → 惩罚系数"""
        factors = self._thresholds["mid_cloud_factors"]  # [1.0, 0.7, 0.3]
        thresholds = self._thresholds["mid_cloud_penalty"]  # [30, 60]
        # factors[0]=≤30%→1.0, factors[1]=>30%→0.7, factors[2]=>60%→0.3
        if mid_cloud_pct > thresholds[1]:
            return factors[2]
        if mid_cloud_pct > thresholds[0]:
            return factors[1]
        return factors[0]

    def _score_wind(self, wind_speed: float) -> int:
        """风速 → wind 维度得分"""
        return self._rated_score(
            wind_speed,
            self._thresholds["wind_speed"],
            self._thresholds["wind_scores"],
            ascending=True,
        )

    # ==================== 安全过滤 ====================

    def _apply_safety_filter(self, weather: pd.DataFrame) -> pd.DataFrame:
        """剔除不安全时段（降水概率过高或能见度过低）"""
        precip_threshold = self._safety["precip_threshold"]
        vis_threshold = self._safety["visibility_threshold"]

        safe_mask = (
            (weather["precipitation_probability"] <= precip_threshold)
            & (weather["visibility"] >= vis_threshold)
        )
        return weather[safe_mask].reset_index(drop=True)
