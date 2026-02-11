"""CloudSeaPlugin — 云海评分

设计依据: design/03-scoring-plugins.md §3.7
评分公式: Score = (Score_gap + Score_density) × Factor_mid_cloud + Score_wind
"""

from __future__ import annotations

from gmp.core.models import DataContext, DataRequirement, ScoreResult
from gmp.scorer.plugin import extract_weather_value, score_to_status


class CloudSeaPlugin:
    """云海评分插件 — 仅需 L1 本地天气"""

    event_type = "cloud_sea"
    display_name = "云海"
    data_requirement = DataRequirement()  # 仅需 L1

    # ------------------------------------------------------------------
    # 触发判定
    # ------------------------------------------------------------------

    def check_trigger(self, l1_data: dict) -> bool:
        """触发条件: 云底高度 < 站点海拔."""
        cloud_base = l1_data.get("cloud_base_altitude", float("inf"))
        site_alt = l1_data.get("site_altitude", 0)
        return cloud_base < site_alt

    # ------------------------------------------------------------------
    # 评分
    # ------------------------------------------------------------------

    def score(self, context: DataContext) -> ScoreResult:
        """基于 DataContext 评分。

        从 local_weather 中提取评分所需字段。
        """
        weather = context.local_weather
        site_alt = context.viewpoint.location.altitude

        # 提取代表性时刻数据 (取首行或均值)
        cloud_base = extract_weather_value(weather, "cloud_base_altitude", float("inf"))
        low_cloud = extract_weather_value(weather, "cloud_cover_low", 0)
        mid_cloud = extract_weather_value(weather, "cloud_cover_mid", 0)
        wind = extract_weather_value(weather, "wind_speed_10m", 0)

        gap = site_alt - cloud_base

        # 维度 1: 高差 (50 分)
        gap_score = self._score_gap(gap)
        # 维度 2: 密度 (30 分)
        density_score = self._score_density(low_cloud)
        # 中云修正因子
        mid_factor = self._mid_cloud_factor(mid_cloud)
        # 维度 3: 稳定 (风速, 20 分)
        wind_score = self._score_wind(wind)

        total = int((gap_score + density_score) * mid_factor + wind_score)
        total = max(0, min(100, total))

        breakdown = {
            "gap": {
                "score": gap_score,
                "max": 50,
                "detail": f"高差{gap:.0f}m",
            },
            "density": {
                "score": density_score,
                "max": 30,
                "detail": f"低云{low_cloud:.0f}%",
            },
            "mid_structure": {
                "factor": mid_factor,
                "detail": f"中云{mid_cloud:.0f}%",
            },
            "wind": {
                "score": wind_score,
                "max": 20,
                "detail": f"风速{wind:.1f}km/h",
            },
        }

        return ScoreResult(
            total_score=total,
            status=score_to_status(total),
            breakdown=breakdown,
        )

    def dimensions(self) -> list[str]:
        return ["gap", "density", "mid_structure", "wind"]

    # ------------------------------------------------------------------
    # 私有评分方法
    # ------------------------------------------------------------------

    @staticmethod
    def _score_gap(gap: float) -> int:
        """高差得分 (满分 50)."""
        if gap > 800:
            return 50
        if gap > 500:
            return 40
        if gap > 200:
            return 20
        if gap > 0:
            return 10
        return 0

    @staticmethod
    def _score_density(low_cloud: float) -> int:
        """密度得分 (满分 30).

        设计文档阶梯: >80%: 30, >50%: 20, <30%: 5
        30-50% 区间归入碎云档 (5 分) — 此区间低云覆盖不足以形成
        连续可观赏的云海，视觉效果接近碎云。
        """
        if low_cloud > 80:
            return 30
        if low_cloud > 50:
            return 20
        return 5  # ≤50% 碎云

    @staticmethod
    def _mid_cloud_factor(mid_cloud: float) -> float:
        """中云修正因子."""
        if mid_cloud <= 30:
            return 1.0
        if mid_cloud <= 60:
            return 0.7
        return 0.3

    @staticmethod
    def _score_wind(wind: float) -> int:
        """风速稳定得分 (满分 20)."""
        if wind < 10:
            return 20
        # 每增 5km/h 扣 5 分
        deduction = int((wind - 10) / 5) * 5 + 5
        return max(0, 20 - deduction)
