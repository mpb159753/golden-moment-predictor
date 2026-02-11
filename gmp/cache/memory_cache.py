"""TTL 内存缓存

三级缓存架构的第一层 — 内存缓存，基于 TTL 自动过期。
接口定义遵循 design/07-code-interface.md §7.1。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


class MemoryCache:
    """TTL 内存缓存

    存储 key → (DataFrame, timestamp) 映射。
    当缓存条目超过 TTL 时间后自动视为过期。
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._storage: dict[str, tuple[pd.DataFrame, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> pd.DataFrame | None:
        """获取缓存数据，过期返回 None。

        Args:
            key: 缓存键

        Returns:
            缓存的 DataFrame 或 None（过期/不存在）
        """
        if key not in self._storage:
            return None

        data, cached_at = self._storage[key]
        if datetime.now() - cached_at > self._ttl:
            # 过期自动清理
            del self._storage[key]
            return None

        return data

    def set(self, key: str, data: pd.DataFrame) -> None:
        """写入缓存 + 当前时间戳。

        Args:
            key: 缓存键
            data: 要缓存的 DataFrame
        """
        self._storage[key] = (data, datetime.now())

    def invalidate(self, key: str) -> None:
        """手动失效指定缓存条目。

        Args:
            key: 缓存键
        """
        self._storage.pop(key, None)

    def clear(self) -> None:
        """清空所有缓存。"""
        self._storage.clear()

    @staticmethod
    def make_key(lat: float, lon: float, date_str: str) -> str:
        """生成缓存 key。

        使用坐标取整到 2 位小数 + 日期字符串组合。

        Args:
            lat: 纬度
            lon: 经度
            date_str: 日期字符串 (如 "2026-02-11")

        Returns:
            缓存 key，格式如 "29.75_102.35_2026-02-11"
        """
        return f"{round(lat, 2)}_{round(lon, 2)}_{date_str}"
