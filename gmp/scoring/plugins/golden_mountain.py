"""gmp/scoring/plugins/golden_mountain.py — 日照金山评分 Plugin

L2 Plugin：需要目标山峰天气、光路检查点天气、天文数据。
支持 sunrise/sunset 双实例，包含目标山峰方位角匹配、光路云量评估、
阶梯评分与一票否决机制。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gmp.core.models import ScoreResult, Target, score_to_status
from gmp.data.geo_utils import GeoUtils
from gmp.scoring.models import DataRequirement

if TYPE_CHECKING:
    from gmp.scoring.models import DataContext


class GoldenMountainPlugin:
    """日照金山评分 Plugin — 支持 sunrise/sunset 双实例"""

    def __init__(self, event_type: str, config: dict) -> None:
        """
        Args:
            event_type: "sunrise_golden_mountain" 或 "sunset_golden_mountain"
            config: 来自 engine_config.yaml → scoring.golden_mountain
        """
        self._event_type = event_type
        self._config = config
        self._weights = config["weights"]
        self._thresholds = config["thresholds"]
        self._trigger = config["trigger"]
        self._veto_threshold = config["veto_threshold"]

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def display_name(self) -> str:
        return "日照金山"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement(
            needs_l2_target=True,
            needs_l2_light_path=True,
            needs_astro=True,
        )

    def dimensions(self) -> list[str]:
        return ["light_path", "target_visible", "local_clear"]

    def score(self, context: DataContext) -> ScoreResult | None:
        """日照金山评分主逻辑

        1. 安全检查 (天文数据)
        2. 触发判定: 总云量 ≥ max_cloud_cover → None
        3. 确定日出/日落方位角
        4. 筛选适用 Target
        5. 无适用 Target → None
        6. 计算光路云量、目标可见性、本地通透
        7. 阶梯评分 + 一票否决
        8. 生成 ScoreResult
        """
        # 1. 安全检查
        if context.sun_events is None:
            return None

        # 2. 触发判定: 总云量检查
        avg_cloud = context.local_weather["cloud_cover_total"].mean()
        max_cloud = self._trigger["max_cloud_cover"]
        if avg_cloud >= max_cloud:
            return None

        # 3. 确定方位角
        sun_azimuth = self._get_sun_azimuth(context)

        # 4. 筛选适用 Target
        applicable_targets = [
            t
            for t in context.viewpoint.targets
            if self._is_target_applicable(t, sun_azimuth, context)
        ]

        # 5. 无适用 Target
        if not applicable_targets:
            return None

        # 6. 计算三维度云量
        light_path_cloud = self._calc_light_path_cloud(context)
        target_cloud = self._calc_target_cloud(applicable_targets, context)
        local_cloud = avg_cloud

        # 7. 阶梯评分
        s_light = self._score_light_path(light_path_cloud)
        s_target = self._score_target(target_cloud)
        s_local = self._score_local(local_cloud)

        # 一票否决
        if s_light <= self._veto_threshold or s_target <= self._veto_threshold or s_local <= self._veto_threshold:
            total = 0
        else:
            total = s_light + s_target + s_local

        total = max(0, min(100, total))

        # 8. 生成结果
        highlights = []
        warnings = []
        if total >= 80:
            highlights.append("日照金山条件优秀")
        if light_path_cloud > 50:
            warnings.append(f"光路云量偏高 ({light_path_cloud:.0f}%)")
        if target_cloud > 50:
            warnings.append(f"目标云量偏高 ({target_cloud:.0f}%)")

        return ScoreResult(
            event_type=self._event_type,
            total_score=total,
            status=score_to_status(total),
            breakdown={
                "light_path": {
                    "score": s_light,
                    "max": self._weights["light_path"],
                    "detail": f"cloud={light_path_cloud:.0f}%",
                },
                "target_visible": {
                    "score": s_target,
                    "max": self._weights["target_visible"],
                    "detail": f"cloud={target_cloud:.0f}%",
                },
                "local_clear": {
                    "score": s_local,
                    "max": self._weights["local_clear"],
                    "detail": f"cloud={local_cloud:.0f}%",
                },
            },
            highlights=highlights,
            warnings=warnings,
        )

    # ==================== 私有方法 ====================

    def _get_sun_azimuth(self, context: DataContext) -> float:
        """根据 event_type 选择日出/日落方位角"""
        if "sunrise" in self._event_type:
            return context.sun_events.sunrise_azimuth
        return context.sun_events.sunset_azimuth

    def _is_target_applicable(
        self,
        target: Target,
        sun_azimuth: float,
        context: DataContext,
    ) -> bool:
        """判断目标是否适用当前事件"""
        event_key = "sunrise" if "sunrise" in self._event_type else "sunset"

        # 1. 显式声明
        if target.applicable_events is not None:
            return event_key in target.applicable_events

        # 2. 自动计算: 方位角匹配
        vp = context.viewpoint.location
        bearing = GeoUtils.calculate_bearing(vp.lat, vp.lon, target.lat, target.lon)
        return GeoUtils.is_opposite_direction(bearing, sun_azimuth)

    def _calc_light_path_cloud(self, context: DataContext) -> float:
        """计算光路云量: 从 context.light_path_weather 取 (low_cloud + mid_cloud) 的均值"""
        if not context.light_path_weather:
            return 0.0

        point_avgs = []
        for point in context.light_path_weather:
            weather = point["weather"]
            low = weather["cloud_cover_low"].mean()
            mid = weather["cloud_cover_medium"].mean()
            point_avgs.append(min(low + mid, 100.0))

        return sum(point_avgs) / len(point_avgs) if point_avgs else 0.0

    def _calc_target_cloud(
        self,
        targets: list[Target],
        context: DataContext,
    ) -> float:
        """计算目标可见性: 从 primary target 的 (high_cloud + mid_cloud)"""
        if not context.target_weather:
            return 0.0

        # 优先取 primary target
        primary = next((t for t in targets if t.weight == "primary"), None)
        target = primary if primary else targets[0]

        weather = context.target_weather.get(target.name)
        if weather is None:
            return 0.0

        high = weather["cloud_cover_high"].mean()
        mid = weather["cloud_cover_medium"].mean()
        return min(high + mid, 100.0)

    def _score_light_path(self, cloud_pct: float) -> int:
        """光路云量 → 阶梯评分"""
        thresholds = self._thresholds["light_path_cloud"]
        scores = self._thresholds["light_path_scores"]
        return self._stepped_score(cloud_pct, thresholds, scores)

    def _score_target(self, cloud_pct: float) -> int:
        """目标可见性 → 阶梯评分"""
        thresholds = self._thresholds["target_cloud"]
        scores = self._thresholds["target_scores"]
        return self._stepped_score(cloud_pct, thresholds, scores)

    def _score_local(self, cloud_pct: float) -> int:
        """本地通透 → 阶梯评分"""
        thresholds = self._thresholds["local_cloud"]
        scores = self._thresholds["local_scores"]
        return self._stepped_score(cloud_pct, thresholds, scores)

    @staticmethod
    def _stepped_score(value: float, thresholds: list[float], scores: list[int]) -> int:
        """通用阶梯评分

        阶梯规则: 值 <= 第一个阈值 → scores[0],
        值 <= 第二个阈值 → scores[1], ..., 超过所有阈值 → scores[-1]。

        thresholds 和 scores 均来自配置文件，scores 比 thresholds 多一个元素（兜底值）。
        """
        for t, s in zip(thresholds, scores):
            if value <= t:
                return s
        return scores[-1]
