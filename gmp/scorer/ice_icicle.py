"""IceIciclePlugin — 冰挂评分

设计依据: design/03-scoring-plugins.md §3.10
评分公式:
  Score = Score_water + Score_freeze + Score_view - Deduction_age - Deduction_temp
"""

from __future__ import annotations

from gmp.core.models import DataContext, DataRequirement, ScoreResult
from gmp.scorer.plugin import score_to_status


class IceIciclePlugin:
    """冰挂评分插件 — 仅需 L1 本地天气"""

    event_type = "ice_icicle"
    display_name = "冰挂"
    data_requirement = DataRequirement()  # 仅需 L1

    # ------------------------------------------------------------------
    # 触发判定 (双路径)
    # ------------------------------------------------------------------

    def check_trigger(self, l1_data: dict) -> bool:
        """双路径触发:
        - fresh_freeze_path: 12h水源≥0.4mm + 距今≤12h + 零下≥4h + 当前晴+冻
        - retention_path:    24h水源≥2.0mm + 距今≤20h + 零下≥10h
                             + 最高温≤1.5°C + 当前晴+冻
        """
        water_12h = l1_data.get("effective_water_input_12h_mm", 0.0)
        water_24h = l1_data.get("effective_water_input_24h_mm", 0.0)
        hours_since = l1_data.get("hours_since_last_water_input", 999.0)
        subzero_h = l1_data.get("subzero_hours_since_last_water", 0.0)
        max_temp = l1_data.get("max_temp_since_last_water", 99.0)
        temp_now = l1_data.get("temperature_2m", 99.0)

        clear_now = (
            l1_data.get("weather_code", 99) in {0, 1, 2}
            and l1_data.get("cloud_cover_total", 100) <= 45
            and l1_data.get("precip_prob", 100) < 30
        )

        fresh_freeze_path = (
            water_12h >= 0.4
            and hours_since <= 12
            and subzero_h >= 4
        )

        retention_path = (
            water_24h >= 2.0
            and hours_since <= 20
            and subzero_h >= 10
            and max_temp <= 1.5
        )

        return clear_now and temp_now <= 0.5 and (fresh_freeze_path or retention_path)

    # ------------------------------------------------------------------
    # 评分
    # ------------------------------------------------------------------

    def score(self, context: DataContext) -> ScoreResult:
        weather = context.local_weather

        water_24h = self._extract(weather, "effective_water_input_24h_mm", 0.0)
        subzero_h = self._extract(weather, "subzero_hours_since_last_water", 0.0)
        temp_now = self._extract(weather, "temperature_2m", 99.0)
        cloud = self._extract(weather, "cloud_cover_total", 100)
        wind = self._extract(weather, "wind_speed_10m", 0)
        hours_since = self._extract(weather, "hours_since_last_water_input", 999)
        max_temp = self._extract(weather, "max_temp_since_last_water", 99)

        # 加分
        water_score = self._score_water(water_24h)
        freeze_score = self._score_freeze(subzero_h, temp_now)
        view_score = self._score_view(cloud, wind)

        # 扣分
        age_ded = self._deduction_age(hours_since)
        temp_ded = self._deduction_temp(max_temp)

        total = water_score + freeze_score + view_score - age_ded - temp_ded
        total = max(0, min(100, total))

        breakdown = {
            "water_input": {
                "score": water_score,
                "max": 50,
                "detail": f"24h有效水源{water_24h:.1f}mm",
            },
            "freeze_strength": {
                "score": freeze_score,
                "max": 30,
                "detail": f"冻结{subzero_h:.0f}h, 当前{temp_now:.1f}°C",
            },
            "view_quality": {
                "score": view_score,
                "max": 20,
                "detail": f"云量{cloud:.0f}%, 风速{wind:.0f}km/h",
            },
            "age_deduction": {
                "score": -age_ded,
                "max": 0,
                "detail": f"水源距今{hours_since:.0f}h",
            },
            "temp_deduction": {
                "score": -temp_ded,
                "max": 0,
                "detail": f"期间最高温{max_temp:.1f}°C",
            },
        }

        return ScoreResult(
            total_score=total,
            status=score_to_status(total),
            breakdown=breakdown,
        )

    def dimensions(self) -> list[str]:
        return [
            "water_input",
            "freeze_strength",
            "view_quality",
            "age_deduction",
            "temp_deduction",
        ]

    # ------------------------------------------------------------------
    # 加分维度
    # ------------------------------------------------------------------

    @staticmethod
    def _score_water(water_24h: float) -> int:
        """水源输入 (满分 50)."""
        if water_24h >= 3.0:
            return 50
        if water_24h >= 2.0:
            return 42
        if water_24h >= 1.0:
            return 34
        if water_24h >= 0.4:
            return 24
        return 0

    @staticmethod
    def _score_freeze(subzero_h: float, temp_now: float) -> int:
        """冻结强度 (满分 30)."""
        if subzero_h >= 14 and temp_now <= -3:
            return 30
        if subzero_h >= 10 and temp_now <= -1:
            return 24
        if subzero_h >= 6 and temp_now <= 0:
            return 16
        return 10

    @staticmethod
    def _score_view(cloud: float, wind: float) -> int:
        """观赏条件 (满分 20)."""
        if cloud <= 20 and wind < 12:
            return 20
        if cloud <= 45 and wind < 20:
            return 14
        return 8

    # ------------------------------------------------------------------
    # 扣分维度
    # ------------------------------------------------------------------

    @staticmethod
    def _deduction_age(hours: float) -> int:
        """水源距今扣分."""
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
