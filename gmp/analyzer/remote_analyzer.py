"""L2 远程滤网 — 目标可见性 + 光路通畅度

使用目标山峰和光路检查点的天气数据进行精细判定:
1. 目标山峰可见性: 高云+中云 < 30%
2. 光路通畅度: 10 个检查点 (low+mid) 均值 < 50%

设计依据:
- design/01-architecture.md §1.5 L2 滤网
- design/03-scoring-plugins.md §3.3 DataRequirement
- design/04-data-flow-example.md §Stage 4
"""

from __future__ import annotations

import pandas as pd

from gmp.analyzer.base import BaseAnalyzer
from gmp.core.config_loader import EngineConfig
from gmp.core.models import AnalysisResult


class RemoteAnalyzer(BaseAnalyzer):
    """L2 远程滤网 — 目标可见性 + 光路通畅度"""

    def __init__(self, config: EngineConfig):
        self._config = config

    def analyze(self, data: pd.DataFrame, context: dict) -> AnalysisResult:
        """分析远程天气数据（目标山峰 + 光路检查点）

        Args:
            data: 未直接使用，保持接口一致性
            context: 上下文信息，需包含:
                - target_weather: {target_name: DataFrame} — 各目标的天气数据
                - light_path_weather: [dict] — 光路检查点天气
                  每个 dict 含: point_name, low_cloud, mid_cloud, combined
                - target_hour: int — 目标分析小时

        Returns:
            AnalysisResult，其中 details 包含目标和光路分析结果
        """
        target_weather: dict = context.get("target_weather", {})
        light_path_weather: list[dict] = context.get("light_path_weather", [])
        target_hour: int = context.get("target_hour", 7)

        # 分析各目标可见性
        targets_results = []
        any_primary_visible = False
        has_primary = False

        for target_name, target_df in target_weather.items():
            weight = context.get("target_weights", {}).get(target_name, "secondary")
            visibility_info = self._check_target_visibility(target_df, target_hour)
            visibility_info["name"] = target_name
            visibility_info["weight"] = weight
            targets_results.append(visibility_info)

            if weight == "primary":
                has_primary = True
                if visibility_info["visible"]:
                    any_primary_visible = True

        # 分析光路通畅度
        light_path_result = self._check_light_path(light_path_weather)

        # 综合判定
        # primary 目标不可见 → L2 评分降低但不一票否决
        # 光路不通畅 → 日照金山评分降低
        passed = True
        reasons = []

        if has_primary and not any_primary_visible:
            reasons.append("主要目标不可见")
        elif not has_primary and not targets_results:
            reasons.append("无目标天气数据")

        if not light_path_result["clear"]:
            reasons.append("光路不通畅")

        if not targets_results and not light_path_weather:
            passed = False
            reasons.append("无远程天气数据")

        reason = "L2 远程滤网通过" if not reasons else "; ".join(reasons)

        # 计算 L2 评分
        score = self._compute_score(targets_results, light_path_result, has_primary)

        details = {
            "targets": targets_results,
            "light_path": light_path_result,
        }

        return AnalysisResult(
            passed=passed,
            score=score,
            reason=reason,
            details=details,
        )

    def _check_target_visibility(
        self, target_data: pd.DataFrame, hour: int
    ) -> dict:
        """检查目标山峰可见性: 高云+中云 < target_cloud_threshold (默认 30%)

        Args:
            target_data: 目标的天气 DataFrame
            hour: 目标小时

        Returns:
            {visible: bool, combined_cloud: float, status: str}
        """
        if target_data.empty:
            return {
                "visible": False,
                "combined_cloud": 100.0,
                "status": "无数据",
            }

        # 获取目标小时的行
        if "forecast_hour" in target_data.columns:
            rows = target_data[target_data["forecast_hour"] == hour]
            if rows.empty:
                row = target_data.iloc[-1]
            else:
                row = rows.iloc[-1]
        else:
            row = target_data.iloc[-1]

        high_cloud = row.get("cloud_cover_high", 0)
        mid_cloud = row.get("cloud_cover_medium", 0)
        combined = high_cloud + mid_cloud

        visible = bool(combined < self._config.target_cloud_threshold)

        if visible:
            status = "可见" if combined < 15 else "基本可见"
        else:
            status = "遮挡"

        return {
            "visible": visible,
            "combined_cloud": float(combined),
            "status": status,
        }

    def _check_light_path(self, light_points_data: list[dict]) -> dict:
        """检查光路通畅度: 各检查点 (low+mid) 均值 < light_path_threshold (默认 50%)

        Args:
            light_points_data: 光路检查点数据列表
                每个 dict 含: point_name, low_cloud, mid_cloud, combined

        Returns:
            {clear: bool, avg_combined_cloud: float, max_combined_cloud: float, status: str}
        """
        if not light_points_data:
            return {
                "clear": False,
                "avg_combined_cloud": 100.0,
                "max_combined_cloud": 100.0,
                "status": "无光路数据",
            }

        combined_values = []
        for point in light_points_data:
            # 使用 combined 字段，或计算 low + mid
            if "combined" in point:
                combined_values.append(float(point["combined"]))
            else:
                low = float(point.get("low_cloud", 0))
                mid = float(point.get("mid_cloud", 0))
                combined_values.append(low + mid)

        avg_combined = sum(combined_values) / len(combined_values)
        max_combined = max(combined_values)

        clear = avg_combined < self._config.light_path_threshold

        if clear:
            status = "通畅" if avg_combined < 25 else "基本通畅"
        else:
            status = "受阻"

        return {
            "clear": clear,
            "avg_combined_cloud": avg_combined,
            "max_combined_cloud": max_combined,
            "status": status,
        }

    def _compute_score(
        self,
        targets: list[dict],
        light_path: dict,
        has_primary: bool,
    ) -> int:
        """计算 L2 综合评分 (0-100)

        评分依据:
        - 光路通畅 (最高 l2_light_path_max)
        - 目标可见 (primary + secondary)
        - 基础分 l2_base_score (有数据即得)
        """
        cfg = self._config
        score = cfg.l2_base_score

        # 光路评分 (最高 l2_light_path_max)
        lp_max = cfg.l2_light_path_max
        avg_cloud = light_path.get("avg_combined_cloud", 100)
        if avg_cloud < cfg.l2_light_path_good_threshold:
            score += lp_max
        elif avg_cloud < self._config.light_path_threshold:
            score += int(
                lp_max * (self._config.light_path_threshold - avg_cloud)
                / (self._config.light_path_threshold - cfg.l2_light_path_good_threshold)
            )
        # avg >= light_path_threshold → no bonus

        # 目标评分
        if targets:
            visible_count = sum(1 for t in targets if t.get("visible", False))
            total_count = len(targets)

            # primary 可见加分
            primary_visible = any(
                t.get("visible") and t.get("weight") == "primary" for t in targets
            )
            if has_primary and primary_visible:
                score += cfg.l2_target_primary_bonus
            elif has_primary:
                score += cfg.l2_target_primary_blocked_bonus
            else:
                # 无 primary，按全部可见比例
                if total_count > 0:
                    score += int(cfg.l2_target_primary_bonus * visible_count / total_count)

            # secondary 可见加分
            secondary_targets = [t for t in targets if t.get("weight") != "primary"]
            if secondary_targets:
                sec_visible = sum(1 for t in secondary_targets if t.get("visible"))
                score += int(cfg.l2_target_secondary_max * sec_visible / len(secondary_targets))

        return min(score, 100)
