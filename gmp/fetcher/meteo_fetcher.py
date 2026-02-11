"""Open-Meteo API 数据获取器

使用 httpx 调用 Open-Meteo 免费 API 获取逐小时天气预报。
实现降级策略: API 超时 → 查 SQLite 过期数据 → 抛 ServiceUnavailableError。
接口定义遵循 design/07-code-interface.md §7.1 IFetcher。
"""

from __future__ import annotations

import logging
import time
import warnings
from datetime import date, timedelta

import httpx
import pandas as pd

from gmp.cache.weather_cache import WeatherCache
from gmp.core.exceptions import (
    APITimeoutError,
    DataDegradedWarning,
    ServiceUnavailableError,
)
from gmp.fetcher.base import BaseFetcher

logger = logging.getLogger(__name__)

# 默认超时配置 (来自设计文档 §8.3)
DEFAULT_TIMEOUT_CONFIG = {
    "connect_timeout": 5,
    "read_timeout": 15,
    "retries": 2,
    "retry_delay": 1,
}


class MeteoFetcher(BaseFetcher):
    """Open-Meteo API 实现

    支持:
    - 逐小时预报 (fetch_hourly)
    - 批量多坐标获取 (fetch_multi_points)
    - 坐标去重
    - 多日数据按日分组缓存
    - 降级策略 (API 失败 → SQLite 过期数据)
    - 超时重试
    """

    API_URL = "https://api.open-meteo.com/v1/forecast"

    HOURLY_PARAMS = [
        "temperature_2m",
        "cloud_cover",
        "cloud_cover_low",
        "cloud_cover_mid",
        "cloud_cover_high",
        "precipitation_probability",
        "visibility",
        "wind_speed_10m",
        "weather_code",
        "snowfall",
        "rain",
        "showers",
    ]

    def __init__(
        self,
        cache: WeatherCache | None = None,
        timeout_config: dict | None = None,
    ) -> None:
        self._cache = cache
        self._timeout_config = timeout_config or DEFAULT_TIMEOUT_CONFIG.copy()

    def fetch_hourly(
        self, lat: float, lon: float, days: int = 7
    ) -> pd.DataFrame:
        """获取小时级天气预报（先查缓存再调 API）。

        对多日数据按日分组进行缓存查询和写入，确保每天的数据都被正确缓存。

        Args:
            lat: 纬度
            lon: 经度
            days: 预报天数

        Returns:
            逐小时天气 DataFrame

        Raises:
            APITimeoutError: API 超时且无降级数据
            ServiceUnavailableError: API 不可用且无缓存
        """
        today = date.today()

        # 尝试从缓存获取所有天的数据
        if self._cache:
            cached_frames = []
            all_cached = True
            for d in range(days):
                target_date = today + timedelta(days=d)
                cached = self._cache.get(lat, lon, target_date)
                if cached is not None:
                    cached_frames.append(cached)
                else:
                    all_cached = False
                    break

            if all_cached and cached_frames:
                return pd.concat(cached_frames, ignore_index=True)

        # 调用 API
        try:
            data = self._call_api(lat, lon, days)
            # 按日分组写入缓存
            if self._cache and "forecast_date" in data.columns:
                for date_str, group in data.groupby("forecast_date"):
                    target_date = date.fromisoformat(str(date_str))
                    self._cache.set(
                        lat, lon, target_date, group.reset_index(drop=True)
                    )
            return data
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            logger.warning("API 调用失败: %s", e)
            return self._handle_degradation(lat, lon, today, e)

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
        # 坐标去重 (round to 2 decimals)
        unique_coords = list({
            (round(lat, 2), round(lon, 2)) for lat, lon in coords
        })

        results: dict[tuple, pd.DataFrame] = {}
        for lat, lon in unique_coords:
            df = self.fetch_hourly(lat, lon, days)
            results[(lat, lon)] = df

        return results

    def _call_api(self, lat: float, lon: float, days: int) -> pd.DataFrame:
        """调用 Open-Meteo API。"""
        params = {
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "hourly": ",".join(self.HOURLY_PARAMS),
            "forecast_days": days,
            "timezone": "Asia/Shanghai",
        }

        timeout = httpx.Timeout(
            connect=self._timeout_config["connect_timeout"],
            read=self._timeout_config["read_timeout"],
            write=10.0,
            pool=10.0,
        )

        retries = self._timeout_config.get("retries", 2)
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                response = httpx.get(
                    self.API_URL,
                    params=params,
                    timeout=timeout,
                )
                response.raise_for_status()
                return self._parse_response(response.json())
            except (httpx.TimeoutException, httpx.HTTPError) as e:
                last_error = e
                if attempt < retries:
                    delay = self._timeout_config.get("retry_delay", 1)
                    logger.info("重试第 %d 次 (delay=%ds)", attempt + 1, delay)
                    time.sleep(delay)

        raise last_error  # type: ignore[misc]

    def _parse_response(self, response: dict) -> pd.DataFrame:
        """解析 Open-Meteo JSON → DataFrame。

        将 API 返回的 ``hourly`` 字段的数组数据转换为标准 DataFrame，
        并重命名列名以匹配内部字段名约定。
        """
        hourly = response.get("hourly", {})
        if not hourly:
            return pd.DataFrame()

        df = pd.DataFrame(hourly)

        # 解析时间列
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            df["forecast_date"] = df["time"].dt.date.astype(str)
            df["forecast_hour"] = df["time"].dt.hour

        # 列名映射 (Open-Meteo → 内部字段: 只做必要重命名)
        rename_map = {
            "cloud_cover": "cloud_cover_total",
            "cloud_cover_mid": "cloud_cover_medium",
        }
        df = df.rename(columns=rename_map)

        return df

    def _handle_degradation(
        self,
        lat: float,
        lon: float,
        target_date: date,
        original_error: Exception,
    ) -> pd.DataFrame:
        """降级策略: API 失败时尝试使用过期的 SQLite 缓存数据。

        1. 查 SQLite (ignore_ttl=True) 获取过期数据
        2. 有过期数据 → 返回 + 警告 DataDegradedWarning
        3. 无数据 → 抛出 ServiceUnavailableError
        """
        if self._cache:
            degraded_data = self._cache.get(
                lat, lon, target_date, ignore_ttl=True
            )
            if degraded_data is not None:
                warnings.warn(
                    f"使用降级数据: lat={lat}, lon={lon}, date={target_date}",
                    DataDegradedWarning,
                    stacklevel=2,
                )
                logger.warning("返回降级数据: lat=%.2f, lon=%.2f", lat, lon)
                return degraded_data

        raise ServiceUnavailableError(
            "open-meteo",
            f"API 超时且无缓存数据: {original_error}",
        )
