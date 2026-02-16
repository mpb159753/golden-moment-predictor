"""tests/backtest/test_backtester.py — Backtester 单元测试"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from gmp.backtest.backtester import Backtester
from gmp.core.exceptions import InvalidDateError
from gmp.core.models import (
    ForecastDay,
    Location,
    PipelineResult,
    ScoreResult,
    Target,
    Viewpoint,
)

_CST = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════
# Test Helpers
# ══════════════════════════════════════════════════════


def _make_viewpoint(
    vp_id: str = "niubei_gongga",
    *,
    lat: float = 29.83,
    lon: float = 102.35,
) -> Viewpoint:
    return Viewpoint(
        id=vp_id,
        name="牛背山_贡嘎",
        location=Location(lat=lat, lon=lon, altitude=3600),
        capabilities=["sunrise", "sunset", "cloud_sea"],
        targets=[
            Target(
                name="贡嘎山",
                lat=29.60,
                lon=101.88,
                altitude=7556,
                weight="primary",
                applicable_events=None,
            ),
        ],
    )


def _make_weather_df(target_date: date) -> pd.DataFrame:
    """生成一天24小时的模拟天气 DataFrame"""
    hours = list(range(24))
    return pd.DataFrame(
        {
            "forecast_date": [target_date] * 24,
            "forecast_hour": hours,
            "temperature_2m": [5.0] * 24,
            "relative_humidity_2m": [80.0] * 24,
            "cloud_cover_total": [30.0] * 24,
            "cloud_cover_low": [20.0] * 24,
            "cloud_cover_medium": [10.0] * 24,
            "cloud_cover_high": [5.0] * 24,
            "cloud_base_altitude": [3000] * 24,
            "precipitation_probability": [10] * 24,
            "visibility": [20000] * 24,
            "wind_speed_10m": [8.0] * 24,
            "snowfall": [0.0] * 24,
            "rain": [0.0] * 24,
            "showers": [0.0] * 24,
            "weather_code": [1] * 24,
        }
    )


def _make_pipeline_result(
    viewpoint: Viewpoint, target_date: date
) -> PipelineResult:
    """构建模拟 PipelineResult"""
    return PipelineResult(
        viewpoint=viewpoint,
        forecast_days=[
            ForecastDay(
                date=target_date.isoformat(),
                summary="晴朗，适合观赏",
                best_event=ScoreResult(
                    event_type="cloud_sea",
                    total_score=85,
                    status="Recommended",
                    breakdown={"humidity": {"score": 40, "max": 50}},
                    confidence="High",
                ),
                events=[
                    ScoreResult(
                        event_type="cloud_sea",
                        total_score=85,
                        status="Recommended",
                        breakdown={"humidity": {"score": 40, "max": 50}},
                        confidence="High",
                    ),
                ],
                confidence="High",
            )
        ],
        meta={
            "generated_at": datetime.now(_CST).isoformat(),
            "data_freshness": "archive",
            "mode": "backtest",
        },
    )


def _make_cache_rows(target_date: date, fetched_at: str) -> list[dict]:
    """模拟 CacheRepository.query_weather 返回的行"""
    rows = []
    for h in range(24):
        rows.append(
            {
                "lat_rounded": 29.83,
                "lon_rounded": 102.35,
                "forecast_date": target_date.isoformat(),
                "forecast_hour": h,
                "fetched_at": fetched_at,
                "api_source": "forecast",
                "temperature_2m": 5.0,
                "relative_humidity_2m": 80.0,
                "cloud_cover_total": 30.0,
                "cloud_cover_low": 20.0,
                "cloud_cover_medium": 10.0,
                "cloud_cover_high": 5.0,
                "cloud_base_altitude": 3000,
                "precipitation_probability": 10,
                "visibility": 20000,
                "wind_speed_10m": 8.0,
                "snowfall": 0.0,
                "rain": 0.0,
                "showers": 0.0,
                "weather_code": 1,
            }
        )
    return rows


def _build_backtester(
    *,
    max_history_days: int = 365,
    viewpoint: Viewpoint | None = None,
) -> tuple[Backtester, MagicMock, MagicMock, MagicMock, MagicMock]:
    """构建 Backtester 及其 mock 依赖，返回 (backtester, scheduler, fetcher, config, cache_repo)"""
    scheduler = MagicMock()
    fetcher = MagicMock()
    config = MagicMock()
    cache_repo = MagicMock()
    viewpoint_config = MagicMock()

    # 配置 config.config.backtest_max_history_days
    config.config.backtest_max_history_days = max_history_days

    # 配置 viewpoint_config 以便 backtester 获取 viewpoint 信息
    vp = viewpoint or _make_viewpoint()
    viewpoint_config.get.return_value = vp

    bt = Backtester(
        scheduler=scheduler,
        fetcher=fetcher,
        config=config,
        cache_repo=cache_repo,
        viewpoint_config=viewpoint_config,
    )

    return bt, scheduler, fetcher, config, cache_repo


# ══════════════════════════════════════════════════════
# Date Validation Tests
# ══════════════════════════════════════════════════════


class TestDateValidation:
    """日期验证测试"""

    def test_past_valid_date_runs_normally(self):
        """过去的有效日期 → 正常执行"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result is not None
        assert result["is_backtest"] is True

    def test_future_date_raises_invalid_date_error(self):
        """未来日期 → InvalidDateError("FutureDate")"""
        bt, *_ = _build_backtester()
        future_date = date.today() + timedelta(days=1)

        with pytest.raises(InvalidDateError, match="FutureDate"):
            bt.run("niubei_gongga", future_date)

    def test_today_raises_invalid_date_error(self):
        """今天的日期 → InvalidDateError("FutureDate") (必须 < today)"""
        bt, *_ = _build_backtester()

        with pytest.raises(InvalidDateError, match="FutureDate"):
            bt.run("niubei_gongga", date.today())

    def test_too_old_date_raises_invalid_date_error(self):
        """超过 max_history_days → InvalidDateError("DateTooOld")"""
        bt, *_ = _build_backtester(max_history_days=365)
        old_date = date.today() - timedelta(days=400)

        with pytest.raises(InvalidDateError, match="DateTooOld"):
            bt.run("niubei_gongga", old_date)


# ══════════════════════════════════════════════════════
# Cache-First Strategy Tests
# ══════════════════════════════════════════════════════


class TestCacheFirstStrategy:
    """缓存优先策略测试"""

    def test_cache_hit_uses_cached_data(self):
        """DB 中有目标日的缓存 → 使用缓存数据, data_source="cache" """
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        # 模拟缓存命中
        cache_rows = _make_cache_rows(
            target_date, "2025-12-01T10:00:00"
        )
        cache_repo.query_weather.return_value = cache_rows
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result["data_source"] == "cache"
        # 不应调用 fetch_historical
        fetcher.fetch_historical.assert_not_called()

    def test_multiple_fetches_uses_latest(self):
        """DB 中有多次获取 (D-1 和 D-5) → 使用最新 fetched_at 的数据"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        # 模拟有多次获取的缓存行，包含不同 fetched_at
        older_rows = _make_cache_rows(target_date, "2025-11-26T10:00:00")
        newer_rows = _make_cache_rows(target_date, "2025-11-30T10:00:00")
        # 返回混合数据 — backtester 应取 fetched_at 最新的
        cache_repo.query_weather.return_value = older_rows + newer_rows
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result["data_source"] == "cache"
        assert result["data_fetched_at"] == "2025-11-30T10:00:00"

    def test_no_cache_calls_fetch_historical(self):
        """DB 中无缓存 → 调用 fetch_historical, data_source="archive" """
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result["data_source"] == "archive"
        fetcher.fetch_historical.assert_called()

    def test_partial_cache_calls_api_for_missing(self):
        """部分坐标有缓存, 部分无 → 缺失部分调 API, data_source="archive" """
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        # 本地坐标有缓存，目标坐标无缓存
        def query_side_effect(lat, lon, td, hours=None):
            if round(lat, 2) == 29.83 and round(lon, 2) == 102.35:
                return _make_cache_rows(td, "2025-11-30T10:00:00")
            return None  # 目标坐标无缓存

        cache_repo.query_weather.side_effect = query_side_effect
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result["data_source"] == "archive"


# ══════════════════════════════════════════════════════
# Save Tests
# ══════════════════════════════════════════════════════


class TestSaveFunction:
    """保存功能测试"""

    def test_save_true_calls_save_prediction(self):
        """save=True → save_prediction 被调用"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        bt.run("niubei_gongga", target_date, save=True)
        cache_repo.save_prediction.assert_called()

    def test_save_true_record_has_backtest_flag(self):
        """save=True → 保存记录中 is_backtest=True"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        bt.run("niubei_gongga", target_date, save=True)

        # 检查 save_prediction 调用的参数
        call_args = cache_repo.save_prediction.call_args
        record = call_args[0][0] if call_args[0] else call_args[1].get("record")
        assert record["is_backtest"] is True

    def test_save_true_record_has_correct_data_source(self):
        """save=True → 保存记录中 data_source 正确"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        bt.run("niubei_gongga", target_date, save=True)

        call_args = cache_repo.save_prediction.call_args
        record = call_args[0][0] if call_args[0] else call_args[1].get("record")
        assert record["data_source"] == "archive"

    def test_save_false_does_not_call_save_prediction(self):
        """save=False → save_prediction 未被调用"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        bt.run("niubei_gongga", target_date, save=False)
        cache_repo.save_prediction.assert_not_called()


# ══════════════════════════════════════════════════════
# Report Format Tests
# ══════════════════════════════════════════════════════


class TestReportFormat:
    """报告格式测试"""

    def test_report_has_required_fields(self):
        """报告包含所有必要字段"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert "viewpoint_id" in result
        assert "target_date" in result
        assert "is_backtest" in result
        assert "data_source" in result
        assert "events" in result
        assert "meta" in result

    def test_report_data_source_reflects_cache(self):
        """data_source 字段在缓存来源时为 "cache" """
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = _make_cache_rows(
            target_date, "2025-12-01T10:00:00"
        )
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result["data_source"] == "cache"

    def test_report_data_fetched_at_present_for_cache(self):
        """data_fetched_at 在缓存来源时有值"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = _make_cache_rows(
            target_date, "2025-12-01T10:00:00"
        )
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result["data_fetched_at"] == "2025-12-01T10:00:00"

    def test_report_data_fetched_at_none_for_archive(self):
        """data_fetched_at 在 archive 来源时为 None"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert result.get("data_fetched_at") is None

    def test_report_events_format_matches_forecast(self):
        """events 格式与 forecast 一致"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        pipeline_result = _make_pipeline_result(vp, target_date)
        scheduler.run_with_data.return_value = pipeline_result

        result = bt.run("niubei_gongga", target_date)
        # events 应该是列表
        assert isinstance(result["events"], list)
        # 至少包含一个事件
        assert len(result["events"]) > 0
        # 每个事件应有 event_type 和 total_score
        for event in result["events"]:
            assert "event_type" in event
            assert "total_score" in event

    def test_report_meta_contains_backtest_run_at(self):
        """meta 中包含 backtest_run_at"""
        bt, scheduler, fetcher, config, cache_repo = _build_backtester()
        target_date = date.today() - timedelta(days=7)
        vp = _make_viewpoint()

        cache_repo.query_weather.return_value = None
        fetcher.fetch_historical.return_value = _make_weather_df(target_date)
        scheduler.run_with_data.return_value = _make_pipeline_result(
            vp, target_date
        )

        result = bt.run("niubei_gongga", target_date)
        assert "backtest_run_at" in result["meta"]
