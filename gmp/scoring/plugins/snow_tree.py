"""gmp/scoring/plugins/snow_tree.py — SnowTreePlugin 树挂积雪评分

基于过去 24h 本地天气数据，分析近期降雪量、降雪持续时长、冰冻时间等
派生指标，评估树挂积雪的观赏条件。

评分模型包含双触发路径（常规/留存）和多项扣分机制。
"""

from __future__ import annotations

from gmp.core.models import ScoreResult, score_to_status
from gmp.scoring.models import DataContext, DataRequirement


class SnowTreePlugin:
    """树挂积雪评分器"""

    def __init__(self, config: dict) -> None:
        self._config = config

    @property
    def event_type(self) -> str:
        return "snow_tree"

    @property
    def display_name(self) -> str:
        return "树挂积雪"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement(past_hours=self._config.get("past_hours", 24))

    def dimensions(self) -> list[str]:
        return ["snow_signal", "clear_weather", "stability"]

    def score(self, context: DataContext) -> ScoreResult | None:
        df = context.local_weather.copy()

        # ---- 安全检查：剔除不安全时段 ----
        safety = self._config.get("safety", {})
        precip_thresh = safety.get("precip_threshold", 50)
        vis_thresh = safety.get("visibility_threshold", 1000)

        safe_mask = (df["precipitation_probability"] <= precip_thresh) & (
            df["visibility"] >= vis_thresh
        )
        df_safe = df[safe_mask]
        if df_safe.empty:
            return None

        # ---- 派生指标计算 ----
        metrics = self._compute_metrics(df)

        # ---- 触发判定 ----
        trigger_cfg = self._config["trigger"]
        recent = trigger_cfg["recent_path"]
        retention = trigger_cfg["retention_path"]

        recent_triggered = (
            metrics["recent_snowfall_12h_cm"] >= recent["min_snowfall_12h_cm"]
        )
        retention_triggered = (
            metrics["recent_snowfall_24h_cm"]
            >= retention["min_snowfall_24h_cm"]
            and metrics["snowfall_duration_h_24h"]
            >= retention["min_duration_h"]
            and metrics["subzero_hours_since_last_snow"]
            >= retention["min_subzero_hours"]
            and metrics["max_temp_since_last_snow"]
            <= retention["max_temp"]
        )

        if not recent_triggered and not retention_triggered:
            return None

        # ---- 评分计算 ----
        # 当前时刻数据 (最后一行安全数据)
        current = df_safe.iloc[-1]

        weights = self._config["weights"]
        score_snow = self._score_snow_signal(metrics)
        score_clear = self._score_clear_weather(current)
        score_stable = self._score_stability(current)

        ded_age = self._deduction_age(metrics["hours_since_last_snow"])
        ded_temp = self._deduction_temp(metrics["max_temp_since_last_snow"])
        ded_sun = self._deduction_sun(metrics["sunshine_score_since_snow"])
        ded_wind = self._deduction_wind(metrics["max_wind_since_last_snow"])

        total = max(
            0,
            score_snow
            + score_clear
            + score_stable
            - ded_age
            - ded_temp
            - ded_sun
            - ded_wind,
        )
        total = min(100, total)

        return ScoreResult(
            event_type="snow_tree",
            total_score=total,
            status=score_to_status(total),
            breakdown={
                "snow_signal": {
                    "score": score_snow,
                    "max": weights["snow_signal"],
                    "detail": f"24h降雪{metrics['recent_snowfall_24h_cm']:.1f}cm",
                },
                "clear_weather": {
                    "score": score_clear,
                    "max": weights["clear_weather"],
                    "detail": f"天气代码{int(current['weather_code'])}",
                },
                "stability": {
                    "score": score_stable,
                    "max": weights["stability"],
                    "detail": f"当前风速{current['wind_speed_10m']:.0f}km/h",
                },
                "age_deduction": {
                    "score": -ded_age,
                    "max": 0,
                    "detail": f"距停雪{metrics['hours_since_last_snow']:.0f}h",
                },
                "temp_deduction": {
                    "score": -ded_temp,
                    "max": 0,
                    "detail": f"最高温{metrics['max_temp_since_last_snow']:.1f}°C",
                },
                "sun_deduction": {
                    "score": -ded_sun,
                    "max": 0,
                    "detail": f"日照积分{metrics['sunshine_score_since_snow']:.0f}",
                },
                "wind_deduction": {
                    "score": -ded_wind,
                    "max": 0,
                    "detail": f"历史最大风速{metrics['max_wind_since_last_snow']:.0f}km/h",
                },
            },
        )

    # ---- 派生指标计算 ----

    def _compute_metrics(self, df: "pd.DataFrame") -> dict:
        """从 local_weather DataFrame 计算所有派生指标"""
        snowfall = df["snowfall"].values
        temp = df["temperature_2m"].values
        cloud = df["cloud_cover"].values
        wind = df["wind_speed_10m"].values
        n = len(snowfall)

        # 近 12h / 24h 降雪量
        recent_snowfall_12h = float(snowfall[-12:].sum()) if n >= 12 else float(snowfall.sum())
        recent_snowfall_24h = float(snowfall[-24:].sum()) if n >= 24 else float(snowfall.sum())

        # 最后一次降雪的位置
        last_snow_idx = -1
        for i in range(n - 1, -1, -1):
            if snowfall[i] > 0:
                last_snow_idx = i
                break

        if last_snow_idx < 0:
            # 无降雪
            return {
                "recent_snowfall_12h_cm": recent_snowfall_12h,
                "recent_snowfall_24h_cm": recent_snowfall_24h,
                "hours_since_last_snow": float("inf"),
                "snowfall_duration_h_24h": 0,
                "subzero_hours_since_last_snow": 0,
                "max_temp_since_last_snow": float(temp.max()),
                "max_wind_since_last_snow": 0.0,
                "sunshine_score_since_snow": 0.0,
            }

        hours_since = n - 1 - last_snow_idx

        # 24h 降雪持续时长
        snowfall_24h = snowfall[-24:] if n >= 24 else snowfall
        duration = int((snowfall_24h > 0).sum())

        # 降雪后指标 (last_snow_idx+1 到末尾)
        post_snow = slice(last_snow_idx + 1, n)
        post_temp = temp[post_snow]
        post_wind = wind[post_snow]
        post_cloud = cloud[post_snow]

        subzero_hours = int((post_temp < 0).sum()) if len(post_temp) > 0 else 0
        max_temp_since = float(post_temp.max()) if len(post_temp) > 0 else float(temp[last_snow_idx])
        max_wind_since = float(post_wind.max()) if len(post_wind) > 0 else 0.0

        # 日照积分：按云量阈值加权
        sunshine_cfg = self._config.get("sunshine", {})
        sun_cloud_thresholds = sunshine_cfg.get("cloud_thresholds", [10, 30])
        sun_weights = sunshine_cfg.get("weights", [2.0, 1.0])
        sunshine_score = 0.0
        for c in post_cloud:
            if c < sun_cloud_thresholds[0]:
                sunshine_score += sun_weights[0]
            elif c < sun_cloud_thresholds[1]:
                sunshine_score += sun_weights[1]

        return {
            "recent_snowfall_12h_cm": recent_snowfall_12h,
            "recent_snowfall_24h_cm": recent_snowfall_24h,
            "hours_since_last_snow": hours_since,
            "snowfall_duration_h_24h": duration,
            "subzero_hours_since_last_snow": subzero_hours,
            "max_temp_since_last_snow": max_temp_since,
            "max_wind_since_last_snow": max_wind_since,
            "sunshine_score_since_snow": sunshine_score,
        }

    # ---- 评分维度 ----

    def _score_snow_signal(self, metrics: dict) -> int:
        """积雪信号得分"""
        thresholds = self._config["thresholds"]["snow_signal"]
        snowfall = metrics["recent_snowfall_24h_cm"]
        duration = metrics["snowfall_duration_h_24h"]
        for t in thresholds:
            sf = t.get("snowfall", 0)
            dur = t.get("duration", 0)
            if snowfall >= sf and duration >= dur:
                return t["score"]
        return 0

    def _score_clear_weather(self, current_row) -> int:
        """晴朗程度得分"""
        thresholds = self._config["thresholds"]["clear_weather"]
        wc = int(current_row["weather_code"])
        cc = float(current_row["cloud_cover"])
        for t in thresholds:
            codes = t.get("weather_code")
            max_cloud = t.get("max_cloud")
            if codes is None and max_cloud is None:
                return t["score"]  # fallback
            if codes is not None and wc in codes and (max_cloud is None or cc <= max_cloud):
                return t["score"]
        # 默认 fallback
        return thresholds[-1]["score"]

    def _score_stability(self, current_row) -> int:
        """稳定保持得分 (当前风速)"""
        wind_thresholds = self._config["thresholds"]["stability_wind"]
        stability_scores = self._config["thresholds"]["stability_scores"]
        wind = float(current_row["wind_speed_10m"])
        # stability_wind: [12, 20], stability_scores: [20, 14, 8]
        if wind < wind_thresholds[0]:
            return stability_scores[0]
        elif wind < wind_thresholds[1]:
            return stability_scores[1]
        else:
            return stability_scores[2]

    # ---- 扣分项 ----

    def _deduction_age(self, hours_since: float) -> int:
        """降雪距今扣分"""
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

    def _deduction_sun(self, sunshine_score: float) -> int:
        """累积日照扣分"""
        sun_entries = self._config["deductions"]["sun"]
        result = 0
        for entry in sun_entries:
            if sunshine_score > entry["sun_score"]:
                result = entry["deduction"]
        return result

    def _deduction_wind(self, max_wind: float) -> int:
        """历史大风扣分"""
        wind_cfg = self._config["deductions"]
        severe = wind_cfg["wind_severe_threshold"]
        moderate = wind_cfg["wind_moderate_threshold"]
        severe_ded = wind_cfg["wind_severe_deduction"]
        moderate_ded = wind_cfg["wind_moderate_deduction"]
        if max_wind > severe:
            return severe_ded
        elif max_wind > moderate:
            return moderate_ded
        return 0
