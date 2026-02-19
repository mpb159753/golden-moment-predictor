"""tests/unit/test_timeline_reporter.py — TimelineReporter 单元测试"""

from __future__ import annotations

from datetime import date

import pytest

from gmp.core.models import (
    ForecastDay,
    Location,
    PipelineResult,
    ScoreResult,
    Viewpoint,
)
from gmp.output.timeline_reporter import TimelineReporter


# ── helpers ──


def _make_event(
    event_type: str = "cloud_sea",
    score: int = 85,
    status: str = "Recommended",
    time_window: str = "06:00 - 09:00",
) -> ScoreResult:
    return ScoreResult(
        event_type=event_type,
        total_score=score,
        status=status,
        breakdown={"gap": {"score": 50, "max": 50}},
        time_window=time_window,
    )


def _make_viewpoint() -> Viewpoint:
    return Viewpoint(
        id="niubei_gongga",
        name="牛背山",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["sunrise", "cloud_sea"],
        targets=[],
    )


def _make_hourly_weather() -> dict[str, dict[int, dict]]:
    """生成 24 小时天气数据 — 与 _extract_hourly_weather 输出一致的格式"""
    day_data: dict[int, dict] = {}
    for h in range(24):
        day_data[h] = {
            "temperature": -3.2 + h * 0.5,
            "cloud_cover": 25,
            "weather_icon": "partly_cloudy",
        }
    return {"2026-02-12": day_data}


def _make_safety_hours() -> dict[int, bool]:
    """默认所有小时 safety_passed = True"""
    return {h: True for h in range(24)}


def _make_pipeline_result(
    events: list[ScoreResult] | None = None,
    hourly_weather: dict[str, dict[int, dict]] | None = None,
    safety_hours: dict[int, bool] | None = None,
) -> PipelineResult:
    if events is None:
        events = [_make_event()]
    day = ForecastDay(
        date="2026-02-12",
        summary="推荐观景 — 云海",
        best_event=events[0] if events else None,
        events=events,
        confidence="High",
    )
    hw = hourly_weather if hourly_weather is not None else _make_hourly_weather()
    return PipelineResult(
        viewpoint=_make_viewpoint(),
        forecast_days=[day],
        meta={
            "generated_at": "2026-02-12T05:00:00+08:00",
            "hourly_weather": hw,
            "safety_hours": safety_hours or _make_safety_hours(),
        },
    )


# ── 24 小时逐时输出 ──


class TestTimelineReporter24Hours:
    """hourly 应包含 24 条记录"""

    def test_hourly_has_24_entries(self) -> None:
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        assert len(result["hourly"]) == 24

    def test_hourly_hours_0_to_23(self) -> None:
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        hours = [entry["hour"] for entry in result["hourly"]]
        assert hours == list(range(24))

    def test_hourly_time_format(self) -> None:
        """每条记录的 time 字段为 HH:00 格式"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        assert result["hourly"][0]["time"] == "00:00"
        assert result["hourly"][6]["time"] == "06:00"
        assert result["hourly"][23]["time"] == "23:00"


# ── safety_passed 标记 ──


class TestTimelineReporterSafety:
    """safety_passed 正确标记"""

    def test_all_safe_hours(self) -> None:
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        for entry in result["hourly"]:
            assert entry["safety_passed"] is True

    def test_unsafe_hours_marked_false(self) -> None:
        safety = _make_safety_hours()
        safety[3] = False
        safety[4] = False
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(safety_hours=safety), date(2026, 2, 12)
        )
        assert result["hourly"][3]["safety_passed"] is False
        assert result["hourly"][4]["safety_passed"] is False
        assert result["hourly"][5]["safety_passed"] is True


# ── 活跃事件标记 ──


class TestTimelineReporterEventsActive:
    """活跃事件在对应时段标记"""

    def test_event_active_in_time_window(self) -> None:
        """cloud_sea 06:00-09:00 → hour 6,7,8 有 events_active"""
        event = _make_event("cloud_sea", 90, "Recommended", "06:00 - 09:00")
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        # hour 6 应包含 cloud_sea
        active_6 = result["hourly"][6]["events_active"]
        assert len(active_6) == 1
        assert active_6[0]["event_type"] == "cloud_sea"

        # hour 8 应包含 cloud_sea
        active_8 = result["hourly"][8]["events_active"]
        assert len(active_8) == 1

        # hour 9 不在窗口内
        active_9 = result["hourly"][9]["events_active"]
        assert len(active_9) == 0

    def test_no_events_date_has_empty_events_active(self) -> None:
        """无活跃事件时 events_active 为空"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[]), date(2026, 2, 12)
        )
        for entry in result["hourly"]:
            assert entry["events_active"] == []


# ── tags 自动生成 ──


class TestTimelineReporterTags:
    """tags 自动生成"""

    def test_sunrise_tag(self) -> None:
        """日出事件在其时段内的 hour 应包含 sunrise tag"""
        event = _make_event(
            "sunrise_golden_mountain", 85, "Recommended", "07:00 - 08:00"
        )
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        tags_7 = result["hourly"][7]["tags"]
        assert "sunrise" in tags_7

    def test_sunset_tag(self) -> None:
        """日落事件在其时段应包含 sunset tag"""
        event = _make_event(
            "sunset_golden_mountain", 80, "Recommended", "18:00 - 19:00"
        )
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        tags_18 = result["hourly"][18]["tags"]
        assert "sunset" in tags_18

    def test_golden_mountain_tag(self) -> None:
        """金山事件在活跃时段包含 golden_mountain tag"""
        event = _make_event(
            "sunrise_golden_mountain", 85, "Recommended", "07:00 - 08:00"
        )
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        tags_7 = result["hourly"][7]["tags"]
        assert "golden_mountain" in tags_7

    def test_cloud_sea_tag(self) -> None:
        """cloud_sea 事件在活跃时段包含 cloud_sea tag"""
        event = _make_event("cloud_sea", 90, "Recommended", "06:00 - 09:00")
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        tags_6 = result["hourly"][6]["tags"]
        assert "cloud_sea" in tags_6

    def test_clear_sky_tag(self) -> None:
        """cloud_cover < 30 时生成 clear_sky tag"""
        weather = _make_hourly_weather()
        weather["2026-02-12"][10] = {**weather["2026-02-12"][10], "cloud_cover": 20}
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[], hourly_weather=weather),
            date(2026, 2, 12),
        )
        assert "clear_sky" in result["hourly"][10]["tags"]

    def test_no_clear_sky_tag_when_cloudy(self) -> None:
        """cloud_cover >= 30 时不生成 clear_sky tag"""
        weather = _make_hourly_weather()
        weather["2026-02-12"][10] = {**weather["2026-02-12"][10], "cloud_cover": 30}
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[], hourly_weather=weather),
            date(2026, 2, 12),
        )
        assert "clear_sky" not in result["hourly"][10]["tags"]

    def test_magnificent_tag(self) -> None:
        """活跃事件 score >= 85 时生成 magnificent tag"""
        event = _make_event("cloud_sea", 85, "Recommended", "06:00 - 09:00")
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        assert "magnificent" in result["hourly"][6]["tags"]

    def test_no_magnificent_tag_below_85(self) -> None:
        """活跃事件 score < 85 时不生成 magnificent tag"""
        event = _make_event("cloud_sea", 60, "Possible", "06:00 - 09:00")
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        assert "magnificent" not in result["hourly"][6]["tags"]

    def test_partial_data_tag(self) -> None:
        """weather 为空 dict 时生成 partial_data tag"""
        weather = _make_hourly_weather()
        weather["2026-02-12"][5] = {}
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[], hourly_weather=weather),
            date(2026, 2, 12),
        )
        assert "partial_data" in result["hourly"][5]["tags"]

    def test_no_event_hour_has_empty_tags(self) -> None:
        """无事件的时段 tags 为空列表（weather 有完整数据且 cloud_cover >= 30）"""
        weather = _make_hourly_weather()
        # 确保 hour 15 cloud_cover >= 30 以不触发 clear_sky
        weather["2026-02-12"][15] = {**weather["2026-02-12"][15], "cloud_cover": 50}
        event = _make_event("cloud_sea", 90, "Recommended", "06:00 - 09:00")
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event], hourly_weather=weather),
            date(2026, 2, 12),
        )
        tags_15 = result["hourly"][15]["tags"]
        assert tags_15 == []


# ── 边界处理 ──


class TestTimelineReporterBoundary:
    """边界情况"""

    def test_hour_0_and_23_normal(self) -> None:
        """hour=0 和 hour=23 正常处理"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        h0 = result["hourly"][0]
        h23 = result["hourly"][23]
        assert h0["hour"] == 0
        assert h23["hour"] == 23
        assert "weather" in h0
        assert "weather" in h23

    def test_no_events_still_has_24_weather(self) -> None:
        """无活跃事件的日期 → hourly 仍有 24 条 weather 数据"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[]), date(2026, 2, 12)
        )
        assert len(result["hourly"]) == 24
        for entry in result["hourly"]:
            assert "weather" in entry


# ── 跨午夜时间窗口 ──


class TestTimelineReporterCrossMidnight:
    """跨午夜时间窗口处理"""

    def test_cross_midnight_window(self) -> None:
        """21:00 - 03:00 跨午夜窗口应正确解析"""
        event = _make_event(
            "stargazing", 85, "Recommended", "21:00 - 03:00"
        )
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(events=[event]), date(2026, 2, 12)
        )
        # hour 21, 22, 23 应有事件
        assert len(result["hourly"][21]["events_active"]) == 1
        assert len(result["hourly"][22]["events_active"]) == 1
        assert len(result["hourly"][23]["events_active"]) == 1
        # hour 0, 1, 2 应有事件
        assert len(result["hourly"][0]["events_active"]) == 1
        assert len(result["hourly"][1]["events_active"]) == 1
        assert len(result["hourly"][2]["events_active"]) == 1
        # hour 3 不在窗口内
        assert len(result["hourly"][3]["events_active"]) == 0


# ── 顶层字段 ──


class TestTimelineReporterTopLevel:
    """顶层字段"""

    def test_viewpoint_id(self) -> None:
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        assert result["viewpoint_id"] == "niubei_gongga"

    def test_generated_at(self) -> None:
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        assert result["generated_at"] == "2026-02-12T05:00:00+08:00"

    def test_date_field(self) -> None:
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result(), date(2026, 2, 12)
        )
        assert result["date"] == "2026-02-12"


# ── 天气字段验证 (MG3A Task 2) ──


def _make_hourly_weather_new_format(
    target_date: str = "2026-02-12",
) -> dict[str, dict[int, dict]]:
    """生成新格式天气数据 {date_str: {hour: weather_dict}}"""
    day_data: dict[int, dict] = {}
    for h in range(24):
        day_data[h] = {
            "temperature": -3.2 + h * 0.5,
            "cloud_cover": 25,
            "weather_icon": "partly_cloudy",
        }
    return {target_date: day_data}


def _make_pipeline_result_new_format(
    events: list[ScoreResult] | None = None,
    hourly_weather: dict | None = None,
    safety_hours: dict[int, bool] | None = None,
) -> PipelineResult:
    if events is None:
        events = [_make_event()]
    day = ForecastDay(
        date="2026-02-12",
        summary="推荐观景 — 云海",
        best_event=events[0] if events else None,
        events=events,
        confidence="High",
    )
    hw = hourly_weather if hourly_weather is not None else _make_hourly_weather_new_format()
    return PipelineResult(
        viewpoint=_make_viewpoint(),
        forecast_days=[day],
        meta={
            "generated_at": "2026-02-12T05:00:00+08:00",
            "hourly_weather": hw,
            "safety_hours": safety_hours or _make_safety_hours(),
        },
    )


class TestTimelineReporterWeatherFields:
    """MG3A Task 2 — weather 包含 temperature/cloud_cover/weather_icon"""

    def test_weather_contains_temperature(self) -> None:
        """每小时 weather 包含 temperature 字段"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result_new_format(), date(2026, 2, 12)
        )
        weather_6 = result["hourly"][6]["weather"]
        assert "temperature" in weather_6

    def test_weather_contains_cloud_cover(self) -> None:
        """每小时 weather 包含 cloud_cover 字段"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result_new_format(), date(2026, 2, 12)
        )
        weather_6 = result["hourly"][6]["weather"]
        assert "cloud_cover" in weather_6

    def test_weather_contains_weather_icon(self) -> None:
        """每小时 weather 包含 weather_icon 字段"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result_new_format(), date(2026, 2, 12)
        )
        weather_6 = result["hourly"][6]["weather"]
        assert "weather_icon" in weather_6

    def test_no_weather_data_returns_empty_dict(self) -> None:
        """无天气数据时 weather 为空 dict"""
        reporter = TimelineReporter()
        result = reporter.generate(
            _make_pipeline_result_new_format(hourly_weather={}),
            date(2026, 2, 12),
        )
        for entry in result["hourly"]:
            assert entry["weather"] == {}

