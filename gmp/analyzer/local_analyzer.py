"""L1 本地滤网 — 安全检查 + 各 Plugin 触发条件预判

使用观景台本地的天气数据进行:
1. 安全检查 (一票否决)
2. 云海判定 (云底高度 vs 站点海拔)
3. 雾凇判定 (温度 < 2°C)
4. 树挂积雪派生指标计算
5. 冰挂派生指标计算
6. 汇总本地天气概要

设计依据:
- design/01-architecture.md §1.5 L1 滤网
- design/03-scoring-plugins.md §3.7-3.10 触发条件
- design/04-data-flow-example.md §Stage 4
"""

from __future__ import annotations

import pandas as pd

from gmp.analyzer.base import BaseAnalyzer
from gmp.core.config_loader import EngineConfig
from gmp.core.models import AnalysisResult


class LocalAnalyzer(BaseAnalyzer):
    """L1 本地滤网 — 安全检查 + 各 Plugin 触发条件预判"""

    # 降雪转换为水当量的系数 (1cm 雪 ≈ 1mm 水)
    SNOW_WATER_EQUIV = 1.0

    def __init__(self, config: EngineConfig):
        self._config = config

    def analyze(self, data: pd.DataFrame, context: dict) -> AnalysisResult:
        """分析本地天气数据

        Args:
            data: 本地观景台的逐小时天气 DataFrame（需包含 forecast_hour 列）
            context: 上下文信息，需包含:
                - site_altitude: int — 观景台海拔 (m)
                - target_hour: int — 目标分析小时 (0-23)

        Returns:
            AnalysisResult，其中 details 包含完整的本地分析指标
        """
        site_altitude: int = context.get("site_altitude", 0)
        target_hour: int = context.get("target_hour", 7)

        # 获取目标小时的行
        hour_row = self._get_hour_row(data, target_hour)
        if hour_row is None:
            return AnalysisResult(
                passed=False,
                score=0,
                reason="无法获取目标小时天气数据",
                details={"safety": {"passed": False}},
            )

        # 1. 安全检查 (一票否决)
        safety_passed = self._check_safety(hour_row)
        safety_details = {
            "passed": safety_passed,
            "precip_prob": hour_row.get("precipitation_probability", 0),
            "visibility": hour_row.get("visibility", 0),
        }

        if not safety_passed:
            return AnalysisResult(
                passed=False,
                score=0,
                reason="安全检查未通过",
                details={
                    "safety": safety_details,
                    "cloud_cover_total": hour_row.get("cloud_cover_total", 0),
                    "temperature_2m": hour_row.get("temperature_2m", 0),
                },
            )

        # 2. 云海判定
        cloud_base_altitude = self._estimate_cloud_base_altitude(hour_row, site_altitude)
        cloud_sea_info = self._check_cloud_sea(cloud_base_altitude, site_altitude)

        # 3. 雾凇判定
        temperature = hour_row.get("temperature_2m", 20.0)
        frost_info = self._check_frost(temperature)

        # 4. 夜间平均云量 (20:00 - 05:00)
        night_cloud = self._compute_night_cloud_cover(data)

        # 5. 树挂积雪派生指标
        snow_tree_indicators = self._compute_snow_tree_indicators(data)

        # 6. 冰挂派生指标
        ice_icicle_indicators = self._compute_ice_icicle_indicators(data)

        # 汇总 details
        details = {
            "safety": safety_details,
            "cloud_cover_total": hour_row.get("cloud_cover_total", 0),
            "cloud_base_altitude": cloud_base_altitude,
            "site_altitude": site_altitude,
            "temperature_2m": temperature,
            "night_cloud_cover": night_cloud,
            "wind_speed_10m": hour_row.get("wind_speed_10m", 0),
            "weather_code": hour_row.get("weather_code", 0),
            "precip_prob": int(hour_row.get("precipitation_probability", 0)),
            # 云海/雾凇标记
            "cloud_sea": cloud_sea_info,
            "frost": frost_info,
        }

        # 合并树挂和冰挂指标
        details.update(snow_tree_indicators)
        details.update(ice_icicle_indicators)

        # 计算综合评分 (0-100)
        score = self._compute_score(details)

        return AnalysisResult(
            passed=True,
            score=score,
            reason="L1 本地滤网通过",
            details=details,
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_hour_row(data: pd.DataFrame, target_hour: int) -> dict | None:
        """获取目标小时的数据行"""
        if "forecast_hour" not in data.columns:
            return None
        rows = data[data["forecast_hour"] == target_hour]
        if rows.empty:
            return None
        return rows.iloc[-1].to_dict()

    def _check_safety(self, row: dict) -> bool:
        """安全检查: 降水概率 < precip_threshold 且 能见度 > visibility_threshold"""
        precip_ok = row.get("precipitation_probability", 100) < self._config.precip_threshold
        visibility_ok = row.get("visibility", 0) > self._config.visibility_threshold
        return precip_ok and visibility_ok

    @staticmethod
    def _estimate_cloud_base_altitude(row: dict, site_altitude: int) -> float:
        """估算云底高度

        使用低云量作为代理指标:
        - 低云量 > 50%: 云底在站点海拔附近
        - 低云量 < 20%: 云底远高于站点
        - 否则: 线性插值

        如果 DataFrame 提供了 cloud_base_altitude 列，直接使用。
        """
        if "cloud_base_altitude" in row:
            return float(row["cloud_base_altitude"])

        low_cloud = row.get("cloud_cover_low", 0)
        if low_cloud > 50:
            # 低云量高 → 云底在站点附近或以下
            return site_altitude - (low_cloud - 50) * 20
        elif low_cloud < 20:
            # 低云量低 → 云底远高于站点
            return site_altitude + 2000
        else:
            # 线性插值: 20%-50% → +2000 到 0
            ratio = (50 - low_cloud) / 30
            return site_altitude + ratio * 2000

    @staticmethod
    def _check_cloud_sea(cloud_base: float, site_altitude: int) -> dict:
        """云海判定: 云底高度 < 站点海拔 → 站点在云上方"""
        is_cloud_sea = cloud_base < site_altitude
        gap = site_altitude - cloud_base if is_cloud_sea else 0
        return {
            "detected": is_cloud_sea,
            "cloud_base": cloud_base,
            "gap": gap,
        }

    def _check_frost(self, temperature: float) -> dict:
        """雾凇判定: 温度 < frost_temp_threshold (默认 2°C)"""
        is_frost = temperature < self._config.frost_temp_threshold
        return {
            "detected": is_frost,
            "temperature": temperature,
            "threshold": self._config.frost_temp_threshold,
        }

    @staticmethod
    def _compute_night_cloud_cover(data: pd.DataFrame) -> float:
        """计算夜间 (20:00-05:00) 平均云量"""
        if "forecast_hour" not in data.columns or "cloud_cover_total" not in data.columns:
            return 0.0

        night_hours = data[
            (data["forecast_hour"] >= 20) | (data["forecast_hour"] <= 5)
        ]
        if night_hours.empty:
            return 0.0
        return float(night_hours["cloud_cover_total"].mean())

    def _compute_snow_tree_indicators(self, weather_history: pd.DataFrame) -> dict:
        """计算树挂积雪相关的派生指标

        从天气历史中计算:
        - recent_snowfall_12h_cm: 近12小时累计降雪
        - recent_snowfall_24h_cm: 近24小时累计降雪
        - hours_since_last_snow: 距最后一次降雪的小时数
        - snowfall_duration_h_24h: 24小时内降雪小时数
        - subzero_hours_since_last_snow: 降雪后零下持续小时数
        - max_temp_since_last_snow: 降雪后最高温度
        - max_wind_since_last_snow: 降雪后最大风速
        - sunshine_hours_since_snow: 降雪后日照时数 (按云量加权)
        """
        defaults = {
            "recent_snowfall_12h_cm": 0.0,
            "recent_snowfall_24h_cm": 0.0,
            "hours_since_last_snow": 999.0,
            "snowfall_duration_h_24h": 0,
            "subzero_hours_since_last_snow": 0,
            "max_temp_since_last_snow": 0.0,
            "max_wind_since_last_snow": 0.0,
            "sunshine_hours_since_snow": 0.0,
        }

        if "snowfall" not in weather_history.columns:
            return defaults

        hist = weather_history.reset_index(drop=True)
        n = len(hist)

        # 近 12/24 小时降雪量
        recent_snowfall_24h_cm = float(hist.tail(24)["snowfall"].sum())
        recent_snowfall_12h_cm = float(hist.tail(12)["snowfall"].sum())

        # 24 小时内降雪小时数
        snow_hours_24h = int((hist.tail(24)["snowfall"] > 0).sum())

        # 距离最后一次降雪的小时数
        snow_indices = hist.index[hist["snowfall"] > 0].tolist()
        if not snow_indices:
            defaults["recent_snowfall_12h_cm"] = recent_snowfall_12h_cm
            defaults["recent_snowfall_24h_cm"] = recent_snowfall_24h_cm
            defaults["snowfall_duration_h_24h"] = snow_hours_24h
            return defaults

        last_snow_idx = snow_indices[-1]
        hours_since = n - last_snow_idx - 1

        # 降雪后的子集
        since_last_snow = hist.iloc[last_snow_idx + 1:]

        # 零下持续小时数
        subzero_hours = 0
        max_temp = float("-inf")
        max_wind = 0.0
        sunshine = 0.0

        if not since_last_snow.empty:
            if "temperature_2m" in since_last_snow.columns:
                subzero_hours = int((since_last_snow["temperature_2m"] < 0).sum())
                max_temp = float(since_last_snow["temperature_2m"].max())
            if "wind_speed_10m" in since_last_snow.columns:
                max_wind = float(since_last_snow["wind_speed_10m"].max())
            if "cloud_cover_total" in since_last_snow.columns:
                for _, row in since_last_snow.iterrows():
                    cc = row["cloud_cover_total"]
                    if cc < 10:
                        sunshine += 2
                    elif cc < 30:
                        sunshine += 1
        else:
            # 最后一行就是降雪，没有 since_last_snow
            max_temp = 0.0

        return {
            "recent_snowfall_12h_cm": recent_snowfall_12h_cm,
            "recent_snowfall_24h_cm": recent_snowfall_24h_cm,
            "hours_since_last_snow": float(hours_since),
            "snowfall_duration_h_24h": snow_hours_24h,
            "subzero_hours_since_last_snow": subzero_hours,
            "max_temp_since_last_snow": max_temp if max_temp != float("-inf") else 0.0,
            "max_wind_since_last_snow": max_wind,
            "sunshine_hours_since_snow": sunshine,
        }

    def _compute_ice_icicle_indicators(self, weather_history: pd.DataFrame) -> dict:
        """计算冰挂相关的派生指标

        从天气历史中计算:
        - effective_water_input_12h_mm: rain + showers + snowfall * 水当量系数
        - effective_water_input_24h_mm: 同上 24 小时
        - hours_since_last_water_input: 距最后有效水源的小时数
        - subzero_hours_since_last_water: 水源后零下持续小时数
        - max_temp_since_last_water: 水源后最高温度
        """
        defaults = {
            "effective_water_input_12h_mm": 0.0,
            "effective_water_input_24h_mm": 0.0,
            "hours_since_last_water_input": 999.0,
            "subzero_hours_since_last_water": 0,
            "max_temp_since_last_water": 0.0,
        }

        hist = weather_history.reset_index(drop=True)
        n = len(hist)

        # 计算有效水源输入 (rain + showers + snowfall * 水当量)
        rain = hist["rain"] if "rain" in hist.columns else pd.Series([0] * n)
        showers = hist["showers"] if "showers" in hist.columns else pd.Series([0] * n)
        snowfall = hist["snowfall"] if "snowfall" in hist.columns else pd.Series([0] * n)

        water_input = rain + showers + snowfall * self.SNOW_WATER_EQUIV

        # 近 12/24 小时有效水源
        effective_24h = float(water_input.tail(24).sum())
        effective_12h = float(water_input.tail(12).sum())

        # 距最后有效水源的小时数
        water_indices = water_input.index[water_input > 0].tolist()
        if not water_indices:
            defaults["effective_water_input_12h_mm"] = effective_12h
            defaults["effective_water_input_24h_mm"] = effective_24h
            return defaults

        last_water_idx = water_indices[-1]
        hours_since = n - last_water_idx - 1

        # 水源后的子集
        since_last_water = hist.iloc[last_water_idx + 1:]

        subzero_hours = 0
        max_temp = 0.0

        if not since_last_water.empty and "temperature_2m" in since_last_water.columns:
            subzero_hours = int((since_last_water["temperature_2m"] < 0).sum())
            max_temp = float(since_last_water["temperature_2m"].max())

        return {
            "effective_water_input_12h_mm": effective_12h,
            "effective_water_input_24h_mm": effective_24h,
            "hours_since_last_water_input": float(hours_since),
            "subzero_hours_since_last_water": subzero_hours,
            "max_temp_since_last_water": max_temp,
        }

    @staticmethod
    def _compute_score(details: dict) -> int:
        """根据各项指标计算 L1 综合评分 (0-100)

        评分依据:
        - 基础分 50 (安全通过即有)
        - 云海检测 +15
        - 雾凇检测 +10
        - 低云量奖励 +15 (总云量 < 30%)
        - 低风速奖励 +10 (风速 < 20 km/h)
        """
        score = 50

        if details.get("cloud_sea", {}).get("detected", False):
            score += 15

        if details.get("frost", {}).get("detected", False):
            score += 10

        cloud_total = details.get("cloud_cover_total", 100)
        if cloud_total < 30:
            score += 15
        elif cloud_total < 60:
            score += 8

        wind = details.get("wind_speed_10m", 100)
        if wind < 20:
            score += 10
        elif wind < 30:
            score += 5

        return min(score, 100)
