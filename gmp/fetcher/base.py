"""BaseFetcher 抽象基类

定义数据获取器的统一接口。
接口定义遵循 design/07-code-interface.md §7.1 IFetcher Protocol。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseFetcher(ABC):
    """数据获取器抽象基类

    所有天气数据获取器（Open-Meteo、Mock 等）都必须实现此接口。
    """

    @abstractmethod
    def fetch_hourly(
        self, lat: float, lon: float, days: int = 7
    ) -> pd.DataFrame:
        """获取小时级天气预报。

        Args:
            lat: 纬度
            lon: 经度
            days: 预报天数

        Returns:
            包含逐小时天气数据的 DataFrame，列包括:
            - forecast_date: 日期
            - forecast_hour: 小时 (0-23)
            - temperature_2m: 2m 温度 (°C)
            - cloud_cover_total: 总云量 (%)
            - cloud_cover_low: 低云量 (%)
            - cloud_cover_medium: 中云量 (%)
            - cloud_cover_high: 高云量 (%)
            - precipitation_probability: 降水概率 (%)
            - visibility: 能见度 (m)
            - wind_speed_10m: 10m 风速 (km/h)
            - snowfall: 降雪量 (cm)
            - rain: 降雨量 (mm)
            - showers: 阵雨量 (mm)
            - weather_code: 天气代码 (WMO)
        """
        ...

    @abstractmethod
    def fetch_multi_points(
        self,
        coords: list[tuple[float, float]],
        days: int = 1,
    ) -> dict[tuple, pd.DataFrame]:
        """批量获取多个坐标点的天气（坐标去重）。

        Args:
            coords: 坐标列表 [(lat, lon), ...]
            days: 预报天数

        Returns:
            {(lat, lon): DataFrame, ...}
        """
        ...
