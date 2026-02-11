"""TTL 内存缓存

三级缓存架构的第一层 — 内存缓存，基于 TTL 自动过期。
支持 max_size 上限，超过时按 LRU 策略淘汰最久未访问的条目。
接口定义遵循 design/07-code-interface.md §7.1。
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta

import pandas as pd


class MemoryCache:
    """TTL 内存缓存

    存储 key → (DataFrame, timestamp) 映射。
    当缓存条目超过 TTL 时间后自动视为过期。
    当条目数量达到 max_size 时，按 LRU 策略淘汰最久未访问的条目。
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1024) -> None:
        self._storage: OrderedDict[str, tuple[pd.DataFrame, datetime]] = (
            OrderedDict()
        )
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_size = max_size

    def get(self, key: str) -> pd.DataFrame | None:
        """获取缓存数据，过期返回 None。

        命中时会将条目移到最新位置 (LRU 更新)。

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

        # LRU: 移到末尾 (最近使用)
        self._storage.move_to_end(key)
        return data

    def set(self, key: str, data: pd.DataFrame) -> None:
        """写入缓存 + 当前时间戳。

        若已存在则更新并移到末尾；若达到 max_size 则淘汰最久未使用的条目。

        Args:
            key: 缓存键
            data: 要缓存的 DataFrame
        """
        if key in self._storage:
            # 已存在：更新并移到末尾
            self._storage[key] = (data, datetime.now())
            self._storage.move_to_end(key)
        else:
            # 新条目：检查容量
            if len(self._storage) >= self._max_size:
                # 淘汰最旧 (最前面) 的条目
                self._storage.popitem(last=False)
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

    @property
    def size(self) -> int:
        """当前缓存条目数量。"""
        return len(self._storage)

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
