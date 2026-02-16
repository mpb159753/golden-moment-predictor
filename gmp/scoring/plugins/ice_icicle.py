"""gmp/scoring/plugins/ice_icicle.py — 冰挂评分 Plugin

IceIciclePlugin 是 L1 Plugin，使用 DataContext.local_weather（含过去24h历史），
评估冰挂形成条件。需要计算有效水源输入（雨+雪转水当量）、冻结强度和观赏通透性。

评分公式: Score = Score_water + Score_freeze + Score_view - Deduction_age - Deduction_temp
"""

from __future__ import annotations

from gmp.core.models import ScoreResult, score_to_status
from gmp.scoring.models import DataContext, DataRequirement


class IceIciclePlugin:
    """冰挂评分器"""

    def __init__(self, config: dict) -> None:
        self._config = config

    @property
    def event_type(self) -> str:
        return "ice_icicle"

    @property
    def display_name(self) -> str:
        return "冰挂"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement(past_hours=self._config.get("past_hours", 24))

    def dimensions(self) -> list[str]:
        return ["water_input", "freeze_strength", "view_quality"]

    def score(self, context: DataContext) -> ScoreResult | None:
        """评分入口

        1. 安全检查 (剔除降水/能见度不合格的时段)
        2. 计算派生指标
        3. 触发判定 (双路径: recent_path / retention_path)
        4. 各维度评分 + 扣分
        5. 返回 ScoreResult
        """
        df = context.local_weather.copy()

        # ── 安全检查 ──
        safety = self._config.get("safety", {})
        precip_thresh = safety.get("precip_threshold", 50)
        vis_thresh = safety.get("visibility_threshold", 1000)

        safe_mask = (df["precipitation_probability"] <= precip_thresh) & (
            df["visibility"] >= vis_thresh
        )
        df_safe = df[safe_mask]
        if df_safe.empty:
            return None

        # ── 派生指标计算 ──
        metrics = self._compute_metrics(df)

        # ── 触发判定 ──
        trigger_cfg = self._config["trigger"]
        recent = trigger_cfg["recent_path"]
        retention = trigger_cfg["retention_path"]

        recent_triggered = (
            metrics["effective_water_input_12h_mm"] >= recent["min_water_12h_mm"]
        )
        retention_triggered = (
            metrics["effective_water_input_24h_mm"] >= retention["min_water_24h_mm"]
            and metrics["subzero_hours_since_last_water"] >= retention["min_subzero_hours"]
            and metrics["max_temp_since_last_water"] <= retention["max_temp"]
        )

        if not recent_triggered and not retention_triggered:
            return None

        # ── 评分计算 ──
        current = df_safe.iloc[-1]

        score_water = self._score_water_input(metrics)
        score_freeze = self._score_freeze_strength(metrics, float(current["temperature_2m"]))
        score_view = self._score_view_quality(current)

        ded_age = self._deduction_age(metrics["hours_since_last_water_input"])
        ded_temp = self._deduction_temp(metrics["max_temp_since_last_water"])

        total = max(
            0,
            score_water + score_freeze + score_view - ded_age - ded_temp,
        )
        total = min(100, total)

        return ScoreResult(
            event_type="ice_icicle",
            total_score=total,
            status=score_to_status(total),
            breakdown={
                "water_input": {
                    "score": score_water,
                    "max": self._config["weights"]["water_input"],
                    "detail": f"水源{metrics['effective_water_input_24h_mm']:.1f}mm",
                },
                "freeze_strength": {
                    "score": score_freeze,
                    "max": self._config["weights"]["freeze_strength"],
                    "detail": f"冻结{metrics['subzero_hours_since_last_water']}h",
                },
                "view_quality": {
                    "score": score_view,
                    "max": self._config["weights"]["view_quality"],
                    "detail": f"云量{float(current['cloud_cover_total']):.0f}%",
                },
                "age_deduction": {
                    "score": -ded_age,
                    "max": 0,
                    "detail": f"距水源{metrics['hours_since_last_water_input']:.0f}h",
                },
                "temp_deduction": {
                    "score": -ded_temp,
                    "max": 0,
                    "detail": f"最高温{metrics['max_temp_since_last_water']:.1f}°C",
                },
            },
        )

    # ── 派生指标计算 ──

    def _compute_metrics(self, df) -> dict:
        """从 local_weather DataFrame 计算所有派生指标"""
        rain = df["rain"].values
        showers = df["showers"].values if "showers" in df.columns else rain * 0
        snowfall = df["snowfall"].values
        temp = df["temperature_2m"].values
        n = len(rain)

        snow_water_ratio = self._config.get("snow_water_ratio", 0.1)

        # 有效水源 = rain + showers + snowfall * ratio (单位: mm)
        # snowfall 单位 cm, ratio 0.1 → 1cm 雪 = 1mm 水
        effective_water = rain + showers + snowfall * (snow_water_ratio * 10)

        # 近 12h / 24h 有效水源
        water_12h = float(effective_water[-12:].sum()) if n >= 12 else float(effective_water.sum())
        water_24h = float(effective_water[-24:].sum()) if n >= 24 else float(effective_water.sum())

        # 最后一次有效水源输入的位置
        last_water_idx = -1
        for i in range(n - 1, -1, -1):
            if effective_water[i] > 0:
                last_water_idx = i
                break

        if last_water_idx < 0:
            return {
                "effective_water_input_12h_mm": water_12h,
                "effective_water_input_24h_mm": water_24h,
                "hours_since_last_water_input": float("inf"),
                "subzero_hours_since_last_water": 0,
                "max_temp_since_last_water": float(temp.max()),
            }

        hours_since = n - 1 - last_water_idx

        # 水源停止后的指标
        post_water = slice(last_water_idx + 1, n)
        post_temp = temp[post_water]

        subzero_hours = int((post_temp < 0).sum()) if len(post_temp) > 0 else 0
        max_temp_since = float(post_temp.max()) if len(post_temp) > 0 else float(temp[last_water_idx])

        return {
            "effective_water_input_12h_mm": water_12h,
            "effective_water_input_24h_mm": water_24h,
            "hours_since_last_water_input": hours_since,
            "subzero_hours_since_last_water": subzero_hours,
            "max_temp_since_last_water": max_temp_since,
        }

    # ── 评分维度 ──

    def _score_water_input(self, metrics: dict) -> int:
        """水源输入量得分"""
        thresholds = self._config["thresholds"]["water_input"]
        water_24h = metrics["effective_water_input_24h_mm"]
        for t in thresholds:
            if water_24h >= t["water"]:
                return t["score"]
        return 0

    def _score_freeze_strength(self, metrics: dict, temp_now: float) -> int:
        """冻结强度得分"""
        thresholds = self._config["thresholds"]["freeze_strength"]
        subzero_hours = metrics["subzero_hours_since_last_water"]
        for t in thresholds:
            required_hours = t.get("subzero_hours")
            required_temp = t.get("temp_now")
            if required_hours is None and required_temp is None:
                return t["score"]  # fallback
            if (required_hours is not None and subzero_hours >= required_hours
                    and required_temp is not None and temp_now <= required_temp):
                return t["score"]
        # fallback to last entry
        return thresholds[-1]["score"]

    def _score_view_quality(self, current_row) -> int:
        """观赏通透性得分"""
        thresholds = self._config["thresholds"]["view_quality"]
        cloud = float(current_row["cloud_cover_total"])
        wind = float(current_row["wind_speed_10m"])
        for t in thresholds:
            max_cloud = t.get("max_cloud")
            max_wind = t.get("max_wind")
            if max_cloud is None and max_wind is None:
                return t["score"]  # fallback
            if (max_cloud is not None and cloud <= max_cloud
                    and max_wind is not None and wind <= max_wind):
                return t["score"]
        return thresholds[-1]["score"]

    # ── 扣分项 ──

    def _deduction_age(self, hours_since: float) -> int:
        """距水源输入停止扣分"""
        age_entries = self._config["deductions"]["age"]
        for entry in age_entries:
            if hours_since <= entry["hours"]:
                return entry["deduction"]
        return age_entries[-1]["deduction"]

    def _deduction_temp(self, max_temp: float) -> int:
        """升温融化扣分"""
        temp_entries = self._config["deductions"]["temp"]
        for entry in temp_entries:
            if max_temp <= entry["temp"]:
                return entry["deduction"]
        return temp_entries[-1]["deduction"]
