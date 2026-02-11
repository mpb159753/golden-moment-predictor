"""FrostPlugin — 雾凇评分

设计依据: design/03-scoring-plugins.md §3.8
评分公式: Score = Score_temp + Score_moisture + Score_wind + Score_cloud
"""

from __future__ import annotations

from gmp.core.models import DataContext, DataRequirement, ScoreResult
from gmp.scorer.plugin import score_to_status


class FrostPlugin:
    """雾凇评分插件 — 仅需 L1 本地天气"""

    event_type = "frost"
    display_name = "雾凇"
    data_requirement = DataRequirement()  # 仅需 L1

    # ------------------------------------------------------------------
    # 触发判定
    # ------------------------------------------------------------------

    def check_trigger(self, l1_data: dict) -> bool:
        """触发条件: 温度 < 2°C."""
        return l1_data.get("temperature_2m", 999) < 2.0

    # ------------------------------------------------------------------
    # 评分
    # ------------------------------------------------------------------

    def score(self, context: DataContext) -> ScoreResult:
        weather = context.local_weather

        temp = self._extract(weather, "temperature_2m", 999)
        visibility = self._extract(weather, "visibility", 99999)
        wind = self._extract(weather, "wind_speed_10m", 0)
        low_cloud = self._extract(weather, "cloud_cover_low", 0)

        temp_score = self._score_temp(temp)
        moisture_score = self._score_moisture(visibility)
        wind_score = self._score_wind(wind)
        cloud_score = self._score_cloud(low_cloud)

        total = temp_score + moisture_score + wind_score + cloud_score
        total = max(0, min(100, total))

        breakdown = {
            "temperature": {
                "score": temp_score,
                "max": 40,
                "detail": f"{temp:.1f}°C",
            },
            "moisture": {
                "score": moisture_score,
                "max": 30,
                "detail": f"能见度{visibility/1000:.0f}km",
            },
            "wind": {
                "score": wind_score,
                "max": 20,
                "detail": f"{wind:.1f}km/h",
            },
            "cloud": {
                "score": cloud_score,
                "max": 10,
                "detail": f"低云{low_cloud:.0f}%",
            },
        }

        return ScoreResult(
            total_score=total,
            status=score_to_status(total),
            breakdown=breakdown,
        )

    def dimensions(self) -> list[str]:
        return ["temperature", "moisture", "wind", "cloud"]

    # ------------------------------------------------------------------
    # 私有评分方法
    # ------------------------------------------------------------------

    @staticmethod
    def _score_temp(temp: float) -> int:
        """温度适宜得分 (满分 40).

        -5 ≤ T ≤ -1 : 40
        -10 ≤ T < -5 : 30
        0 ≤ T ≤ 2   : 25
        T < -10      : 15
        """
        if -5 <= temp <= -1:
            return 40
        if -10 <= temp < -5:
            return 30
        if 0 <= temp <= 2:
            return 25
        if temp < -10:
            return 15
        # temp > 2 不应到这里 (check_trigger 应拦截), 但以防万一
        return 0

    @staticmethod
    def _score_moisture(visibility: float) -> int:
        """湿度条件得分 (满分 30). visibility 单位: m."""
        vis_km = visibility / 1000.0 if visibility > 100 else visibility
        if vis_km < 5:
            return 30
        if vis_km < 10:
            return 20
        if vis_km < 20:
            return 10
        return 5  # ≥ 20km 空气干燥

    @staticmethod
    def _score_wind(wind: float) -> int:
        """风速稳定得分 (满分 20)."""
        if wind < 3:
            return 20
        if wind < 5:
            return 15
        if wind < 10:
            return 10
        return 0

    @staticmethod
    def _score_cloud(low_cloud: float) -> int:
        """云况适宜得分 (满分 10)."""
        if 30 <= low_cloud <= 60:
            return 10
        if low_cloud < 30:
            return 5
        return 3  # > 60%

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
