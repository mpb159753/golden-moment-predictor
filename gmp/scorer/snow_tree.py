"""SnowTreePlugin — 树挂积雪评分

设计依据: design/03-scoring-plugins.md §3.9
评分公式:
  Score = Score_snow + Score_clear + Score_stable
        - Deduction_age - Deduction_temp - Deduction_sun - Deduction_wind
"""

from __future__ import annotations

from gmp.core.models import DataContext, DataRequirement, ScoreResult
from gmp.scorer.plugin import score_to_status


class SnowTreePlugin:
    """树挂积雪评分插件 — 仅需 L1 本地天气"""

    event_type = "snow_tree"
    display_name = "树挂积雪"
    data_requirement = DataRequirement()  # 仅需 L1

    # ------------------------------------------------------------------
    # 触发判定 (双路径)
    # ------------------------------------------------------------------

    def check_trigger(self, l1_data: dict) -> bool:
        """双路径触发:
        - fresh_path:     近12h降雪≥0.2cm + 距今≤12h + 当前晴朗
        - retention_path: 近24h降雪≥1.5cm + 降雪时段≥3h + 零下≥8h
                          + 最高温≤1.5°C + 距今≤20h + 当前晴朗
        """
        recent_snow_12h = l1_data.get("recent_snowfall_12h_cm", 0.0)
        recent_snow_24h = l1_data.get("recent_snowfall_24h_cm", 0.0)
        hours_since = l1_data.get("hours_since_last_snow", 999.0)
        duration_h = l1_data.get("snowfall_duration_h_24h", 0.0)
        subzero_h = l1_data.get("subzero_hours_since_last_snow", 0.0)
        max_temp = l1_data.get("max_temp_since_last_snow", 99.0)

        clear_now = (
            l1_data.get("weather_code", 99) in {0, 1, 2}
            and l1_data.get("cloud_cover_total", 100) <= 45
            and l1_data.get("precip_prob", 100) < 30
        )

        fresh_path = recent_snow_12h >= 0.2 and hours_since <= 12

        retention_path = (
            recent_snow_24h >= 1.5
            and duration_h >= 3
            and subzero_h >= 8
            and max_temp <= 1.5
            and hours_since <= 20
        )

        return clear_now and (fresh_path or retention_path)

    # ------------------------------------------------------------------
    # 评分
    # ------------------------------------------------------------------

    def score(self, context: DataContext) -> ScoreResult:
        weather = context.local_weather

        snow_24h = self._extract(weather, "recent_snowfall_24h_cm", 0.0)
        duration_h = self._extract(weather, "snowfall_duration_h_24h", 0.0)
        weather_code = int(self._extract(weather, "weather_code", 99))
        cloud = self._extract(weather, "cloud_cover_total", 100)
        wind = self._extract(weather, "wind_speed_10m", 0)
        hours_since = self._extract(weather, "hours_since_last_snow", 999)
        max_temp = self._extract(weather, "max_temp_since_last_snow", 99)
        sunshine_h = self._extract(weather, "sunshine_hours_since_snow", 0)
        max_wind_hist = self._extract(weather, "max_wind_since_last_snow", 0)

        # 加分
        snow_score = self._score_snow(snow_24h, duration_h)
        clear_score = self._score_clear(weather_code, cloud)
        stable_score = self._score_stable(wind)

        # 扣分
        age_ded = self._deduction_age(hours_since)
        temp_ded = self._deduction_temp(max_temp)
        sun_ded = self._deduction_sun(sunshine_h)
        wind_ded = self._deduction_wind(max_wind_hist)

        total = snow_score + clear_score + stable_score - age_ded - temp_ded - sun_ded - wind_ded
        total = max(0, min(100, total))

        breakdown = {
            "snow_signal": {
                "score": snow_score,
                "max": 60,
                "detail": f"降雪{snow_24h:.1f}cm, 时长{duration_h:.0f}h",
            },
            "clear_weather": {
                "score": clear_score,
                "max": 20,
                "detail": f"weather_code={weather_code}, 云量{cloud:.0f}%",
            },
            "stability": {
                "score": stable_score,
                "max": 20,
                "detail": f"当前风速{wind:.1f}km/h",
            },
            "age_deduction": {
                "score": -age_ded,
                "max": 0,
                "detail": f"距停雪{hours_since:.0f}h",
            },
            "temp_deduction": {
                "score": -temp_ded,
                "max": 0,
                "detail": f"最高温{max_temp:.1f}°C",
            },
            "sun_deduction": {
                "score": -sun_ded,
                "max": 0,
                "detail": f"累积日照{sunshine_h:.0f}h",
            },
            "wind_deduction": {
                "score": -wind_ded,
                "max": 0,
                "detail": f"历史最大风速{max_wind_hist:.0f}km/h",
            },
        }

        return ScoreResult(
            total_score=total,
            status=score_to_status(total),
            breakdown=breakdown,
        )

    def dimensions(self) -> list[str]:
        return [
            "snow_signal",
            "clear_weather",
            "stability",
            "age_deduction",
            "temp_deduction",
            "sun_deduction",
            "wind_deduction",
        ]

    # ------------------------------------------------------------------
    # 加分维度
    # ------------------------------------------------------------------

    @staticmethod
    def _score_snow(snow_24h: float, duration_h: float) -> int:
        """积雪信号 (满分 60)."""
        if snow_24h >= 2.5 and duration_h >= 4:
            return 60
        if snow_24h >= 1.5 and duration_h >= 3:
            return 52
        if snow_24h >= 0.8 and duration_h >= 2:
            return 44
        if snow_24h >= 0.2:
            return 32
        return 0

    @staticmethod
    def _score_clear(weather_code: int, cloud: float) -> int:
        """晴朗程度 (满分 20)."""
        if weather_code == 0 and cloud <= 20:
            return 20
        if weather_code in {1, 2} and cloud <= 45:
            return 16
        return 8

    @staticmethod
    def _score_stable(wind: float) -> int:
        """稳定保持 — 当前风速 (满分 20)."""
        if wind < 12:
            return 20
        if wind < 20:
            return 14
        return 8

    # ------------------------------------------------------------------
    # 扣分维度 (阶梯查表)
    # ------------------------------------------------------------------

    @staticmethod
    def _deduction_age(hours: float) -> int:
        """降雪距今扣分."""
        thresholds = [(3, 0), (8, 2), (12, 5), (16, 8), (20, 12)]
        for h, d in thresholds:
            if hours <= h:
                return d
        return 20

    @staticmethod
    def _deduction_temp(max_temp: float) -> int:
        """升温融化扣分."""
        thresholds = [(-2.0, 0), (-0.5, 2), (1.0, 6), (2.5, 12)]
        for t, d in thresholds:
            if max_temp <= t:
                return d
        return 22

    @staticmethod
    def _deduction_sun(sunshine_hours: float) -> int:
        """累积日照扣分."""
        if sunshine_hours > 8:
            return 30
        if sunshine_hours > 5:
            return 15
        if sunshine_hours > 2:
            return 5
        return 0

    @staticmethod
    def _deduction_wind(max_wind: float) -> int:
        """历史大风扣分."""
        if max_wind > 50:
            return 50
        if max_wind > 30:
            return 20
        return 0

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _extract(weather, column: str, default: float) -> float:
        if hasattr(weather, "__getitem__") and column in weather.columns:
            vals = weather[column].dropna()
            if len(vals) > 0:
                return float(vals.iloc[0])
        return default
