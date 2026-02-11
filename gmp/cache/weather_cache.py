"""多级缓存门面

三级缓存查询链路: 内存缓存 → SQLite → 外部 API (via fetcher_func)。
接口定义遵循 design/07-code-interface.md §7.1。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Callable

import pandas as pd

from gmp.cache.memory_cache import MemoryCache
from gmp.cache.repository import CacheRepository

logger = logging.getLogger(__name__)


class WeatherCache:
    """多级缓存门面

    查询顺序:
    1. 内存缓存 (TTL 由 MemoryCache 决定)
    2. SQLite 持久化缓存 (TTL 由 ttl_db_seconds 决定)
    3. 外部 API (通过 get_or_fetch 的 fetcher_func 回调)

    写入时双写: 同时写入内存缓存 + SQLite。
    """

    def __init__(
        self,
        memory_cache: MemoryCache,
        repository: CacheRepository,
        ttl_db_seconds: int = 3600,
    ) -> None:
        self._memory = memory_cache
        self._repo = repository
        self._ttl_db = timedelta(seconds=ttl_db_seconds)

    def get(
        self,
        lat: float,
        lon: float,
        target_date: date,
        hours: list[int] | None = None,
        ignore_ttl: bool = False,
    ) -> pd.DataFrame | None:
        """多级查询: 内存 → SQLite → None。

        Args:
            lat: 纬度
            lon: 经度
            target_date: 目标日期
            hours: 需要的小时列表，None 表示全天 (0-23)
            ignore_ttl: 是否忽略 TTL（降级模式使用）

        Returns:
            缓存的 DataFrame 或 None
        """
        if hours is None:
            hours = list(range(24))

        date_str = target_date.isoformat()
        cache_key = MemoryCache.make_key(lat, lon, date_str)

        # 第一级: 内存缓存
        mem_data = self._memory.get(cache_key)
        if mem_data is not None:
            logger.debug("内存缓存命中: %s", cache_key)
            return mem_data

        # 第二级: SQLite
        rows = self._repo.query(lat, lon, target_date, hours)
        if rows:
            # 检查 TTL
            fetched_at_str = rows[0].get("fetched_at", "")
            if fetched_at_str:
                fetched_at = datetime.fromisoformat(fetched_at_str)
                age = datetime.now() - fetched_at
                if not ignore_ttl and age > self._ttl_db:
                    logger.debug("SQLite 缓存过期: %s (age=%s)", cache_key, age)
                    return None

            df = pd.DataFrame(rows)
            # 回填内存缓存
            self._memory.set(cache_key, df)
            logger.debug("SQLite 缓存命中: %s", cache_key)
            return df

        return None

    def set(
        self,
        lat: float,
        lon: float,
        target_date: date,
        data: pd.DataFrame,
    ) -> None:
        """双写: 内存 + SQLite。

        Args:
            lat: 纬度
            lon: 经度
            target_date: 目标日期
            data: 天气数据 DataFrame
        """
        date_str = target_date.isoformat()
        cache_key = MemoryCache.make_key(lat, lon, date_str)

        # 写入内存缓存
        self._memory.set(cache_key, data)

        # 写入 SQLite — 批量 upsert
        rows = [row.to_dict() for _, row in data.iterrows()]
        self._repo.upsert_batch(lat, lon, target_date, rows)

        logger.debug("双写完成: %s (%d 条)", cache_key, len(data))

    def get_or_fetch(
        self,
        lat: float,
        lon: float,
        target_date: date,
        fetcher_func: Callable[[], pd.DataFrame],
    ) -> pd.DataFrame:
        """缓存未命中时自动调用 fetcher 获取数据。

        Args:
            lat: 纬度
            lon: 经度
            target_date: 目标日期
            fetcher_func: 无参回调，返回 DataFrame

        Returns:
            天气数据 DataFrame
        """
        # 先查缓存
        cached = self.get(lat, lon, target_date)
        if cached is not None:
            return cached

        # 缓存 miss，调用 fetcher
        logger.info("缓存未命中，调用 fetcher: lat=%.2f, lon=%.2f, date=%s",
                     lat, lon, target_date)
        data = fetcher_func()

        # 双写缓存
        self.set(lat, lon, target_date, data)

        return data
