"""MeteoFetcher 单元测试

测试 Open-Meteo API 获取器的核心逻辑，包括:
- 响应解析 (_parse_response)
- 缓存集成 (fetch_hourly 缓存读写)
- 降级策略 (_handle_degradation)
- 重试机制
- 批量去重

所有 HTTP 请求通过 unittest.mock.patch 模拟。
"""

from __future__ import annotations

import json
import warnings
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pandas as pd
import pytest

from gmp.cache.memory_cache import MemoryCache
from gmp.cache.weather_cache import WeatherCache
from gmp.core.exceptions import (
    DataDegradedWarning,
    ServiceUnavailableError,
)
from gmp.fetcher.meteo_fetcher import MeteoFetcher

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ─── 辅助函数 ───────────────────────────────────────────────────────


def _load_fixture(name: str) -> dict:
    """加载 fixture JSON 文件。"""
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _make_mock_response(fixture_name: str, status_code: int = 200) -> MagicMock:
    """创建模拟的 httpx.Response。"""
    data = _load_fixture(fixture_name)
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


def _make_fetcher_with_cache(
    ttl_mem: int = 300, ttl_db: int = 3600
) -> tuple[MeteoFetcher, WeatherCache, MemoryCache, MagicMock]:
    """创建带 mock 缓存的 MeteoFetcher。"""
    from gmp.cache.repository import CacheRepository

    memory = MemoryCache(ttl_seconds=ttl_mem)
    repo = MagicMock(spec=CacheRepository)
    repo.query.return_value = None
    cache = WeatherCache(memory, repo, ttl_db_seconds=ttl_db)
    fetcher = MeteoFetcher(
        cache=cache,
        timeout_config={"connect_timeout": 1, "read_timeout": 1, "retries": 0, "retry_delay": 0},
    )
    return fetcher, cache, memory, repo


# ─── _parse_response 测试 ───────────────────────────────────────────


class TestParseResponse:
    """响应解析测试"""

    def test_parse_response_clear(self):
        """解析晴天 fixture JSON: 列名正确, 数据完整"""
        fetcher = MeteoFetcher()
        data = _load_fixture("weather_data_clear.json")
        df = fetcher._parse_response(data)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 24
        # 验证列名重命名: cloud_cover → cloud_cover_total
        assert "cloud_cover_total" in df.columns
        assert "cloud_cover" not in df.columns
        # 验证列名重命名: cloud_cover_mid → cloud_cover_medium
        assert "cloud_cover_medium" in df.columns
        assert "cloud_cover_mid" not in df.columns
        # 验证时间解析
        assert "forecast_date" in df.columns
        assert "forecast_hour" in df.columns
        assert df["forecast_hour"].min() == 0
        assert df["forecast_hour"].max() == 23

    def test_parse_response_rainy(self):
        """解析雨天 fixture JSON: 高云量, 有降水"""
        fetcher = MeteoFetcher()
        data = _load_fixture("weather_data_rainy.json")
        df = fetcher._parse_response(data)

        assert len(df) == 24
        assert df["cloud_cover_total"].mean() > 70
        assert df["rain"].sum() > 0
        assert df["precipitation_probability"].mean() > 50

    def test_parse_response_empty(self):
        """空响应返回空 DataFrame"""
        fetcher = MeteoFetcher()
        df = fetcher._parse_response({})
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_parse_response_no_hourly(self):
        """响应中无 hourly 字段返回空 DataFrame"""
        fetcher = MeteoFetcher()
        df = fetcher._parse_response({"latitude": 29.75, "longitude": 102.35})
        assert len(df) == 0

    def test_column_rename(self):
        """cloud_cover → cloud_cover_total, cloud_cover_mid → cloud_cover_medium"""
        fetcher = MeteoFetcher()
        data = {
            "hourly": {
                "time": ["2026-02-11T08:00"],
                "cloud_cover": [25],
                "cloud_cover_mid": [10],
                "cloud_cover_low": [5],
                "cloud_cover_high": [3],
                "temperature_2m": [15.0],
            }
        }
        df = fetcher._parse_response(data)
        assert df["cloud_cover_total"].iloc[0] == 25
        assert df["cloud_cover_medium"].iloc[0] == 10


# ─── fetch_hourly 缓存集成测试 ─────────────────────────────────────


class TestFetchHourlyCaching:
    """fetch_hourly 缓存查询和写入测试"""

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_fetch_hourly_api_success(self, mock_get):
        """API 正常返回: 数据完整"""
        mock_get.return_value = _make_mock_response("weather_data_clear.json")
        fetcher = MeteoFetcher(
            timeout_config={"connect_timeout": 1, "read_timeout": 1, "retries": 0, "retry_delay": 0}
        )

        df = fetcher.fetch_hourly(29.75, 102.35, days=1)
        assert len(df) == 24
        mock_get.assert_called_once()

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_fetch_hourly_uses_cache(self, mock_get):
        """缓存命中时不调用 API"""
        fetcher, cache, memory, _ = _make_fetcher_with_cache()
        today = date.today()

        # 预填充缓存 (模拟 days=1 的数据)
        cached_df = pd.DataFrame({
            "forecast_date": [today.isoformat()] * 24,
            "forecast_hour": list(range(24)),
            "temperature_2m": [15.0] * 24,
        })
        key = MemoryCache.make_key(29.75, 102.35, today.isoformat())
        memory.set(key, cached_df)

        df = fetcher.fetch_hourly(29.75, 102.35, days=1)
        assert len(df) == 24
        mock_get.assert_not_called()

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_fetch_hourly_writes_cache(self, mock_get):
        """API 成功后按日分组写入缓存"""
        mock_get.return_value = _make_mock_response("weather_data_clear.json")
        fetcher, cache, memory, repo = _make_fetcher_with_cache()

        fetcher.fetch_hourly(29.75, 102.35, days=1)

        # 验证数据写入了内存缓存
        today = date.today()
        # _parse_response 会生成 forecast_date 列，但 fixture 数据是 2026-02-11
        # 所以缓存 key 应该对应 fixture 中的日期
        key = MemoryCache.make_key(29.75, 102.35, "2026-02-11")
        cached = memory.get(key)
        assert cached is not None

        # 验证 repo.upsert_batch 被调用
        assert repo.upsert_batch.call_count >= 1


# ─── 降级策略测试 (T3) ──────────────────────────────────────────────


class TestDegradation:
    """降级策略测试 — 覆盖设计文档 §8.2"""

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_degradation_uses_stale_cache(self, mock_get):
        """API 超时 + 有过期缓存 → 返回降级数据"""
        mock_get.side_effect = httpx.TimeoutException("connect timeout")
        fetcher, cache, memory, repo = _make_fetcher_with_cache()

        # 模拟 SQLite 中有过期数据
        from datetime import datetime
        stale_data = [
            {
                "forecast_hour": h,
                "temperature_2m": 10.0 + h,
                "fetched_at": datetime.now().isoformat(),
            }
            for h in range(24)
        ]
        # 第一次查询 (正常 cache.get) 返回 None → 触发 API → 降级
        # 第二次查询 (ignore_ttl=True) 返回过期数据
        repo.query.side_effect = [None, stale_data]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            df = fetcher.fetch_hourly(29.75, 102.35, days=1)

            assert df is not None
            assert len(df) == 24
            # 验证发出了降级警告
            degraded_warnings = [x for x in w if issubclass(x.category, DataDegradedWarning)]
            assert len(degraded_warnings) >= 1

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_degradation_no_cache_raises(self, mock_get):
        """API 超时 + 无缓存 → ServiceUnavailableError"""
        mock_get.side_effect = httpx.TimeoutException("connect timeout")
        fetcher, cache, memory, repo = _make_fetcher_with_cache()

        # repo.query 默认返回 None (无缓存)

        with pytest.raises(ServiceUnavailableError) as exc_info:
            fetcher.fetch_hourly(29.75, 102.35, days=1)

        assert "open-meteo" in exc_info.value.service

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_degradation_no_cache_at_all_raises(self, mock_get):
        """API 超时 + 完全没有缓存实例 → ServiceUnavailableError"""
        mock_get.side_effect = httpx.TimeoutException("connect timeout")
        fetcher = MeteoFetcher(
            cache=None,
            timeout_config={"connect_timeout": 1, "read_timeout": 1, "retries": 0, "retry_delay": 0},
        )

        with pytest.raises(ServiceUnavailableError):
            fetcher.fetch_hourly(29.75, 102.35, days=1)

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_degradation_warning_issued(self, mock_get):
        """降级时发出 DataDegradedWarning"""
        mock_get.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=MagicMock()
        )
        fetcher, cache, memory, repo = _make_fetcher_with_cache()

        from datetime import datetime
        stale_data = [
            {"forecast_hour": 0, "temperature_2m": 10.0, "fetched_at": datetime.now().isoformat()}
        ]
        # 第一次查询返回 None → 触发 API → 降级
        # 第二次查询 (ignore_ttl) 返回过期数据
        repo.query.side_effect = [None, stale_data]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            fetcher.fetch_hourly(29.75, 102.35, days=1)

            degraded = [x for x in w if issubclass(x.category, DataDegradedWarning)]
            assert len(degraded) == 1
            assert "降级数据" in str(degraded[0].message)


# ─── 重试机制测试 ───────────────────────────────────────────────────


class TestRetryMechanism:
    """重试机制测试"""

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_retry_on_timeout(self, mock_get):
        """超时后重试直到成功"""
        success_resp = _make_mock_response("weather_data_clear.json")
        mock_get.side_effect = [
            httpx.TimeoutException("timeout 1"),
            success_resp,
        ]

        fetcher = MeteoFetcher(
            timeout_config={"connect_timeout": 1, "read_timeout": 1, "retries": 2, "retry_delay": 0},
        )

        df = fetcher.fetch_hourly(29.75, 102.35, days=1)
        assert len(df) == 24
        assert mock_get.call_count == 2

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_retry_exhausted(self, mock_get):
        """重试次数用完后抛出异常"""
        mock_get.side_effect = httpx.TimeoutException("always timeout")

        fetcher = MeteoFetcher(
            cache=None,
            timeout_config={"connect_timeout": 1, "read_timeout": 1, "retries": 1, "retry_delay": 0},
        )

        with pytest.raises(ServiceUnavailableError):
            fetcher.fetch_hourly(29.75, 102.35, days=1)

        # retries=1 → 初始 1 次 + 重试 1 次 = 2 次
        assert mock_get.call_count == 2


# ─── 批量去重测试 ───────────────────────────────────────────────────


class TestMultiPoints:
    """批量多坐标获取测试"""

    @patch("gmp.fetcher.meteo_fetcher.httpx.get")
    def test_multi_points_dedup(self, mock_get):
        """相近坐标去重后只调用一次 API"""
        mock_get.return_value = _make_mock_response("weather_data_clear.json")

        fetcher = MeteoFetcher(
            timeout_config={"connect_timeout": 1, "read_timeout": 1, "retries": 0, "retry_delay": 0},
        )

        coords = [
            (29.7512, 102.3489),
            (29.7523, 102.3451),  # round 后与第一个相同
            (30.5, 103.0),
        ]
        results = fetcher.fetch_multi_points(coords, days=1)

        assert len(results) == 2  # 去重后 2 个唯一坐标
        assert mock_get.call_count == 2
