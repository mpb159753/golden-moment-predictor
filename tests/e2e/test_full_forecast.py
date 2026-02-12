"""E2E 测试 — 完整预测流程

使用 MockMeteoFetcher 替代真实 API 调用，
验证从 Scheduler → Reporter → API 的完整管线。

测试用例:
  - 完整 7 天预测流程
  - CLI 模式输出
  - forecast 和 timeline 一致性
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from gmp.api.routes import create_app
from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.reporter.cli_formatter import CLIFormatter
from gmp.reporter.forecast_reporter import ForecastReporter
from gmp.reporter.timeline_reporter import TimelineReporter

from tests.conftest import (
    build_mock_scheduler,
    make_viewpoint,
)


# ======================================================================
# E2E 测试用例
# ======================================================================


class TestFullForecast:
    """完整 7 天预测 E2E 流程"""

    def test_full_7day_forecast(self):
        """Scheduler → ForecastReporter → JSON 输出完整性"""
        scheduler = build_mock_scheduler()
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
        scheduler = build_mock_scheduler()
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
        scheduler = build_mock_scheduler()
        result = scheduler.run("niubei_gongga", days=3)

        formatter = CLIFormatter(color_enabled=False)
        output = formatter.generate(result)

        assert len(output) > 0
        assert "牛背山" in output

    def test_cli_no_color_output(self):
        """--no-color 模式无 ANSI 转义码"""
        scheduler = build_mock_scheduler()
        result = scheduler.run("niubei_gongga", days=1)

        formatter = CLIFormatter(color_enabled=False)
        output = formatter.generate(result)

        # 不应包含 ANSI 转义码
        assert "\033[" not in output

    def test_cli_color_output(self):
        """颜色模式应包含 ANSI 转义码"""
        scheduler = build_mock_scheduler()
        result = scheduler.run("niubei_gongga", days=1)

        formatter = CLIFormatter(color_enabled=True)
        output = formatter.generate(result)

        # 应包含 ANSI 转义码
        assert "\033[" in output


class TestForecastTimelineConsistency:
    """forecast 和 timeline 使用同一 DataContext"""

    def test_forecast_timeline_consistency(self):
        """同一 Scheduler 产出 → 两个 Reporter 输出天数一致"""
        scheduler = build_mock_scheduler()
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
        scheduler = build_mock_scheduler()
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
        scheduler = build_mock_scheduler()
        vp = make_viewpoint()

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
