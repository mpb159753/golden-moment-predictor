"""tests/unit/test_models.py — 核心数据模型测试"""

from datetime import datetime, date
from typing import Optional

import pytest

from gmp.core.models import (
    Location,
    Target,
    Viewpoint,
    RouteStop,
    Route,
    SunEvents,
    MoonStatus,
    StargazingWindow,
    ScoreResult,
    ForecastDay,
    PipelineResult,
    score_to_status,
    days_ahead_to_confidence,
)


# ==================== Location ====================

class TestLocation:
    def test_basic_construction(self):
        loc = Location(lat=29.6, lon=102.3, altitude=3600)
        assert loc.lat == 29.6
        assert loc.lon == 102.3
        assert loc.altitude == 3600

    def test_negative_coordinates(self):
        loc = Location(lat=-33.8, lon=-70.6, altitude=500)
        assert loc.lat == -33.8
        assert loc.lon == -70.6

    def test_zero_coordinates(self):
        loc = Location(lat=0.0, lon=0.0, altitude=0)
        assert loc.lat == 0.0
        assert loc.lon == 0.0
        assert loc.altitude == 0


# ==================== Target ====================

class TestTarget:
    def test_primary_weight(self):
        t = Target(
            name="贡嘎", lat=29.6, lon=101.8, altitude=7556,
            weight="primary", applicable_events=None,
        )
        assert t.weight == "primary"
        assert t.applicable_events is None

    def test_secondary_weight(self):
        t = Target(
            name="田海子", lat=29.5, lon=101.9, altitude=6070,
            weight="secondary", applicable_events=["sunrise"],
        )
        assert t.weight == "secondary"
        assert t.applicable_events == ["sunrise"]

    def test_invalid_weight_raises(self):
        with pytest.raises(ValueError, match="weight 必须为"):
            Target(
                name="X", lat=0, lon=0, altitude=0,
                weight="invalid", applicable_events=None,
            )


# ==================== Viewpoint ====================

class TestViewpoint:
    def test_basic_construction(self):
        loc = Location(lat=29.6, lon=102.3, altitude=3600)
        vp = Viewpoint(
            id="niubei",
            name="牛背山",
            location=loc,
            capabilities=["sunrise", "sunset", "stargazing"],
            targets=[],
        )
        assert vp.id == "niubei"
        assert vp.name == "牛背山"
        assert vp.location is loc
        assert len(vp.capabilities) == 3

    def test_empty_capabilities(self):
        loc = Location(lat=0, lon=0, altitude=0)
        vp = Viewpoint(id="x", name="x", location=loc, capabilities=[], targets=[])
        assert vp.capabilities == []


# ==================== RouteStop & Route ====================

class TestRouteStop:
    def test_basic_construction(self):
        rs = RouteStop(viewpoint_id="niubei", order=1, stay_note="建议日落前到达")
        assert rs.viewpoint_id == "niubei"
        assert rs.order == 1
        assert rs.stay_note == "建议日落前到达"

    def test_default_stay_note(self):
        rs = RouteStop(viewpoint_id="x", order=2)
        assert rs.stay_note == ""


class TestRoute:
    def test_basic_construction(self):
        r = Route(id="lixiao", name="理小路", description="经典线路")
        assert r.id == "lixiao"
        assert r.name == "理小路"
        assert r.description == "经典线路"

    def test_default_stops(self):
        r = Route(id="x", name="x")
        assert r.stops == []

    def test_with_stops(self):
        stops = [RouteStop(viewpoint_id="a", order=1), RouteStop(viewpoint_id="b", order=2)]
        r = Route(id="r1", name="Route 1", stops=stops)
        assert len(r.stops) == 2
        assert r.stops[0].order == 1


# ==================== SunEvents ====================

class TestSunEvents:
    def test_basic_construction(self):
        se = SunEvents(
            sunrise=datetime(2025, 1, 1, 7, 15),
            sunset=datetime(2025, 1, 1, 17, 30),
            sunrise_azimuth=118.5,
            sunset_azimuth=241.3,
            astronomical_dawn=datetime(2025, 1, 1, 5, 45),
            astronomical_dusk=datetime(2025, 1, 1, 19, 0),
        )
        assert se.sunrise_azimuth == 118.5
        assert se.sunset_azimuth == 241.3


# ==================== MoonStatus ====================

class TestMoonStatus:
    def test_basic_construction(self):
        ms = MoonStatus(
            phase=75, elevation=-5.2,
            moonrise=datetime(2025, 1, 1, 20, 0),
            moonset=datetime(2025, 1, 2, 8, 0),
        )
        assert ms.phase == 75
        assert ms.elevation == -5.2

    def test_optional_times(self):
        ms = MoonStatus(phase=0, elevation=10.0, moonrise=None, moonset=None)
        assert ms.moonrise is None
        assert ms.moonset is None


# ==================== StargazingWindow ====================

class TestStargazingWindow:
    @pytest.mark.parametrize("quality", ["optimal", "good", "partial", "poor"])
    def test_quality_values(self, quality):
        sw = StargazingWindow(
            optimal_start=None, optimal_end=None,
            good_start=None, good_end=None,
            quality=quality,
        )
        assert sw.quality == quality


# ==================== ScoreResult ====================

class TestScoreResult:
    def test_basic_construction(self):
        sr = ScoreResult(
            event_type="sunrise",
            total_score=85,
            status="Recommended",
            breakdown={"light": {"score": 30, "max": 40, "detail": "良好"}},
        )
        assert sr.event_type == "sunrise"
        assert sr.total_score == 85
        assert sr.status == "Recommended"

    def test_default_values(self):
        sr = ScoreResult(
            event_type="sunset",
            total_score=50,
            status="Possible",
            breakdown={},
        )
        assert sr.time_window == ""
        assert sr.confidence == ""
        assert sr.highlights == []
        assert sr.warnings == []
        assert sr.note == ""


# ==================== ForecastDay ====================

class TestForecastDay:
    def test_basic_construction(self):
        sr = ScoreResult(
            event_type="sunrise", total_score=95,
            status="Perfect", breakdown={},
        )
        fd = ForecastDay(
            date="2025-01-15",
            summary="日照金山最佳日",
            best_event=sr,
            events=[sr],
            confidence="High",
        )
        assert fd.date == "2025-01-15"
        assert fd.best_event is sr
        assert len(fd.events) == 1
        assert fd.confidence == "High"

    def test_no_best_event(self):
        fd = ForecastDay(
            date="2025-01-16", summary="无推荐",
            best_event=None, events=[], confidence="Low",
        )
        assert fd.best_event is None
        assert fd.events == []


# ==================== PipelineResult ====================

class TestPipelineResult:
    def test_basic_construction(self):
        loc = Location(lat=29.6, lon=102.3, altitude=3600)
        vp = Viewpoint(id="niubei", name="牛背山", location=loc, capabilities=[], targets=[])
        pr = PipelineResult(
            viewpoint=vp,
            forecast_days=[],
            meta={"generated_at": "2025-01-15T12:00:00", "engine_version": "0.1"},
        )
        assert pr.viewpoint is vp
        assert pr.forecast_days == []
        assert pr.meta["engine_version"] == "0.1"


# ==================== score_to_status ====================

class TestScoreToStatus:
    @pytest.mark.parametrize(
        "score, expected",
        [
            (0, "Not Recommended"),
            (49, "Not Recommended"),
            (50, "Possible"),
            (79, "Possible"),
            (80, "Recommended"),
            (94, "Recommended"),
            (95, "Perfect"),
            (100, "Perfect"),
        ],
    )
    def test_default_thresholds(self, score, expected):
        assert score_to_status(score) == expected

    def test_custom_thresholds(self):
        thresholds = {"perfect": 90, "recommended": 70, "possible": 40}
        assert score_to_status(90, thresholds=thresholds) == "Perfect"
        assert score_to_status(89, thresholds=thresholds) == "Recommended"
        assert score_to_status(70, thresholds=thresholds) == "Recommended"
        assert score_to_status(69, thresholds=thresholds) == "Possible"
        assert score_to_status(40, thresholds=thresholds) == "Possible"
        assert score_to_status(39, thresholds=thresholds) == "Not Recommended"


# ==================== days_ahead_to_confidence ====================

class TestDaysAheadToConfidence:
    @pytest.mark.parametrize(
        "days, expected",
        [
            (1, "High"),
            (2, "High"),
            (3, "Medium"),
            (4, "Medium"),
            (5, "Low"),
            (10, "Low"),
            (16, "Low"),
        ],
    )
    def test_default_config(self, days, expected):
        assert days_ahead_to_confidence(days) == expected

    def test_custom_config(self):
        config = {"high": [1, 3], "medium": [4, 7], "low": [8, 16]}
        assert days_ahead_to_confidence(3, config=config) == "High"
        assert days_ahead_to_confidence(4, config=config) == "Medium"
        assert days_ahead_to_confidence(8, config=config) == "Low"
