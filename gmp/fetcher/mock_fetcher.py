"""Mock 数据获取器 (测试用)

提供多种预制天气场景，用于单元测试和开发调试。
支持场景: clear / rain / frost / timeout / snow / ice
接口定义遵循 design/09-testing-config.md §9.4。
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from gmp.core.exceptions import APITimeoutError
from gmp.fetcher.base import BaseFetcher


class MockMeteoFetcher(BaseFetcher):
    """测试用 Mock 数据获取器

    根据设定的场景 (scenario) 返回预制天气数据，
    同时记录所有调用日志供测试断言。
    """

    def __init__(self, scenario: str = "clear") -> None:
        """初始化 MockMeteoFetcher。

        Args:
            scenario: 天气场景
                - "clear": 典型晴天
                - "rain": 雨天
                - "frost": 雾凇天
                - "timeout": 模拟 API 超时
                - "snow": 降雪天
                - "ice": 冰挂天
        """
        self.scenario = scenario
        self.call_log: list[dict] = []
        self.remote_call_count: int = 0

    def fetch_hourly(
        self, lat: float, lon: float, days: int = 7
    ) -> pd.DataFrame:
        """根据 scenario 返回预制天气数据。

        Args:
            lat: 纬度
            lon: 经度
            days: 预报天数

        Returns:
            预制天气 DataFrame

        Raises:
            APITimeoutError: scenario 为 "timeout" 时
        """
        self.call_log.append({
            "method": "fetch_hourly",
            "lat": lat,
            "lon": lon,
            "days": days,
        })
        self.remote_call_count += 1

        if self.scenario == "timeout":
            raise APITimeoutError(service="open-meteo", timeout=15)

        generators = {
            "clear": self._generate_clear_weather,
            "rain": self._generate_rainy_weather,
            "frost": self._generate_frost_weather,
            "snow": self._generate_snow_weather,
            "ice": self._generate_ice_weather,
        }

        generator = generators.get(self.scenario, self._generate_clear_weather)
        return generator(days)

    def fetch_multi_points(
        self,
        coords: list[tuple[float, float]],
        days: int = 1,
    ) -> dict[tuple, pd.DataFrame]:
        """批量获取多个坐标点的天气（坐标去重）。"""
        unique_coords = list({
            (round(lat, 2), round(lon, 2)) for lat, lon in coords
        })

        results: dict[tuple, pd.DataFrame] = {}
        for lat, lon in unique_coords:
            df = self.fetch_hourly(lat, lon, days)
            results[(lat, lon)] = df

        return results

    def _make_base_dataframe(self, days: int) -> pd.DataFrame:
        """创建基础 DataFrame 框架 (日期 + 小时列)。"""
        today = date.today()
        rows = []
        for d in range(days):
            current_date = today + timedelta(days=d)
            for h in range(24):
                rows.append({
                    "forecast_date": current_date.isoformat(),
                    "forecast_hour": h,
                })
        return pd.DataFrame(rows)

    def _generate_clear_weather(self, days: int) -> pd.DataFrame:
        """典型晴天: 云量低, 无降水, 高能见度。"""
        df = self._make_base_dataframe(days)
        n = len(df)
        rng = np.random.default_rng(42)

        df["temperature_2m"] = rng.uniform(10, 25, n).round(1)
        df["cloud_cover_total"] = rng.integers(0, 20, n)
        df["cloud_cover_low"] = rng.integers(0, 10, n)
        df["cloud_cover_medium"] = rng.integers(0, 10, n)
        df["cloud_cover_high"] = rng.integers(0, 15, n)
        df["precipitation_probability"] = rng.integers(0, 10, n)
        df["visibility"] = rng.uniform(15000, 50000, n).round(0)
        df["wind_speed_10m"] = rng.uniform(2, 12, n).round(1)
        df["snowfall"] = 0.0
        df["rain"] = 0.0
        df["showers"] = 0.0
        df["weather_code"] = 0  # Clear sky

        return df

    def _generate_rainy_weather(self, days: int) -> pd.DataFrame:
        """雨天: 高降水概率, 低能见度。"""
        df = self._make_base_dataframe(days)
        n = len(df)
        rng = np.random.default_rng(43)

        df["temperature_2m"] = rng.uniform(8, 18, n).round(1)
        df["cloud_cover_total"] = rng.integers(70, 100, n)
        df["cloud_cover_low"] = rng.integers(60, 95, n)
        df["cloud_cover_medium"] = rng.integers(50, 80, n)
        df["cloud_cover_high"] = rng.integers(40, 70, n)
        df["precipitation_probability"] = rng.integers(60, 100, n)
        df["visibility"] = rng.uniform(500, 5000, n).round(0)
        df["wind_speed_10m"] = rng.uniform(5, 20, n).round(1)
        df["snowfall"] = 0.0
        df["rain"] = rng.uniform(1, 15, n).round(1)
        df["showers"] = rng.uniform(0, 5, n).round(1)
        df["weather_code"] = 61  # Slight rain

        return df

    def _generate_frost_weather(self, days: int) -> pd.DataFrame:
        """雾凇天: 低温, 低风速, 高湿度。"""
        df = self._make_base_dataframe(days)
        n = len(df)
        rng = np.random.default_rng(44)

        df["temperature_2m"] = rng.uniform(-8, 0, n).round(1)
        df["cloud_cover_total"] = rng.integers(40, 80, n)
        df["cloud_cover_low"] = rng.integers(30, 70, n)
        df["cloud_cover_medium"] = rng.integers(20, 50, n)
        df["cloud_cover_high"] = rng.integers(10, 40, n)
        df["precipitation_probability"] = rng.integers(5, 30, n)
        df["visibility"] = rng.uniform(2000, 10000, n).round(0)
        df["wind_speed_10m"] = rng.uniform(0, 5, n).round(1)
        df["snowfall"] = rng.uniform(0, 2, n).round(1)
        df["rain"] = 0.0
        df["showers"] = 0.0
        df["weather_code"] = 45  # Fog

        return df

    def _generate_snow_weather(self, days: int) -> pd.DataFrame:
        """降雪天: 低温, 有降雪, 适合树挂/雪景。"""
        df = self._make_base_dataframe(days)
        n = len(df)
        rng = np.random.default_rng(45)

        df["temperature_2m"] = rng.uniform(-10, -2, n).round(1)
        df["cloud_cover_total"] = rng.integers(60, 100, n)
        df["cloud_cover_low"] = rng.integers(40, 80, n)
        df["cloud_cover_medium"] = rng.integers(30, 60, n)
        df["cloud_cover_high"] = rng.integers(20, 50, n)
        df["precipitation_probability"] = rng.integers(40, 80, n)
        df["visibility"] = rng.uniform(1000, 8000, n).round(0)
        df["wind_speed_10m"] = rng.uniform(2, 10, n).round(1)
        df["snowfall"] = rng.uniform(1, 10, n).round(1)
        df["rain"] = 0.0
        df["showers"] = 0.0
        df["weather_code"] = 71  # Slight snow fall

        return df

    def _generate_ice_weather(self, days: int) -> pd.DataFrame:
        """冰挂天: 先有降水再冻结, 适合冰挂。"""
        df = self._make_base_dataframe(days)
        n = len(df)
        rng = np.random.default_rng(46)

        df["temperature_2m"] = rng.uniform(-5, 2, n).round(1)
        df["cloud_cover_total"] = rng.integers(50, 90, n)
        df["cloud_cover_low"] = rng.integers(30, 70, n)
        df["cloud_cover_medium"] = rng.integers(20, 50, n)
        df["cloud_cover_high"] = rng.integers(15, 40, n)
        df["precipitation_probability"] = rng.integers(30, 70, n)
        df["visibility"] = rng.uniform(3000, 12000, n).round(0)
        df["wind_speed_10m"] = rng.uniform(1, 8, n).round(1)
        df["snowfall"] = rng.uniform(0, 3, n).round(1)
        df["rain"] = rng.uniform(0.5, 5, n).round(1)
        df["showers"] = rng.uniform(0, 2, n).round(1)
        df["weather_code"] = 66  # Freezing rain

        return df
