"""gmp/cache/weather_cache.py — 缓存管理层

在 CacheRepository (底层 DB 操作) 之上，提供 DataFrame 级别的缓存接口，
以及数据新鲜度判断和 get_or_fetch 模式。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Callable

import pandas as pd
import structlog

from gmp.cache.repository import CacheRepository

logger = structlog.get_logger()


class WeatherCache:
    """DataFrame 级别的天气缓存管理"""

    def __init__(
        self,
        repository: CacheRepository,
        freshness_config: dict | None = None,
    ) -> None:
        """
        Args:
            repository: 底层数据库操作实例
            freshness_config: 新鲜度配置
                示例: {"forecast_valid_hours": 24, "archive_never_stale": True}
        """
        self._repo = repository
        self._config = freshness_config or {
            "forecast_valid_hours": 24,
            "archive_never_stale": True,
        }

    def get(
        self,
        lat: float,
        lon: float,
        target_date: date,
        hours: list[int] | None = None,
    ) -> pd.DataFrame | None:
        """获取缓存数据，返回 DataFrame 或 None"""
        rows = self._repo.query_weather(lat, lon, target_date, hours)
        if rows is None:
            return None
        df = pd.DataFrame(rows)
        if df.empty:
            return None
        return df

    def set(
        self,
        lat: float,
        lon: float,
        target_date: date,
        data: pd.DataFrame,
    ) -> None:
        """将 DataFrame 写入缓存。空 DataFrame 不写入。"""
        if data.empty:
            return
        now = datetime.now(timezone.utc).isoformat()
        rows = data.to_dict("records")
        for row in rows:
            row["fetched_at"] = now
        self._repo.upsert_weather_batch(lat, lon, target_date, rows)

    def get_or_fetch(
        self,
        lat: float,
        lon: float,
        target_date: date,
        fetch_fn: Callable[[], pd.DataFrame],
    ) -> pd.DataFrame:
        """有则用缓存，无则调用 fetch_fn 获取并缓存。

        fetch_fn 抛异常时，异常向上传播，缓存不写入。
        """
        cached = self.get(lat, lon, target_date)
        if cached is not None:
            logger.debug(
                "weather_cache.hit",
                lat=lat,
                lon=lon,
                target_date=str(target_date),
            )
            return cached

        logger.debug(
            "weather_cache.miss",
            lat=lat,
            lon=lon,
            target_date=str(target_date),
        )
        data = fetch_fn()
        self.set(lat, lon, target_date, data)
        return data

    def is_fresh(
        self,
        fetched_at: datetime,
        data_source: str = "forecast",
    ) -> bool:
        """判断数据是否新鲜

        - forecast: fetched_at 为今日 → True
        - archive: 永远 True
        """
        if data_source == "archive":
            return True
        # forecast: 同一天视为新鲜
        today = datetime.now().date()
        return fetched_at.date() == today
