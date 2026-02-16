"""tests/unit/test_forecast_reporter.py — ForecastReporter 单元测试"""

from __future__ import annotations

import pytest

from gmp.core.models import (
    ForecastDay,
    Location,
    PipelineResult,
    Route,
    RouteStop,
    ScoreResult,
    Viewpoint,
)
from gmp.output.forecast_reporter import ForecastReporter
from gmp.output.summary_generator import SummaryGenerator


# ── helpers ──


def _make_event(
    event_type: str = "cloud_sea",
    score: int = 85,
    status: str = "Recommended",
    confidence: str = "High",
    time_window: str = "07:00 - 08:00",
) -> ScoreResult:
    return ScoreResult(
        event_type=event_type,
        total_score=score,
        status=status,
        breakdown={"gap": {"score": 50, "max": 50}},
        time_window=time_window,
        confidence=confidence,
    )


def _make_viewpoint(
    vid: str = "niubei_gongga", name: str = "牛背山"
) -> Viewpoint:
    return Viewpoint(
        id=vid,
        name=name,
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["sunrise", "cloud_sea"],
        targets=[],
    )


def _make_pipeline_result(
    viewpoint: Viewpoint | None = None,
    days: list[ForecastDay] | None = None,
) -> PipelineResult:
    vp = viewpoint or _make_viewpoint()
    if days is None:
        e1 = _make_event("cloud_sea", 90, "Recommended", "High")
        e2 = _make_event("sunrise_golden_mountain", 85, "Recommended", "High")
        days = [
            ForecastDay(
                date="2026-02-12",
                summary="",
                best_event=e1,
                events=[e1, e2],
                confidence="High",
            )
        ]
    return PipelineResult(
        viewpoint=vp,
        forecast_days=days,
        meta={
            "generated_at": "2026-02-12T05:00:00+08:00",
            "engine_version": "4.0.0",
        },
    )


# ── 单站 forecast 测试 ──


class TestForecastReporterGenerate:
    """generate() — 单站 forecast"""

    def test_contains_all_top_level_fields(self) -> None:
        reporter = ForecastReporter()
        result = reporter.generate(_make_pipeline_result())
        assert result["viewpoint_id"] == "niubei_gongga"
        assert result["viewpoint_name"] == "牛背山"
        assert "generated_at" in result
        assert "forecast_days" in result
        assert "daily" in result

    def test_events_sorted_by_score_descending(self) -> None:
        """events 按 score 降序排列"""
        e1 = _make_event("frost", 70, "Possible")
        e2 = _make_event("cloud_sea", 90, "Recommended")
        e3 = _make_event("sunrise_golden_mountain", 85, "Recommended")
        day = ForecastDay(
            date="2026-02-12",
            summary="",
            best_event=e2,
            events=[e1, e2, e3],
            confidence="High",
        )
        result = ForecastReporter().generate(
            _make_pipeline_result(days=[day])
        )
        daily_events = result["daily"][0]["events"]
        scores = [ev["score"] for ev in daily_events]
        assert scores == sorted(scores, reverse=True)

    def test_best_event_is_highest_score(self) -> None:
        """best_event 为最高分事件"""
        e1 = _make_event("frost", 70, "Possible")
        e2 = _make_event("cloud_sea", 95, "Perfect")
        day = ForecastDay(
            date="2026-02-12",
            summary="",
            best_event=e2,
            events=[e1, e2],
            confidence="High",
        )
        result = ForecastReporter().generate(
            _make_pipeline_result(days=[day])
        )
        best = result["daily"][0]["best_event"]
        assert best["score"] == 95
        assert best["event_type"] == "cloud_sea"

    def test_summary_generated_by_summary_generator(self) -> None:
        """summary 由 SummaryGenerator 生成"""
        result = ForecastReporter().generate(_make_pipeline_result())
        summary = result["daily"][0]["summary"]
        # SummaryGenerator 应生成非空摘要
        assert len(summary) > 0
        assert summary != ""

    def test_event_has_confidence_field(self) -> None:
        """每个 event 有 confidence 字段"""
        result = ForecastReporter().generate(_make_pipeline_result())
        for ev in result["daily"][0]["events"]:
            assert "confidence" in ev

    def test_sunrise_event_has_correct_tags(self) -> None:
        """sunrise_golden_mountain 事件包含 sunrise 和 golden_mountain tags"""
        e = _make_event("sunrise_golden_mountain", 90, "Recommended")
        day = ForecastDay(
            date="2026-02-12",
            summary="",
            best_event=e,
            events=[e],
            confidence="High",
        )
        result = ForecastReporter().generate(
            _make_pipeline_result(days=[day])
        )
        tags = result["daily"][0]["events"][0]["tags"]
        assert "sunrise" in tags
        assert "golden_mountain" in tags

    def test_high_score_event_has_magnificent_tag(self) -> None:
        """评分 >= 85 的事件包含 magnificent tag"""
        e = _make_event("cloud_sea", 90, "Recommended")
        day = ForecastDay(
            date="2026-02-12",
            summary="",
            best_event=e,
            events=[e],
            confidence="High",
        )
        result = ForecastReporter().generate(
            _make_pipeline_result(days=[day])
        )
        tags = result["daily"][0]["events"][0]["tags"]
        assert "magnificent" in tags

    def test_event_with_warnings_has_partial_data_tag(self) -> None:
        """有 warnings 的事件包含 partial_data tag"""
        e = ScoreResult(
            event_type="cloud_sea",
            total_score=70,
            status="Possible",
            breakdown={},
            warnings=["数据缺失"],
        )
        day = ForecastDay(
            date="2026-02-12",
            summary="",
            best_event=e,
            events=[e],
            confidence="High",
        )
        result = ForecastReporter().generate(
            _make_pipeline_result(days=[day])
        )
        tags = result["daily"][0]["events"][0]["tags"]
        assert "partial_data" in tags
        assert "magnificent" not in tags  # score < 85


# ── 路线 forecast 测试 ──


class TestForecastReporterGenerateRoute:
    """generate_route() — 路线 forecast"""

    def _make_route(self) -> Route:
        return Route(
            id="lixiao",
            name="理小路",
            description="理县到小金路线",
            stops=[
                RouteStop(viewpoint_id="zheduo_gongga", order=1, stay_note="建议停留2小时"),
                RouteStop(viewpoint_id="niubei_gongga", order=2, stay_note="建议停留3小时"),
            ],
        )

    def test_two_stops_produces_stops_array_len_2(self) -> None:
        """2 站 PipelineResult → stops 数组长度 2"""
        route = self._make_route()
        p1 = _make_pipeline_result(
            viewpoint=_make_viewpoint("zheduo_gongga", "折多山")
        )
        p2 = _make_pipeline_result(
            viewpoint=_make_viewpoint("niubei_gongga", "牛背山")
        )
        result = ForecastReporter().generate_route([p1, p2], route)
        assert len(result["stops"]) == 2

    def test_stops_sorted_by_order(self) -> None:
        """stops 按 order 排序"""
        route = self._make_route()
        # 故意反序传入
        p1 = _make_pipeline_result(
            viewpoint=_make_viewpoint("niubei_gongga", "牛背山")
        )
        p2 = _make_pipeline_result(
            viewpoint=_make_viewpoint("zheduo_gongga", "折多山")
        )
        result = ForecastReporter().generate_route([p1, p2], route)
        orders = [s["order"] for s in result["stops"]]
        assert orders == sorted(orders)

    def test_route_id_and_name_correct(self) -> None:
        """route_id / route_name / forecast_days 正确填充"""
        route = self._make_route()
        p1 = _make_pipeline_result(
            viewpoint=_make_viewpoint("zheduo_gongga", "折多山")
        )
        p2 = _make_pipeline_result(
            viewpoint=_make_viewpoint("niubei_gongga", "牛背山")
        )
        result = ForecastReporter().generate_route([p1, p2], route)
        assert result["route_id"] == "lixiao"
        assert result["route_name"] == "理小路"
        assert "generated_at" in result
        assert result["forecast_days"] == 1

    def test_each_stop_forecast_matches_single_station_format(self) -> None:
        """每站 forecast 格式与单站一致"""
        route = self._make_route()
        p1 = _make_pipeline_result(
            viewpoint=_make_viewpoint("zheduo_gongga", "折多山")
        )
        result = ForecastReporter().generate_route([p1], route)
        stop_forecast = result["stops"][0]["forecast"]
        # 单站格式的核心字段
        assert "viewpoint_id" in stop_forecast
        assert "daily" in stop_forecast

