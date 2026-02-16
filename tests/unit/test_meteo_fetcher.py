"""tests/unit/test_meteo_fetcher.py — MeteoFetcher 单元测试

覆盖：解析、校验、缓存集成、错误处理、past_days、历史数据、多点批量。
"""

from __future__ import annotations

import warnings
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from gmp.core.exceptions import APITimeoutError, DataDegradedWarning
from gmp.data.meteo_fetcher import MeteoFetcher

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_API_RESPONSE: dict = {
    "hourly": {
        "time": [
            "2025-12-01T00:00",
            "2025-12-01T01:00",
            "2025-12-01T02:00",
        ],
        "temperature_2m": [5.0, 4.5, 4.0],
        "cloud_cover": [10, 20, 30],
        "cloud_cover_low": [5, 10, 15],
        "cloud_cover_mid": [3, 8, 12],
        "cloud_cover_high": [2, 5, 10],
        "cloud_base": [3000.0, 2800.0, 2500.0],
        "precipitation_probability": [0, 5, 10],
        "visibility": [20000.0, 18000.0, 15000.0],
        "wind_speed_10m": [3.0, 4.0, 5.0],
        "snowfall": [0.0, 0.0, 0.0],
        "rain": [0.0, 0.0, 0.0],
        "showers": [0.0, 0.0, 0.0],
        "weather_code": [0, 1, 2],
    }
}


def _make_fetcher(cache: MagicMock | None = None, config: dict | None = None) -> MeteoFetcher:
    """创建 MeteoFetcher 实例，默认用 mock cache"""
    if cache is None:
        cache = MagicMock()
        cache.get.return_value = None  # 默认缓存未命中
    return MeteoFetcher(cache=cache, config=config)


# ========================================================================
# 1. 解析测试 — _parse_response
# ========================================================================


class TestParseResponse:
    """_parse_response 解析 Open-Meteo JSON → DataFrame"""

    def test_parse_returns_dataframe_with_correct_columns(self) -> None:
        """解析后 DataFrame 包含所有预期列"""
        fetcher = _make_fetcher()
        df = fetcher._parse_response(SAMPLE_API_RESPONSE)

        expected_columns = [
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
        assert list(df.columns) == expected_columns

    def test_parse_column_name_mapping(self) -> None:
        """Open-Meteo 字段名正确映射：cloud_cover→cloud_cover_total, cloud_cover_mid→cloud_cover_medium, cloud_base→cloud_base_altitude"""
        fetcher = _make_fetcher()
        df = fetcher._parse_response(SAMPLE_API_RESPONSE)

        # cloudbase → cloud_base_altitude
        assert df["cloud_base_altitude"].iloc[0] == 3000.0
        # cloud_cover → cloud_cover_total
        assert df["cloud_cover_total"].iloc[0] == 10
        # cloud_cover_mid → cloud_cover_medium
        assert df["cloud_cover_medium"].iloc[0] == 3

    def test_parse_date_hour_extraction(self) -> None:
        """从时间戳正确提取 date 和 hour"""
        fetcher = _make_fetcher()
        df = fetcher._parse_response(SAMPLE_API_RESPONSE)

        assert df["forecast_date"].iloc[0] == "2025-12-01"
        assert df["forecast_hour"].iloc[0] == 0
        assert df["forecast_hour"].iloc[1] == 1
        assert df["forecast_hour"].iloc[2] == 2

    def test_parse_row_count_matches_input(self) -> None:
        """行数与输入数据匹配"""
        fetcher = _make_fetcher()
        df = fetcher._parse_response(SAMPLE_API_RESPONSE)
        assert len(df) == 3


# ========================================================================
# 2. 校验测试 — _validate_data
# ========================================================================


class TestValidateData:
    """_validate_data 数据校验"""

    def test_cloud_base_altitude_none_replaced(self) -> None:
        """cloud_base_altitude=None → 替换为 10000"""
        fetcher = _make_fetcher()
        df = pd.DataFrame(
            {
                "forecast_date": [date(2025, 12, 1)],
                "forecast_hour": [0],
                "temperature_2m": [5.0],
                "cloud_cover_total": [10],
                "cloud_cover_low": [5],
                "cloud_cover_medium": [3],
                "cloud_cover_high": [2],
                "cloud_base_altitude": [None],
                "precipitation_probability": [0],
                "visibility": [20000.0],
                "wind_speed_10m": [3.0],
                "snowfall": [0.0],
                "rain": [0.0],
                "showers": [0.0],
                "weather_code": [0],
            }
        )
        result = fetcher._validate_data(df)
        assert result["cloud_base_altitude"].iloc[0] == 10000

    def test_visibility_none_replaced(self) -> None:
        """visibility=None → 替换为 0"""
        fetcher = _make_fetcher()
        df = pd.DataFrame(
            {
                "forecast_date": [date(2025, 12, 1)],
                "forecast_hour": [0],
                "temperature_2m": [5.0],
                "cloud_cover_total": [10],
                "cloud_cover_low": [5],
                "cloud_cover_medium": [3],
                "cloud_cover_high": [2],
                "cloud_base_altitude": [3000.0],
                "precipitation_probability": [0],
                "visibility": [None],
                "wind_speed_10m": [3.0],
                "snowfall": [0.0],
                "rain": [0.0],
                "showers": [0.0],
                "weather_code": [0],
            }
        )
        result = fetcher._validate_data(df)
        assert result["visibility"].iloc[0] == 0

    def test_precipitation_probability_clipped(self) -> None:
        """precipitation_probability=110 → clip 到 100"""
        fetcher = _make_fetcher()
        df = pd.DataFrame(
            {
                "forecast_date": [date(2025, 12, 1)],
                "forecast_hour": [0],
                "temperature_2m": [5.0],
                "cloud_cover_total": [10],
                "cloud_cover_low": [5],
                "cloud_cover_medium": [3],
                "cloud_cover_high": [2],
                "cloud_base_altitude": [3000.0],
                "precipitation_probability": [110],
                "visibility": [20000.0],
                "wind_speed_10m": [3.0],
                "snowfall": [0.0],
                "rain": [0.0],
                "showers": [0.0],
                "weather_code": [0],
            }
        )
        result = fetcher._validate_data(df)
        assert result["precipitation_probability"].iloc[0] == 100

    def test_temperature_degraded_warning(self) -> None:
        """temperature_2m=-70 → 发出 DataDegradedWarning"""
        fetcher = _make_fetcher()
        df = pd.DataFrame(
            {
                "forecast_date": [date(2025, 12, 1)],
                "forecast_hour": [0],
                "temperature_2m": [-70.0],
                "cloud_cover_total": [10],
                "cloud_cover_low": [5],
                "cloud_cover_medium": [3],
                "cloud_cover_high": [2],
                "cloud_base_altitude": [3000.0],
                "precipitation_probability": [0],
                "visibility": [20000.0],
                "wind_speed_10m": [3.0],
                "snowfall": [0.0],
                "rain": [0.0],
                "showers": [0.0],
                "weather_code": [0],
            }
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            fetcher._validate_data(df)
            degraded = [x for x in w if issubclass(x.category, DataDegradedWarning)]
            assert len(degraded) >= 1

    def test_wind_speed_none_replaced(self) -> None:
        """wind_speed_10m=None → 替换为 0"""
        fetcher = _make_fetcher()
        df = pd.DataFrame(
            {
                "forecast_date": [date(2025, 12, 1)],
                "forecast_hour": [0],
                "temperature_2m": [5.0],
                "cloud_cover_total": [10],
                "cloud_cover_low": [5],
                "cloud_cover_medium": [3],
                "cloud_cover_high": [2],
                "cloud_base_altitude": [3000.0],
                "precipitation_probability": [0],
                "visibility": [20000.0],
                "wind_speed_10m": [None],
                "snowfall": [0.0],
                "rain": [0.0],
                "showers": [0.0],
                "weather_code": [0],
            }
        )
        result = fetcher._validate_data(df)
        assert result["wind_speed_10m"].iloc[0] == 0

    def test_cloud_cover_clipped(self) -> None:
        """cloud_cover_total 超出 0-100 → clip"""
        fetcher = _make_fetcher()
        df = pd.DataFrame(
            {
                "forecast_date": [date(2025, 12, 1)],
                "forecast_hour": [0],
                "temperature_2m": [5.0],
                "cloud_cover_total": [120],
                "cloud_cover_low": [5],
                "cloud_cover_medium": [3],
                "cloud_cover_high": [2],
                "cloud_base_altitude": [3000.0],
                "precipitation_probability": [0],
                "visibility": [20000.0],
                "wind_speed_10m": [3.0],
                "snowfall": [0.0],
                "rain": [0.0],
                "showers": [0.0],
                "weather_code": [0],
            }
        )
        result = fetcher._validate_data(df)
        assert result["cloud_cover_total"].iloc[0] == 100


# ========================================================================
# 3. 缓存集成测试
# ========================================================================


class TestCacheIntegration:
    """缓存命中/未命中行为"""

    def test_cache_hit_skips_api_call(self) -> None:
        """缓存命中时不调用 API"""
        cache = MagicMock()
        cached_df = pd.DataFrame(
            {
                "forecast_date": [date(2025, 12, 1)],
                "forecast_hour": [0],
                "temperature_2m": [5.0],
                "cloud_cover_total": [10],
                "cloud_cover_low": [5],
                "cloud_cover_medium": [3],
                "cloud_cover_high": [2],
                "cloud_base_altitude": [3000.0],
                "precipitation_probability": [0],
                "visibility": [20000.0],
                "wind_speed_10m": [3.0],
                "snowfall": [0.0],
                "rain": [0.0],
                "showers": [0.0],
                "weather_code": [0],
            }
        )
        cache.get.return_value = cached_df
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api") as mock_api:
            result = fetcher.fetch_hourly(29.75, 102.35)
            mock_api.assert_not_called()
            assert len(result) == 1

    def test_cache_miss_calls_api_and_writes_cache(self) -> None:
        """缓存未命中时调用 API 并写入缓存"""
        cache = MagicMock()
        cache.get.return_value = None  # miss
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE):
            result = fetcher.fetch_hourly(29.75, 102.35, days=1)
            cache.set.assert_called()
            assert len(result) == 3


# ========================================================================
# 4. 错误处理测试
# ========================================================================


class TestErrorHandling:
    """API 超时、无效响应、重试"""

    def test_api_timeout_raises_api_timeout_error(self) -> None:
        """API 超时 → 抛出 APITimeoutError"""
        import httpx

        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache, config={"retries": 0})

        with patch.object(
            fetcher,
            "_call_api",
            side_effect=APITimeoutError("open-meteo", 15),
        ):
            with pytest.raises(APITimeoutError):
                fetcher.fetch_hourly(29.75, 102.35, days=1)

    def test_api_invalid_format_raises_error(self) -> None:
        """API 返回格式无效 → 合理错误"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api", return_value={"bad": "data"}):
            with pytest.raises((KeyError, ValueError)):
                fetcher.fetch_hourly(29.75, 102.35, days=1)

    def test_retry_succeeds_on_second_attempt(self) -> None:
        """第 1 次超时, 第 2 次成功 → 返回正常数据"""
        import httpx

        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(
            cache=cache,
            config={"retries": 2, "retry_delay": 0, "connect_timeout": 5, "read_timeout": 15},
        )

        call_count = 0

        def _mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("timeout")
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = SAMPLE_API_RESPONSE
            response.raise_for_status = MagicMock()
            return response

        with patch("httpx.get", side_effect=_mock_get):
            result = fetcher.fetch_hourly(29.75, 102.35, days=1)
            assert len(result) == 3
            assert call_count == 2

    def test_retry_exhausted_raises_api_timeout_error(self) -> None:
        """重试次数耗尽 → 抛出 APITimeoutError"""
        import httpx

        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(
            cache=cache,
            config={"retries": 2, "retry_delay": 0, "connect_timeout": 5, "read_timeout": 15},
        )

        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(APITimeoutError):
                fetcher.fetch_hourly(29.75, 102.35, days=1)


# ========================================================================
# 5. past_days 参数测试
# ========================================================================


class TestPastDays:
    """past_days 参数传递"""

    def test_past_days_included_in_api_request(self) -> None:
        """past_days=1 → API 请求包含 past_days=1"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE) as mock_api:
            fetcher.fetch_hourly(29.75, 102.35, days=1, past_days=1)
            call_args = mock_api.call_args
            params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
            assert params.get("past_days") == 1

    def test_past_days_zero_not_included(self) -> None:
        """past_days=0 → API 请求不含 past_days 或为 0"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE) as mock_api:
            fetcher.fetch_hourly(29.75, 102.35, days=1, past_days=0)
            call_args = mock_api.call_args
            params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
            assert params.get("past_days", 0) == 0


# ========================================================================
# 6. fetch_historical 测试
# ========================================================================


class TestFetchHistorical:
    """fetch_historical 使用 Archive API"""

    def test_uses_archive_api_url(self) -> None:
        """使用 Archive API URL"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE) as mock_api:
            fetcher.fetch_historical(29.75, 102.35, date(2025, 12, 1))
            call_args = mock_api.call_args
            url = call_args[0][0]
            assert "archive" in url

    def test_passes_start_and_end_date(self) -> None:
        """正确传入 start_date 和 end_date"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE) as mock_api:
            fetcher.fetch_historical(29.75, 102.35, date(2025, 12, 1))
            call_args = mock_api.call_args
            params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
            assert params["start_date"] == "2025-12-01"
            assert params["end_date"] == "2025-12-01"

    def test_returns_dataframe_with_same_format(self) -> None:
        """返回 DataFrame 格式与 fetch_hourly 一致"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE):
            result = fetcher.fetch_historical(29.75, 102.35, date(2025, 12, 1))
            assert isinstance(result, pd.DataFrame)
            assert "cloud_cover_total" in result.columns
            assert "cloud_base_altitude" in result.columns


# ========================================================================
# 7. fetch_multi_points 测试
# ========================================================================


class TestFetchMultiPoints:
    """fetch_multi_points 批量获取"""

    def test_deduplicates_by_rounded_coords(self) -> None:
        """坐标去重: 3 个坐标, 2 个 ROUND(2) 后相同 → 实际请求 2 个"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        coords = [
            (29.7511, 102.3522),  # rounds to (29.75, 102.35)
            (29.7499, 102.3501),  # rounds to (29.75, 102.35) — 重复
            (30.0000, 103.0000),  # unique
        ]

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE):
            result = fetcher.fetch_multi_points(coords, days=1)
            assert len(result) == 2

    def test_returns_dict_keyed_by_rounded_coords(self) -> None:
        """返回字典 key 为 rounded 坐标"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        coords = [(29.7511, 102.3522)]

        with patch.object(fetcher, "_call_api", return_value=SAMPLE_API_RESPONSE):
            result = fetcher.fetch_multi_points(coords, days=1)
            assert (29.75, 102.35) in result

    def test_empty_coords_returns_empty_dict(self) -> None:
        """空坐标列表 → 返回空字典"""
        cache = MagicMock()
        cache.get.return_value = None
        fetcher = MeteoFetcher(cache=cache)

        result = fetcher.fetch_multi_points([], days=1)
        assert result == {}
