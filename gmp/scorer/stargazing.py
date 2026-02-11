"""StargazingPlugin — 观星评分插件

设计依据:
  - design/03-scoring-plugins.md §3.6 StargazingPlugin
  - implementation-plans/module-06-scorer-complex.md

评分公式:
  Score = Base - Deduction_cloud - Deduction_wind

基准分:
  optimal: 100 | good: 90 | partial: 70 | poor: max(0, 100 - phase×0.8)
"""

from __future__ import annotations

from gmp.core.models import DataContext, DataRequirement, ScoreResult
from gmp.scorer.plugin import score_to_status


class StargazingPlugin:
    """观星评分插件

    仅需天文数据 (月相/月出月落/天文晨暮曦)，不需要 L2 远程天气。
    通过 stargazing_config 注入可配置参数 (来源: engine_config.yaml scoring.stargazing)。
    """

    data_requirement = DataRequirement(
        needs_astro=True,
    )

    def __init__(self, stargazing_config: dict | None = None) -> None:
        cfg = stargazing_config or {}
        self._base_optimal: int = cfg.get("base_optimal", 100)
        self._base_good: int = cfg.get("base_good", 90)
        self._base_partial: int = cfg.get("base_partial", 70)
        self._cloud_penalty_factor: float = cfg.get("cloud_penalty_factor", 0.8)

    @property
    def event_type(self) -> str:
        return "stargazing"

    @property
    def display_name(self) -> str:
        return "观星"

    # ------------------------------------------------------------------
    # 触发条件
    # ------------------------------------------------------------------

    def check_trigger(self, l1_data: dict) -> bool:
        """触发条件: 夜间总云量 < 70%"""
        return l1_data.get("night_cloud_cover", 100) < 70

    # ------------------------------------------------------------------
    # 评分
    # ------------------------------------------------------------------

    def score(self, context: DataContext) -> ScoreResult:
        """计算观星综合评分.

        Score = Base - Deduction_cloud - Deduction_wind
        最终限制在 [0, 100] 区间。
        """
        base, detail_base = self._determine_base_score(context)
        d_cloud, detail_cloud = self._calc_cloud_deduction(context)
        d_wind, detail_wind = self._calc_wind_deduction(context)

        total = base - d_cloud - d_wind
        total = max(0, min(100, total))

        return ScoreResult(
            total_score=total,
            status=score_to_status(total),
            breakdown={
                "base": {
                    "score": base,
                    "max": 100,
                    "detail": detail_base,
                },
                "cloud": {
                    "score": -d_cloud,
                    "max": 0,
                    "detail": detail_cloud,
                },
                "wind": {
                    "score": -d_wind,
                    "max": 0,
                    "detail": detail_wind,
                },
            },
        )

    # ------------------------------------------------------------------
    # 私有评分维度
    # ------------------------------------------------------------------

    def _determine_base_score(self, context: DataContext) -> tuple[int, str]:
        """根据 StargazingWindow.quality 确定基准分.

        optimal / good / partial: 使用配置化固定分
        poor: max(0, 100 - phase × cloud_penalty_factor)
        """
        window = context.stargazing_window
        moon = context.moon_status

        if window is None:
            # 无观星窗口数据 → 降级为 poor
            phase = moon.phase if moon else 100
            base = max(0, int(100 - phase * self._cloud_penalty_factor))
            return base, f"无观星窗口数据, 月相{phase}%, 降级计算"

        quality = window.quality

        if quality == "optimal":
            return self._base_optimal, "optimal: 月亮在地平线下的完美暗夜"
        elif quality == "good":
            return self._base_good, "good: 月相<50%的残月微光"
        elif quality == "partial":
            return self._base_partial, "partial: 月相≥50%但有月下时段"
        else:  # poor
            phase = moon.phase if moon else 100
            base = max(0, int(100 - phase * self._cloud_penalty_factor))
            return base, f"poor: 月相{phase}%, 满月整夜"

    def _calc_cloud_deduction(self, context: DataContext) -> tuple[int, str]:
        """夜间平均云量扣分.

        Deduction = TotalCloudCover% × cloud_penalty_factor，四舍五入取整。
        从 local_weather 中提取 20:00-05:00 时段的平均云量。
        """
        lw = context.local_weather
        avg_cloud = self._extract_night_cloud(lw)
        factor = self._cloud_penalty_factor

        deduction = int(round(avg_cloud * factor))
        detail = f"夜间平均云量{avg_cloud:.0f}%, 扣{avg_cloud * factor:.1f}→{deduction}"
        return deduction, detail

    def _calc_wind_deduction(self, context: DataContext) -> tuple[int, str]:
        """风速扣分 (影响长曝光).

        > 40km/h: -30
        > 20km/h: -10
        ≤ 20km/h:  0
        """
        lw = context.local_weather
        wind = self._extract_night_wind(lw)

        if wind > 40:
            return 30, f"{wind:.1f}km/h >40, 扣30分"
        elif wind > 20:
            return 10, f"{wind:.1f}km/h >20, 扣10分"
        else:
            return 0, f"{wind:.1f}km/h ≤20, 无扣分"

    # ------------------------------------------------------------------
    # 数据提取辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_night_cloud(local_weather) -> float:
        """从本地天气中提取夜间 (20:00-05:00) 平均云量.

        使用向量化操作替代 iterrows() 以保持代码规范一致性。
        """
        if local_weather is None:
            return 100.0

        if hasattr(local_weather, "columns"):
            # DataFrame — 向量化过滤夜间小时
            hour_col = "forecast_hour" if "forecast_hour" in local_weather.columns else "hour"
            cloud_col = "cloud_cover_total" if "cloud_cover_total" in local_weather.columns else "cloud_cover"

            if hour_col in local_weather.columns and cloud_col in local_weather.columns:
                hours = local_weather[hour_col]
                mask = (hours >= 20) | (hours <= 5)
                night_data = local_weather.loc[mask, cloud_col]
                if not night_data.empty:
                    return float(night_data.mean())
                # 无夜间行 → 使用全量均值
                return float(local_weather[cloud_col].mean())

            if cloud_col in local_weather.columns:
                return float(local_weather[cloud_col].mean())
            return 100.0

        if isinstance(local_weather, dict):
            return float(
                local_weather.get(
                    "night_cloud_cover",
                    local_weather.get("cloud_cover_total", local_weather.get("cloud_cover", 100)),
                )
            )

        return 100.0

    @staticmethod
    def _extract_night_wind(local_weather) -> float:
        """从本地天气中提取夜间平均风速.

        使用向量化操作替代 iterrows() 以保持代码规范一致性。
        """
        if local_weather is None:
            return 0.0

        if hasattr(local_weather, "columns"):
            # DataFrame — 向量化过滤
            hour_col = "forecast_hour" if "forecast_hour" in local_weather.columns else "hour"
            wind_col = "wind_speed_10m" if "wind_speed_10m" in local_weather.columns else "wind_speed"

            if hour_col in local_weather.columns and wind_col in local_weather.columns:
                hours = local_weather[hour_col]
                mask = (hours >= 20) | (hours <= 5)
                night_data = local_weather.loc[mask, wind_col]
                if not night_data.empty:
                    return float(night_data.mean())
                return float(local_weather[wind_col].mean())

            if wind_col in local_weather.columns:
                return float(local_weather[wind_col].mean())
            return 0.0

        if isinstance(local_weather, dict):
            return float(
                local_weather.get("wind_speed_10m", local_weather.get("wind_speed", 0))
            )

        return 0.0

    def dimensions(self) -> list[str]:
        return ["base", "cloud", "wind"]
