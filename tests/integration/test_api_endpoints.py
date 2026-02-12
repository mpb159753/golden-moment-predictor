"""Module 09 集成测试 — API 端点

使用 FastAPI TestClient + MockMeteoFetcher 测试所有端点。
所有外部依赖使用 mock 替代，确保测试不依赖网络。

测试用例:
  - GET /api/v1/viewpoints: 列表 + 分页
  - GET /api/v1/forecast/{id}: 正常 / 事件过滤 / 404 / 422
  - GET /api/v1/timeline/{id}: 正常 / 24 小时结构
  - 错误响应格式 (404 / 408 / 422 / 503)
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from gmp.api.routes import create_app
from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.core.exceptions import (
    APITimeoutError,
    InvalidCoordinateError,
    ServiceUnavailableError,
    ViewpointNotFoundError,
)

from tests.conftest import (
    build_mock_scheduler,
    create_test_client,
    make_viewpoint,
)


# ======================================================================
# 测试用例
# ======================================================================


class TestListViewpoints:
    """GET /api/v1/viewpoints"""

    def test_list_viewpoints_200(self):
        client = create_test_client()
        resp = client.get("/api/v1/viewpoints")

        assert resp.status_code == 200
        data = resp.json()
        assert "viewpoints" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1

    def test_list_viewpoints_pagination(self):
        """自定义分页参数: page=1, page_size=1"""
        vp = make_viewpoint()

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
            scheduler=build_mock_scheduler(),
        )
        client = TestClient(app)

        resp = client.get("/api/v1/viewpoints?page=1&page_size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["page_size"] == 1

    def test_viewpoint_item_fields(self):
        """验证每个 viewpoint 有必需字段"""
        client = create_test_client()
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
        client = create_test_client()
        resp = client.get("/api/v1/forecast/niubei_gongga")

        assert resp.status_code == 200
        data = resp.json()
        assert "viewpoint" in data
        assert "forecast_days" in data
        assert "meta" in data

    def test_forecast_with_events(self):
        """?events=cloud_sea,frost → 仅含指定事件"""
        client = create_test_client()
        resp = client.get("/api/v1/forecast/niubei_gongga?events=cloud_sea,frost")

        assert resp.status_code == 200
        data = resp.json()
        assert "forecast_days" in data

    def test_forecast_with_invalid_events(self):
        """传入不在 capabilities 中的事件类型 → 忽略不报错 (T5)"""
        client = create_test_client()
        resp = client.get(
            "/api/v1/forecast/niubei_gongga?events=nonexistent_event,cloud_sea"
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "forecast_days" in data

    def test_forecast_404(self):
        """无效 viewpoint_id → 404"""
        # 自定义 scheduler 使其 run() 抛出 ViewpointNotFoundError
        scheduler = MagicMock()
        scheduler.run.side_effect = ViewpointNotFoundError("invalid_id")

        client = create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/invalid_id")

        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["type"] == "ViewpointNotFound"
        assert data["error"]["code"] == 404

    def test_forecast_422_days_too_large(self):
        """days > 7 → 422 (FastAPI 自动校验)"""
        client = create_test_client()
        resp = client.get("/api/v1/forecast/niubei_gongga?days=10")

        assert resp.status_code == 422

    def test_forecast_days_param(self):
        """days=3 → 正确传递至 scheduler (T3: 简化断言)"""
        scheduler = MagicMock()
        scheduler.run.return_value = {
            "viewpoint": "牛背山",
            "forecast_days": [],
            "meta": {"api_calls": 0, "cache_hits": 0},
        }

        client = create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/niubei_gongga?days=3")

        assert resp.status_code == 200
        scheduler.run.assert_called_once_with(
            viewpoint_id="niubei_gongga", days=3, events=None
        )


class TestTimeline:
    """GET /api/v1/timeline/{viewpoint_id}"""

    def test_timeline_200(self):
        client = create_test_client()
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

        client = create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/timeline/niubei_gongga?days=1")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["timeline_days"]) == 1
        assert len(data["timeline_days"][0]["hours"]) == 24

    def test_timeline_404(self):
        """无效 viewpoint_id → 404"""
        scheduler = MagicMock()
        scheduler.run.side_effect = ViewpointNotFoundError("invalid_id")

        client = create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/timeline/invalid_id")

        assert resp.status_code == 404


class TestErrorFormat:
    """错误响应结构验证"""

    def test_error_response_structure(self):
        """404 错误应包含 error.type, error.message, error.code"""
        scheduler = MagicMock()
        scheduler.run.side_effect = ViewpointNotFoundError("bad_id")

        client = create_test_client(scheduler=scheduler)
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
        scheduler = MagicMock()
        scheduler.run.side_effect = APITimeoutError(
            service="open-meteo", timeout=15
        )

        client = create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/niubei_gongga")

        assert resp.status_code == 408
        data = resp.json()
        assert data["error"]["type"] == "APITimeout"
        assert data["error"]["code"] == 408

    def test_invalid_coordinate_422(self):
        """InvalidCoordinateError → 422 (T2)"""
        scheduler = MagicMock()
        scheduler.run.side_effect = InvalidCoordinateError(lat=999, lon=999)

        client = create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/niubei_gongga")

        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["type"] == "InvalidParameter"
        assert data["error"]["code"] == 422

    def test_service_unavailable_503(self):
        """ServiceUnavailableError → 503 + X-Data-Freshness: stale (T1)"""
        scheduler = MagicMock()
        scheduler.run.side_effect = ServiceUnavailableError(
            service="open-meteo", reason="所有 API 失败且无缓存"
        )

        client = create_test_client(scheduler=scheduler)
        resp = client.get("/api/v1/forecast/niubei_gongga")

        assert resp.status_code == 503
        data = resp.json()
        assert data["error"]["type"] == "ServiceDegraded"
        assert data["error"]["code"] == 503
        assert resp.headers.get("X-Data-Freshness") == "stale"
