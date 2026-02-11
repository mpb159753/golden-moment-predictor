"""E2E 测试 — 完整预测流程

使用 MockMeteoFetcher 替代真实 API 调用，
验证从 Scheduler → Reporter → API 的完整管线。

测试用例:
  - 完整 7 天预测流程
  - CLI 模式输出
  - forecast 和 timeline 一致性
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from gmp.api.routes import create_app
from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.core.models import (
    DataRequirement,
    Location,
    MoonStatus,
    ScoreResult,
    StargazingWindow,
    SunEvents,
    Target,
    Viewpoint,
)
from gmp.core.scheduler import GMPScheduler
from gmp.reporter.cli_formatter import CLIFormatter
from gmp.reporter.forecast_reporter import ForecastReporter
from gmp.reporter.timeline_reporter import TimelineReporter
from gmp.scorer.engine import ScoreEngine

_CST = timezone(timedelta(hours=8))


# ======================================================================
# Fixtures
# ======================================================================


def _make_viewpoint() -> Viewpoint:
    return Viewpoint(
        id="niubei_gongga",
        name="牛背山",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["cloud_sea", "frost", "snow_tree", "ice_icicle"],
        targets=[
            Target(
                name="贡嘎山", lat=29.58, lon=101.88,
                altitude=7556, weight="primary",
                applicable_events=None,
            ),
        ],
    )


class _SimplePlugin:
    """E2E 用简化 Plugin"""

    def __init__(self, event_type: str, display_name: str = "",
                 score_value: int = 80):
        self.event_type = event_type
        self.display_name = display_name or event_type
        self.data_requirement = DataRequirement()
        self._score_value = score_value

    def check_trigger(self, l1_data: dict) -> bool:
        return True

    def score(self, context) -> ScoreResult:
        return ScoreResult(
            total_score=self._score_value,
            status="Recommended" if self._score_value >= 80 else "Possible",
            breakdown={
                "main": {"score": self._score_value, "max": 100,
                         "detail": "测试维度"},
            },
        )


def _make_clear_weather(target_date: date, hours: int = 24) -> pd.DataFrame:
    rows = []
    for h in range(hours):
        rows.append({
            "forecast_date": str(target_date),
            "forecast_hour": h,
            "temperature_2m": -2.0 + h * 0.5,
            "cloud_cover_total": 8,
            "cloud_cover_low": 60,
            "cloud_cover_mid": 5,
            "cloud_cover_medium": 5,
            "cloud_cover_high": 3,
            "precipitation_probability": 0,
            "visibility": 35000,
            "wind_speed_10m": 5.0,
            "weather_code": 0,
            "snowfall": 0,
            "rain": 0,
            "showers": 0,
        })
    return pd.DataFrame(rows)


def _make_sun_events(target_date: date) -> SunEvents:
    d = target_date
    return SunEvents(
        sunrise=datetime(d.year, d.month, d.day, 7, 15, tzinfo=_CST),
        sunset=datetime(d.year, d.month, d.day, 18, 30, tzinfo=_CST),
        sunrise_azimuth=108.5,
        sunset_azimuth=251.5,
        astronomical_dawn=datetime(d.year, d.month, d.day, 5, 40, tzinfo=_CST),
        astronomical_dusk=datetime(d.year, d.month, d.day, 20, 5, tzinfo=_CST),
    )


def _build_scheduler(
    viewpoint: Viewpoint | None = None,
    plugins: list | None = None,
) -> GMPScheduler:
    """构建完整 mock Scheduler"""
    from gmp.astro.astro_utils import AstroUtils
    from gmp.fetcher.meteo_fetcher import MeteoFetcher

    config = EngineConfig()
    vp = viewpoint or _make_viewpoint()

    vp_config = MagicMock(spec=ViewpointConfig)
    vp_config.get.return_value = vp
    vp_config.list_all.return_value = {
        "viewpoints": [vp],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total": 1,
            "total_pages": 1,
        },
    }

    fetcher = MagicMock(spec=MeteoFetcher)
    frames = []
    for d in range(7):
        target_d = date.today() + timedelta(days=d + 1)
        frames.append(_make_clear_weather(target_d))
    fetcher.fetch_hourly.return_value = pd.concat(frames, ignore_index=True)
    fetcher.fetch_multi_points.return_value = {}

    astro = MagicMock(spec=AstroUtils)
    se = _make_sun_events(date.today() + timedelta(days=1))
    astro.get_sun_events.return_value = se
    astro.get_moon_status.return_value = MoonStatus(phase=15, elevation=-10.0)
    astro.determine_stargazing_window.return_value = StargazingWindow(
        good_start=se.astronomical_dusk,
        good_end=se.astronomical_dawn,
        quality="good",
    )

    engine = ScoreEngine()
    if plugins is None:
        plugins = [
            _SimplePlugin("cloud_sea", "云海", 85),
            _SimplePlugin("frost", "雾凇", 70),
        ]
    for p in plugins:
        engine.register(p)

    return GMPScheduler(
        config=config,
        viewpoint_config=vp_config,
        fetcher=fetcher,
        astro=astro,
        score_engine=engine,
    )


# ======================================================================
# E2E 测试用例
# ======================================================================


class TestFullForecast:
    """完整 7 天预测 E2E 流程"""

    def test_full_7day_forecast(self):
        """Scheduler → ForecastReporter → JSON 输出完整性"""
        scheduler = _build_scheduler()
        result = scheduler.run("niubei_gongga", days=7)

        # Scheduler 输出结构
        assert result["viewpoint"] == "牛背山"
        assert len(result["forecast_days"]) == 7
        assert "meta" in result

        # ForecastReporter 格式化
        reporter = ForecastReporter()
        report = reporter.generate(result)

        assert "report_date" in report
        assert "viewpoint" in report
        assert report["viewpoint"] == "牛背山"
        assert len(report["forecast_days"]) == 7

        for day in report["forecast_days"]:
            assert "date" in day
            assert "confidence" in day
            assert "summary" in day
            assert "events" in day

        assert "meta" in report
        assert "generated_at" in report["meta"]
        assert "cache_stats" in report["meta"]

    def test_full_forecast_events_content(self):
        """验证事件内容结构"""
        scheduler = _build_scheduler()
        result = scheduler.run("niubei_gongga", days=1)

        reporter = ForecastReporter()
        report = reporter.generate(result)

        day = report["forecast_days"][0]
        assert day["confidence"] == "High"

        for event in day["events"]:
            assert "type" in event
            assert "score" in event
            assert "status" in event
            assert "score_breakdown" in event


class TestCLIPredict:
    """CLI 模式输出测试"""

    def test_cli_predict_output(self):
        """CLI 模式输出不为空"""
        scheduler = _build_scheduler()
        result = scheduler.run("niubei_gongga", days=3)

        formatter = CLIFormatter(color_enabled=False)
        output = formatter.generate(result)

        assert len(output) > 0
        assert "牛背山" in output

    def test_cli_no_color_output(self):
        """--no-color 模式无 ANSI 转义码"""
        scheduler = _build_scheduler()
        result = scheduler.run("niubei_gongga", days=1)

        formatter = CLIFormatter(color_enabled=False)
        output = formatter.generate(result)

        # 不应包含 ANSI 转义码
        assert "\033[" not in output

    def test_cli_color_output(self):
        """颜色模式应包含 ANSI 转义码"""
        scheduler = _build_scheduler()
        result = scheduler.run("niubei_gongga", days=1)

        formatter = CLIFormatter(color_enabled=True)
        output = formatter.generate(result)

        # 应包含 ANSI 转义码
        assert "\033[" in output


class TestForecastTimelineConsistency:
    """forecast 和 timeline 使用同一 DataContext"""

    def test_forecast_timeline_consistency(self):
        """同一 Scheduler 产出 → 两个 Reporter 输出天数一致"""
        scheduler = _build_scheduler()
        result = scheduler.run("niubei_gongga", days=7)

        forecast_reporter = ForecastReporter()
        timeline_reporter = TimelineReporter()

        forecast = forecast_reporter.generate(result)
        timeline = timeline_reporter.generate(result)

        # 天数一致
        assert len(forecast["forecast_days"]) == len(timeline["timeline_days"])

        # 日期一致
        for f_day, t_day in zip(
            forecast["forecast_days"], timeline["timeline_days"]
        ):
            assert f_day["date"] == t_day["date"]

    def test_timeline_hours_structure(self):
        """Timeline 每天应有 24 小时"""
        scheduler = _build_scheduler()
        result = scheduler.run("niubei_gongga", days=3)

        reporter = TimelineReporter()
        timeline = reporter.generate(result)

        for day in timeline["timeline_days"]:
            assert len(day["hours"]) == 24
            hours = [h["hour"] for h in day["hours"]]
            assert hours == list(range(24))


class TestAPIE2E:
    """通过 TestClient 进行 E2E API 测试"""

    def test_api_full_forecast_e2e(self):
        """API → Scheduler → Reporter 完整管线"""
        scheduler = _build_scheduler()
        vp = _make_viewpoint()

        vp_config = MagicMock(spec=ViewpointConfig)
        vp_config.get.return_value = vp
        vp_config.list_all.return_value = {
            "viewpoints": [vp],
            "pagination": {"page": 1, "page_size": 20,
                           "total": 1, "total_pages": 1},
        }

        app = create_app(
            config=EngineConfig(),
            viewpoint_config=vp_config,
            scheduler=scheduler,
        )
        client = TestClient(app)

        # 1. 查看观景台列表
        resp = client.get("/api/v1/viewpoints")
        assert resp.status_code == 200
        viewpoints = resp.json()["viewpoints"]
        assert len(viewpoints) >= 1
        vp_id = viewpoints[0]["id"]

        # 2. 获取预测报告
        resp = client.get(f"/api/v1/forecast/{vp_id}?days=3")
        assert resp.status_code == 200
        forecast = resp.json()
        assert forecast["viewpoint"] == "牛背山"
        assert len(forecast["forecast_days"]) > 0

        # 3. 获取时间轴
        resp = client.get(f"/api/v1/timeline/{vp_id}?days=3")
        assert resp.status_code == 200
        timeline = resp.json()
        assert timeline["viewpoint"] == "牛背山"
        assert len(timeline["timeline_days"]) > 0
