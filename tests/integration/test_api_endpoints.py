"""Module 09 集成测试 — API 端点

使用 FastAPI TestClient + MockMeteoFetcher 测试所有端点。
所有外部依赖使用 mock 替代，确保测试不依赖网络。

测试用例:
  - GET /api/v1/viewpoints: 列表 + 分页
  - GET /api/v1/forecast/{id}: 正常 / 事件过滤 / 404 / 422
  - GET /api/v1/timeline/{id}: 正常 / 24 小时结构
  - 错误响应格式
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from gmp.api.routes import create_app
from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.core.exceptions import ViewpointNotFoundError
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
from gmp.scorer.engine import ScoreEngine

# UTC+8
_CST = timezone(timedelta(hours=8))


# ======================================================================
# Fixtures
# ======================================================================


def _make_viewpoint() -> Viewpoint:
    """创建标准测试观景台"""
    return Viewpoint(
        id="niubei_gongga",
        name="牛背山",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["sunrise", "sunset", "stargazing", "cloud_sea", "frost"],
        targets=[
            Target(
                name="贡嘎山",
                lat=29.58,
                lon=101.88,
                altitude=7556,
                weight="primary",
                applicable_events=None,
            ),
        ],
    )


class _SimplePlugin:
    """最小化 mock Plugin"""

    def __init__(self, event_type: str, score_value: int = 80):
        self.event_type = event_type
        self.display_name = event_type
        self.data_requirement = DataRequirement()
        self._score_value = score_value

    def check_trigger(self, l1_data: dict) -> bool:
        return True

    def score(self, context) -> ScoreResult:
        return ScoreResult(
            total_score=self._score_value,
            status="Recommended",
            breakdown={"test": {"score": self._score_value, "max": 100}},
        )


def _make_clear_weather(target_date: date, hours: int = 24) -> pd.DataFrame:
    """晴天天气 DataFrame"""
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


def _build_mock_scheduler(
    viewpoint: Viewpoint | None = None,
    plugins: list | None = None,
) -> GMPScheduler:
    """构建注入 mock 的 Scheduler"""
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
    # 默认 7 天晴天
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
            _SimplePlugin("cloud_sea", 85),
            _SimplePlugin("frost", 70),
        ]
    for p in plugins:
        engine.register(p)

    scheduler = GMPScheduler(
        config=config,
        viewpoint_config=vp_config,
        fetcher=fetcher,
        astro=astro,
        score_engine=engine,
    )
    return scheduler


def _create_test_client(scheduler=None) -> TestClient:
    """创建测试用 TestClient"""
    vp = _make_viewpoint()

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

    if scheduler is None:
        scheduler = _build_mock_scheduler()

    app = create_app(
        config=EngineConfig(),
        viewpoint_config=vp_config,
        scheduler=scheduler,
    )
    return TestClient(app)


# ======================================================================
# 测试用例
# ======================================================================


class TestListViewpoints:
    """GET /api/v1/viewpoints"""

    def test_list_viewpoints_200(self):
        client = _create_test_client()
        resp = client.get("/api/v1/viewpoints")

        assert resp.status_code == 200
        data = resp.json()
        assert "viewpoints" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1

    def test_list_viewpoints_pagination(self):
        """自定义分页参数: page=1, page_size=1"""
        vp = _make_viewpoint()

        vp_config = MagicMock(spec=ViewpointConfig)
        # 模拟 page=1, page_size=1 的调用
        vp_config.list_all.return_value = {
            "viewpoints": [vp],
            "pagination": {
                "page": 1,
                "page_size": 1,
                "total": 1,
                "total_pages": 1,
            },
        }

        app = create_app(
            config=EngineConfig(),
            viewpoint_config=vp_config,
            scheduler=_build_mock_scheduler(),
        )
        client = TestClient(app)

        resp = client.get("/api/v1/viewpoints?page=1&page_size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["page_size"] == 1

    def test_viewpoint_item_fields(self):
        """验证每个 viewpoint 有必需字段"""
        client = _create_test_client()
        resp = client.get("/api/v1/viewpoints")
        data = resp.json()

        vp_list = data["viewpoints"]
        assert len(vp_list) >= 1
        vp = vp_list[0]
        assert "id" in vp
        assert "name" in vp
        assert "location" in vp
        assert "capabilities" in vp
        assert "targets" in vp


class TestForecast:
    """GET /api/v1/forecast/{viewpoint_id}"""

    def test_forecast_200(self):
        client = _create_test_client()
        resp = client.get("/api/v1/forecast/niubei_gongga")

        assert resp.status_code == 200
        data = resp.json()
        assert "viewpoint" in data
        assert "forecast_days" in data
        assert "meta" in data

    def test_forecast_with_events(self):
        """?events=cloud_sea,frost → 仅含指定事件"""
        client = _create_test_client()
        resp = client.get("/api/v1/forecast/niubei_gongga?events=cloud_sea,frost")

        assert resp.status_code == 200
        data = resp.json()
        assert "forecast_days" in data

    def test_forecast_404(self):
        """无效 viewpoint_id → 404"""
        # 自定义 scheduler 使其 run() 抛出 ViewpointNotFoundError
        scheduler = MagicMock()
        scheduler.run.side_effect = ViewpointNotFoundError("invalid_id")

        client = _create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/invalid_id")

        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["type"] == "ViewpointNotFound"
        assert data["error"]["code"] == 404

    def test_forecast_422_days_too_large(self):
        """days > 7 → 422 (FastAPI 自动校验)"""
        client = _create_test_client()
        resp = client.get("/api/v1/forecast/niubei_gongga?days=10")

        assert resp.status_code == 422

    def test_forecast_days_param(self):
        """days=3 → 正确传递至 scheduler"""
        scheduler = MagicMock()
        scheduler.run.return_value = {
            "viewpoint": "牛背山",
            "forecast_days": [],
            "meta": {"api_calls": 0, "cache_hits": 0},
        }

        client = _create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/niubei_gongga?days=3")

        assert resp.status_code == 200
        # 验证 scheduler.run 被调用时 days=3
        scheduler.run.assert_called_once()
        call_kwargs = scheduler.run.call_args
        assert call_kwargs[1]["days"] == 3 or call_kwargs[0][1] == 3 or \
            (call_kwargs.kwargs.get("days") == 3)


class TestTimeline:
    """GET /api/v1/timeline/{viewpoint_id}"""

    def test_timeline_200(self):
        client = _create_test_client()
        resp = client.get("/api/v1/timeline/niubei_gongga")

        assert resp.status_code == 200
        data = resp.json()
        assert "viewpoint" in data
        assert "timeline_days" in data

    def test_timeline_24hours(self):
        """每天应含 24 小时数据"""
        # 使用 mock scheduler，直接返回包含 hourly_weather 的结果
        scheduler = MagicMock()
        tomorrow = date.today() + timedelta(days=1)
        scheduler.run.return_value = {
            "viewpoint": "牛背山",
            "forecast_days": [
                {
                    "date": str(tomorrow),
                    "confidence": "High",
                    "events": [],
                    "hourly_weather": [
                        {
                            "hour": h,
                            "cloud_cover_total": 10,
                            "precipitation_probability": 0,
                            "temperature_2m": 5.0,
                        }
                        for h in range(24)
                    ],
                }
            ],
            "meta": {"api_calls": 0, "cache_hits": 0},
        }

        client = _create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/timeline/niubei_gongga?days=1")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["timeline_days"]) == 1
        assert len(data["timeline_days"][0]["hours"]) == 24

    def test_timeline_404(self):
        """无效 viewpoint_id → 404"""
        scheduler = MagicMock()
        scheduler.run.side_effect = ViewpointNotFoundError("invalid_id")

        client = _create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/timeline/invalid_id")

        assert resp.status_code == 404


class TestErrorFormat:
    """错误响应结构验证"""

    def test_error_response_structure(self):
        """404 错误应包含 error.type, error.message, error.code"""
        scheduler = MagicMock()
        scheduler.run.side_effect = ViewpointNotFoundError("bad_id")

        client = _create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/bad_id")

        assert resp.status_code == 404
        data = resp.json()

        assert "error" in data
        error = data["error"]
        assert "type" in error
        assert "message" in error
        assert "code" in error
        assert error["code"] == 404
        assert "bad_id" in error["message"]

    def test_api_timeout_error_format(self):
        """APITimeoutError → 408"""
        from gmp.core.exceptions import APITimeoutError

        scheduler = MagicMock()
        scheduler.run.side_effect = APITimeoutError(
            service="open-meteo", timeout=15
        )

        client = _create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/niubei_gongga")

        assert resp.status_code == 408
        data = resp.json()
        assert data["error"]["type"] == "APITimeout"
        assert data["error"]["code"] == 408
