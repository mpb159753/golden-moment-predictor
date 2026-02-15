"""tests/unit/test_weather_cache.py — WeatherCache 单元测试

测试缓存管理层，包括 DataFrame 读写、新鲜度判断、get_or_fetch 模式。
"""

from datetime import date, datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from gmp.cache.repository import CacheRepository
from gmp.cache.weather_cache import WeatherCache

# ==================== Fixtures ====================


@pytest.fixture
def repo():
    """内存数据库的 CacheRepository"""
    r = CacheRepository(":memory:")
    yield r
    r.close()


@pytest.fixture
def cache(repo):
    """WeatherCache 实例"""
    return WeatherCache(repo)


def _make_df(hours=None, temperature=-10.0):
    """辅助函数: 生成测试用 DataFrame"""
    if hours is None:
        hours = list(range(24))
    rows = []
    for h in hours:
        rows.append(
            {
                "forecast_hour": h,
                "fetched_at": "2026-02-10 08:00:00",
                "temperature_2m": temperature + h * 0.5,
                "cloud_cover_total": 15,
                "cloud_cover_low": 5,
                "cloud_cover_medium": 8,
                "cloud_cover_high": 2,
                "cloud_base_altitude": 5200.0,
                "precipitation_probability": 0,
                "visibility": 45000.0,
                "wind_speed_10m": 8.5,
                "snowfall": 0.0,
                "rain": 0.0,
                "showers": 0.0,
                "weather_code": 0,
            }
        )
    return pd.DataFrame(rows)


# ==================== set + get 读写循环 ====================


class TestSetAndGet:
    def test_roundtrip(self, cache):
        """set + get 完整循环: DataFrame 写入后能读出相同数据"""
        df = _make_df(hours=[6, 7, 8])
        cache.set(29.58, 101.88, date(2026, 2, 11), df)

        result = cache.get(29.58, 101.88, date(2026, 2, 11))
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert list(result["forecast_hour"]) == [6, 7, 8]

    def test_get_no_data_returns_none(self, cache):
        """get 无数据返回 None"""
        result = cache.get(0.0, 0.0, date(2026, 1, 1))
        assert result is None

    def test_empty_dataframe_returns_none(self, cache):
        """空 DataFrame (0 行) 写入后 get 返回 None"""
        empty_df = pd.DataFrame()
        cache.set(29.58, 101.88, date(2026, 2, 11), empty_df)
        result = cache.get(29.58, 101.88, date(2026, 2, 11))
        assert result is None

    def test_dataframe_column_mapping(self, cache):
        """DataFrame 列名与 weather_cache 表字段对应"""
        df = _make_df(hours=[6])
        cache.set(29.58, 101.88, date(2026, 2, 11), df)

        result = cache.get(29.58, 101.88, date(2026, 2, 11))
        expected_cols = {
            "forecast_hour",
            "fetched_at",
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
        }
        # 结果 DataFrame 应包含这些列
        assert expected_cols.issubset(set(result.columns))


# ==================== is_fresh 新鲜度判断 ====================


class TestIsFresh:
    def test_forecast_today_is_fresh(self, cache):
        """forecast 数据今日获取 → True"""
        now = datetime.now()
        fetched_at = now.replace(hour=8, minute=0, second=0)
        assert cache.is_fresh(fetched_at, data_source="forecast") is True

    def test_forecast_yesterday_is_stale(self, cache):
        """forecast 数据昨日获取 → False"""
        from datetime import timedelta

        yesterday = datetime.now() - timedelta(days=1)
        assert cache.is_fresh(yesterday, data_source="forecast") is False

    def test_archive_always_fresh(self, cache):
        """archive 数据无论何时获取 → True"""
        from datetime import timedelta

        old_time = datetime.now() - timedelta(days=365)
        assert cache.is_fresh(old_time, data_source="archive") is True


# ==================== get_or_fetch ====================


class TestGetOrFetch:
    def test_cache_hit_skips_fetch(self, cache):
        """缓存命中时不调用 fetch_fn"""
        df = _make_df(hours=[6, 7, 8])
        cache.set(29.58, 101.88, date(2026, 2, 11), df)

        mock_fn = MagicMock()
        result = cache.get_or_fetch(29.58, 101.88, date(2026, 2, 11), mock_fn)
        mock_fn.assert_not_called()
        assert len(result) == 3

    def test_cache_miss_calls_fetch(self, cache):
        """缓存未命中时调用 fetch_fn 并写入缓存"""
        df = _make_df(hours=[6, 7, 8])
        mock_fn = MagicMock(return_value=df)

        result = cache.get_or_fetch(29.58, 101.88, date(2026, 2, 11), mock_fn)
        mock_fn.assert_called_once()
        assert len(result) == 3

        # 验证数据已写入缓存
        cached = cache.get(29.58, 101.88, date(2026, 2, 11))
        assert cached is not None
        assert len(cached) == 3

    def test_fetch_exception_propagates(self, cache):
        """fetch_fn 抛异常 → 异常向上传播，缓存不写入"""
        mock_fn = MagicMock(side_effect=RuntimeError("API down"))

        with pytest.raises(RuntimeError, match="API down"):
            cache.get_or_fetch(29.58, 101.88, date(2026, 2, 11), mock_fn)

        # 缓存未被写入
        assert cache.get(29.58, 101.88, date(2026, 2, 11)) is None
