"""缓存层单元测试

测试 MemoryCache / WeatherCache / MockMeteoFetcher。
测试用例严格遵循 module-03-cache-fetcher.md §测试计划。
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

from gmp.cache.memory_cache import MemoryCache
from gmp.cache.repository import CacheRepository
from gmp.cache.weather_cache import WeatherCache
from gmp.core.exceptions import APITimeoutError
from gmp.fetcher.mock_fetcher import MockMeteoFetcher


# ─── MemoryCache 测试 ───────────────────────────────────────────────


class TestMemoryCache:
    """MemoryCache 单元测试"""

    def test_memory_cache_hit(self):
        """写入后立即读取命中"""
        cache = MemoryCache(ttl_seconds=60)
        df = pd.DataFrame({"temperature_2m": [15.0, 16.0]})
        key = "29.75_102.35_2026-02-11"

        cache.set(key, df)
        result = cache.get(key)

        assert result is not None
        assert len(result) == 2
        assert result["temperature_2m"].iloc[0] == 15.0

    def test_memory_cache_miss(self):
        """未写入时读取返回 None"""
        cache = MemoryCache(ttl_seconds=60)
        result = cache.get("nonexistent_key")
        assert result is None

    def test_memory_cache_ttl_expire(self):
        """TTL 过期后返回 None"""
        cache = MemoryCache(ttl_seconds=1)
        df = pd.DataFrame({"temperature_2m": [15.0]})
        key = "29.75_102.35_2026-02-11"

        cache.set(key, df)
        assert cache.get(key) is not None

        # 等待超过 TTL
        time.sleep(1.1)
        result = cache.get(key)
        assert result is None

    def test_memory_cache_key_format(self):
        """key 格式为 "lat_lon_date" """
        key = MemoryCache.make_key(29.7512, 102.3489, "2026-02-11")
        assert key == "29.75_102.35_2026-02-11"

    def test_memory_cache_key_rounding(self):
        """坐标取整到 2 位小数"""
        key1 = MemoryCache.make_key(29.7512, 102.3489, "2026-02-11")
        key2 = MemoryCache.make_key(29.7523, 102.3451, "2026-02-11")
        assert key1 == key2

    def test_memory_cache_invalidate(self):
        """手动失效后返回 None"""
        cache = MemoryCache(ttl_seconds=60)
        df = pd.DataFrame({"temperature_2m": [15.0]})
        key = "test_key"

        cache.set(key, df)
        assert cache.get(key) is not None

        cache.invalidate(key)
        assert cache.get(key) is None

    def test_memory_cache_clear(self):
        """清空所有缓存"""
        cache = MemoryCache(ttl_seconds=60)
        cache.set("key1", pd.DataFrame({"a": [1]}))
        cache.set("key2", pd.DataFrame({"b": [2]}))

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


# ─── WeatherCache 测试 ──────────────────────────────────────────────


class TestWeatherCache:
    """WeatherCache 多级缓存测试"""

    def _make_weather_cache(self, ttl_mem=300, ttl_db=3600):
        """创建测试用 WeatherCache（使用 mock repo）"""
        memory = MemoryCache(ttl_seconds=ttl_mem)
        repo = MagicMock(spec=CacheRepository)
        repo.query.return_value = None
        return WeatherCache(memory, repo, ttl_db_seconds=ttl_db), memory, repo

    def test_weather_cache_fallback(self):
        """内存 Miss → SQLite 查询"""
        cache, memory, repo = self._make_weather_cache()
        target = date(2026, 2, 11)

        # 设置 SQLite 返回模拟数据
        from datetime import datetime
        repo.query.return_value = [
            {
                "forecast_hour": 0,
                "temperature_2m": 15.0,
                "fetched_at": datetime.now().isoformat(),
            }
        ]

        result = cache.get(29.75, 102.35, target, hours=[0])
        assert result is not None
        assert len(result) == 1
        repo.query.assert_called_once()

    def test_weather_cache_dual_write(self):
        """set 后内存和 SQLite 都有数据"""
        cache, memory, repo = self._make_weather_cache()
        target = date(2026, 2, 11)

        df = pd.DataFrame({
            "forecast_hour": [0, 1, 2],
            "temperature_2m": [15.0, 14.5, 14.0],
        })

        cache.set(29.75, 102.35, target, df)

        # 验证内存缓存有数据
        key = MemoryCache.make_key(29.75, 102.35, target.isoformat())
        mem_result = memory.get(key)
        assert mem_result is not None
        assert len(mem_result) == 3

        # 验证 SQLite upsert 被调用了 3 次 (每行一次)
        assert repo.upsert.call_count == 3

    def test_weather_cache_memory_hit_skips_sqlite(self):
        """内存缓存命中时不查 SQLite"""
        cache, memory, repo = self._make_weather_cache()
        target = date(2026, 2, 11)

        df = pd.DataFrame({"forecast_hour": [0], "temperature_2m": [15.0]})
        key = MemoryCache.make_key(29.75, 102.35, target.isoformat())
        memory.set(key, df)

        result = cache.get(29.75, 102.35, target)
        assert result is not None
        repo.query.assert_not_called()

    def test_get_or_fetch_calls_fetcher_on_miss(self):
        """缓存未命中时调用 fetcher"""
        cache, memory, repo = self._make_weather_cache()
        target = date(2026, 2, 11)

        fetched_df = pd.DataFrame({
            "forecast_hour": [0, 1],
            "temperature_2m": [15.0, 14.5],
        })
        fetcher_func = MagicMock(return_value=fetched_df)

        result = cache.get_or_fetch(29.75, 102.35, target, fetcher_func)
        assert result is not None
        assert len(result) == 2
        fetcher_func.assert_called_once()

    def test_get_or_fetch_uses_cache_when_hit(self):
        """缓存命中时不调用 fetcher"""
        cache, memory, repo = self._make_weather_cache()
        target = date(2026, 2, 11)

        df = pd.DataFrame({"forecast_hour": [0], "temperature_2m": [15.0]})
        key = MemoryCache.make_key(29.75, 102.35, target.isoformat())
        memory.set(key, df)

        fetcher_func = MagicMock()
        result = cache.get_or_fetch(29.75, 102.35, target, fetcher_func)
        assert result is not None
        fetcher_func.assert_not_called()


# ─── MockMeteoFetcher 测试 ──────────────────────────────────────────


class TestMockMeteoFetcher:
    """MockMeteoFetcher 场景测试"""

    def test_mock_fetcher_clear(self):
        """Mock 晴天数据格式正确"""
        fetcher = MockMeteoFetcher(scenario="clear")
        df = fetcher.fetch_hourly(29.75, 102.35, days=1)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 24  # 1 天 24 小时
        assert "temperature_2m" in df.columns
        assert "cloud_cover_total" in df.columns
        assert "precipitation_probability" in df.columns
        assert "visibility" in df.columns
        # 晴天: 云量低
        assert df["cloud_cover_total"].mean() < 30
        # 晴天: 无降水
        assert df["precipitation_probability"].mean() < 15

    def test_mock_fetcher_rain(self):
        """Mock 雨天降水概率 > 50%"""
        fetcher = MockMeteoFetcher(scenario="rain")
        df = fetcher.fetch_hourly(29.75, 102.35, days=1)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 24
        assert df["precipitation_probability"].mean() > 50
        assert df["rain"].sum() > 0

    def test_mock_fetcher_frost(self):
        """Mock 雾凇天: 低温低风速"""
        fetcher = MockMeteoFetcher(scenario="frost")
        df = fetcher.fetch_hourly(29.75, 102.35, days=1)

        assert isinstance(df, pd.DataFrame)
        assert df["temperature_2m"].mean() < 0
        assert df["wind_speed_10m"].mean() < 10

    def test_mock_fetcher_timeout(self):
        """timeout 场景抛出 APITimeoutError"""
        fetcher = MockMeteoFetcher(scenario="timeout")
        with pytest.raises(APITimeoutError):
            fetcher.fetch_hourly(29.75, 102.35)

    def test_mock_fetcher_call_log(self):
        """调用记录正确"""
        fetcher = MockMeteoFetcher(scenario="clear")
        fetcher.fetch_hourly(29.75, 102.35, days=3)
        fetcher.fetch_hourly(30.5, 103.0, days=1)

        assert len(fetcher.call_log) == 2
        assert fetcher.remote_call_count == 2
        assert fetcher.call_log[0]["lat"] == 29.75
        assert fetcher.call_log[0]["days"] == 3
        assert fetcher.call_log[1]["lat"] == 30.5

    def test_mock_fetcher_snow(self):
        """Mock 降雪天: 低温有降雪"""
        fetcher = MockMeteoFetcher(scenario="snow")
        df = fetcher.fetch_hourly(29.75, 102.35, days=1)

        assert df["temperature_2m"].mean() < 0
        assert df["snowfall"].sum() > 0

    def test_mock_fetcher_ice(self):
        """Mock 冰挂天: 有降水"""
        fetcher = MockMeteoFetcher(scenario="ice")
        df = fetcher.fetch_hourly(29.75, 102.35, days=1)

        assert df["rain"].sum() > 0

    def test_mock_fetcher_multi_points(self):
        """批量获取多坐标天气"""
        fetcher = MockMeteoFetcher(scenario="clear")
        coords = [(29.75, 102.35), (30.5, 103.0), (29.75, 102.35)]
        results = fetcher.fetch_multi_points(coords, days=1)

        # 第 1 和第 3 个坐标相同，去重后只有 2 个
        assert len(results) == 2
