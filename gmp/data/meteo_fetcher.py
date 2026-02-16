"""gmp/data/meteo_fetcher.py — Open-Meteo 气象数据获取

负责调用 Open-Meteo Forecast API 和 Archive API，解析响应为 DataFrame，
执行数据校验，并通过 WeatherCache 实现缓存。
"""

from __future__ import annotations

import time
import warnings
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import pandas as pd
import structlog

from gmp.cache.weather_cache import WeatherCache
from gmp.core.exceptions import APITimeoutError, DataDegradedWarning

logger = structlog.get_logger()

_CST = timezone(timedelta(hours=8))

# Open-Meteo API 需要请求的 hourly 字段
_HOURLY_FIELDS = (
    "temperature_2m,"
    "cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,"
    "cloud_base,"
    "precipitation_probability,"
    "visibility,"
    "wind_speed_10m,"
    "snowfall,rain,showers,"
    "weather_code"
)

# Open-Meteo 字段名 → GMP 内部字段名
_COLUMN_RENAME = {
    "cloud_cover": "cloud_cover_total",
    "cloud_cover_mid": "cloud_cover_medium",
    "cloud_base": "cloud_base_altitude",
}

# DataFrame 最终列顺序
_COLUMNS = [
    "forecast_date",
    "forecast_hour",
    "temperature_2m",
    "cloud_cover_total",
    "cloud_cover_low",
    "cloud_cover_medium",
    "cloud_cover_high",
    "cloud_base_altitude",
    "precipitation_probability",
    "visibility",
    "wind_speed_10m",
    "snowfall",
    "rain",
    "showers",
    "weather_code",
]


class MeteoFetcher:
    """Open-Meteo 气象数据获取器"""

    def __init__(
        self,
        cache: WeatherCache,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Args:
            cache: WeatherCache 缓存实例
            config: 配置字典，可选字段:
                - base_url: Forecast API 基地址
                - archive_base_url: Archive API 地址
                - connect_timeout: 连接超时秒数
                - read_timeout: 读取超时秒数
                - retries: 重试次数
                - retry_delay: 重试间隔秒数
        """
        cfg = config or {}
        self._cache = cache
        self._base_url = cfg.get(
            "base_url", "https://api.open-meteo.com/v1/forecast"
        )
        self._archive_base_url = cfg.get(
            "archive_base_url",
            "https://archive-api.open-meteo.com/v1/archive",
        )
        self._connect_timeout = cfg.get("connect_timeout", 5)
        self._read_timeout = cfg.get("read_timeout", 15)
        self._retries = cfg.get("retries", 2)
        self._retry_delay = cfg.get("retry_delay", 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_hourly(
        self,
        lat: float,
        lon: float,
        days: int = 7,
        past_days: int = 0,
    ) -> pd.DataFrame:
        """获取逐小时天气预报。

        1. 先查缓存
        2. 缓存未命中 → 调用 API
        3. 解析响应 → DataFrame
        4. 数据校验
        5. 写入缓存
        6. 返回 DataFrame
        """
        # 1) 尝试缓存
        today = datetime.now(_CST).date()
        cached = self._cache.get(lat, lon, today)
        if cached is not None:
            logger.debug("meteo_fetcher.cache_hit", lat=lat, lon=lon)
            return cached

        # 2) 构建请求参数
        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": _HOURLY_FIELDS,
            "forecast_days": days,
        }
        if past_days > 0:
            params["past_days"] = past_days

        # 3) 调用 API
        raw = self._call_api(self._base_url, params)

        # 4) 解析 + 校验
        df = self._parse_response(raw)
        df = self._validate_data(df)

        # 5) 写入缓存 — 按日期分组存储
        for d, group in df.groupby("forecast_date"):
            cache_date = date.fromisoformat(d) if isinstance(d, str) else d
            self._cache.set(lat, lon, cache_date, group)

        return df

    def fetch_historical(
        self,
        lat: float,
        lon: float,
        target_date: date,
    ) -> pd.DataFrame:
        """获取历史天气 (回测用), 使用 Archive API"""
        # 尝试缓存
        cached = self._cache.get(lat, lon, target_date)
        if cached is not None:
            return cached

        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": _HOURLY_FIELDS,
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        raw = self._call_api(self._archive_base_url, params)
        df = self._parse_response(raw)
        df = self._validate_data(df)

        self._cache.set(lat, lon, target_date, df)
        return df

    def fetch_multi_points(
        self,
        coords: list[tuple[float, float]],
        days: int = 7,
    ) -> dict[tuple[float, float], pd.DataFrame]:
        """批量获取多坐标天气（光路点 + 目标点）。

        坐标先 ROUND(2) 去重以减少 API 调用。
        """
        if not coords:
            return {}

        # 去重
        unique: dict[tuple[float, float], None] = {}
        for lat, lon in coords:
            rounded = (round(lat, 2), round(lon, 2))
            unique[rounded] = None

        result: dict[tuple[float, float], pd.DataFrame] = {}
        for lat, lon in unique:
            df = self.fetch_hourly(lat, lon, days=days)
            result[(lat, lon)] = df

        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_api(self, url: str, params: dict[str, Any]) -> dict:
        """HTTP GET 调用 + 重试 + 超时处理"""
        timeout = httpx.Timeout(
            connect=self._connect_timeout,
            read=self._read_timeout,
            write=5.0,
            pool=5.0,
        )
        last_exc: Exception | None = None

        for attempt in range(1 + self._retries):
            try:
                response = httpx.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "meteo_fetcher.timeout",
                    url=url,
                    attempt=attempt + 1,
                    max_retries=self._retries,
                )
                if attempt < self._retries:
                    time.sleep(self._retry_delay)

        raise APITimeoutError("open-meteo", self._read_timeout)

    def _parse_response(self, response: dict) -> pd.DataFrame:
        """解析 Open-Meteo JSON 响应 → DataFrame

        字段名映射:
        - cloud_cover → cloud_cover_total
        - cloud_cover_mid → cloud_cover_medium
        - cloud_base → cloud_base_altitude
        """
        hourly = response["hourly"]

        # 提取时间 → forecast_date + forecast_hour
        timestamps = hourly["time"]
        dates = []
        hours = []
        for ts in timestamps:
            dt = datetime.fromisoformat(ts)
            dates.append(dt.date().isoformat())
            hours.append(dt.hour)

        # 构建 DataFrame
        data: dict[str, Any] = {
            "forecast_date": dates,
            "forecast_hour": hours,
        }

        # 映射和拷贝字段
        for api_field in [
            "temperature_2m",
            "cloud_cover",
            "cloud_cover_low",
            "cloud_cover_mid",
            "cloud_cover_high",
            "cloud_base",
            "precipitation_probability",
            "visibility",
            "wind_speed_10m",
            "snowfall",
            "rain",
            "showers",
            "weather_code",
        ]:
            col_name = _COLUMN_RENAME.get(api_field, api_field)
            data[col_name] = hourly[api_field]

        df = pd.DataFrame(data)
        return df[_COLUMNS]

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据校验: clip 异常值, None 填充默认值

        规则 (设计文档 §8.10):
        - cloud_base_altitude: None → 10000
        - visibility: None → 0
        - wind_speed_10m: None → 0
        - precipitation_probability: clip 0-100
        - cloud_cover*: clip 0-100
        - temperature_2m: 超出 -60~60 → DataDegradedWarning
        """
        df = df.copy()

        # None 替换
        df["cloud_base_altitude"] = df["cloud_base_altitude"].fillna(10000)
        df["visibility"] = df["visibility"].fillna(0)
        df["wind_speed_10m"] = df["wind_speed_10m"].fillna(0)

        # clip 范围
        df["precipitation_probability"] = df["precipitation_probability"].clip(0, 100)
        for col in ["cloud_cover_total", "cloud_cover_low", "cloud_cover_medium", "cloud_cover_high"]:
            df[col] = df[col].clip(0, 100)

        # 温度异常检测
        temp = df["temperature_2m"]
        if ((temp < -60) | (temp > 60)).any():
            warnings.warn(
                "temperature_2m 包含超出 -60°C~60°C 范围的值，标记为 degraded",
                DataDegradedWarning,
                stacklevel=2,
            )

        return df
