"""测试 gmp.core.models 数据模型"""

from datetime import date, datetime

from gmp.core.models import (
    AnalysisResult,
    DataContext,
    DataRequirement,
    Location,
    MoonStatus,
    ScoreResult,
    StargazingWindow,
    SunEvents,
    Target,
    Viewpoint,
)


class TestLocation:
    def test_location_creation(self):
        """Location 正确创建"""
        loc = Location(lat=29.75, lon=102.35, altitude=3660)
        assert loc.lat == 29.75
        assert loc.lon == 102.35
        assert loc.altitude == 3660


class TestViewpoint:
    def test_viewpoint_with_targets(self):
        """Viewpoint 包含 Target 列表"""
        loc = Location(lat=29.75, lon=102.35, altitude=3660)
        targets = [
            Target(
                name="贡嘎主峰",
                lat=29.58,
                lon=101.88,
                altitude=7556,
                weight="primary",
                applicable_events=None,
            ),
            Target(
                name="雅拉神山",
                lat=30.15,
                lon=101.75,
                altitude=5820,
                weight="secondary",
                applicable_events=["sunset"],
            ),
        ]
        vp = Viewpoint(
            id="niubei_gongga",
            name="牛背山",
            location=loc,
            capabilities=["sunrise", "sunset", "stargazing"],
            targets=targets,
        )
        assert vp.id == "niubei_gongga"
        assert len(vp.targets) == 2
        assert vp.targets[0].weight == "primary"
        assert vp.targets[0].applicable_events is None
        assert vp.targets[1].applicable_events == ["sunset"]
        assert "sunrise" in vp.capabilities


class TestScoreResult:
    def test_score_result_status(self):
        """ScoreResult 状态字符串正确"""
        result = ScoreResult(
            total_score=87,
            status="Recommended",
            breakdown={
                "light_path": {"score": 31, "max": 35, "detail": "光路云量8%"},
                "target_visible": {"score": 35, "max": 40, "detail": "目标云量13%"},
                "local_clear": {"score": 21, "max": 25, "detail": "本地云量22%"},
            },
        )
        assert result.total_score == 87
        assert result.status == "Recommended"
        assert "light_path" in result.breakdown
        assert result.breakdown["light_path"]["score"] == 31


class TestDataRequirement:
    def test_data_requirement_defaults(self):
        """DataRequirement 默认值全 False/None"""
        req = DataRequirement()
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False
        assert req.season_months is None

    def test_data_requirement_custom(self):
        """DataRequirement 自定义值"""
        req = DataRequirement(
            needs_l2_target=True,
            needs_l2_light_path=True,
            needs_astro=True,
            season_months=[10, 11, 12],
        )
        assert req.needs_l2_target is True
        assert req.season_months == [10, 11, 12]


class TestSunEvents:
    def test_sun_events_creation(self):
        """SunEvents 正确创建"""
        se = SunEvents(
            sunrise=datetime(2026, 2, 11, 7, 25),
            sunset=datetime(2026, 2, 11, 18, 30),
            sunrise_azimuth=108.5,
            sunset_azimuth=251.5,
            astronomical_dawn=datetime(2026, 2, 11, 5, 50),
            astronomical_dusk=datetime(2026, 2, 11, 20, 5),
        )
        assert se.sunrise_azimuth == 108.5
        assert se.sunset_azimuth == 251.5


class TestMoonStatus:
    def test_moon_status_optional_fields(self):
        """MoonStatus 可选字段默认 None"""
        ms = MoonStatus(phase=35, elevation=-15.0)
        assert ms.phase == 35
        assert ms.moonrise is None
        assert ms.moonset is None


class TestStargazingWindow:
    def test_stargazing_window_defaults(self):
        """StargazingWindow 默认 quality 为 poor"""
        sw = StargazingWindow()
        assert sw.quality == "poor"
        assert sw.optimal_start is None


class TestAnalysisResult:
    def test_analysis_result_creation(self):
        """AnalysisResult 正确创建"""
        ar = AnalysisResult(
            passed=True,
            score=85,
            reason="L1 通过",
            details={"cloud_cover": 15},
        )
        assert ar.passed is True
        assert ar.details["cloud_cover"] == 15


class TestDataContext:
    def test_data_context_creation(self):
        """DataContext 可正确实例化 (前向引用不报错)"""
        loc = Location(lat=29.75, lon=102.35, altitude=3660)
        vp = Viewpoint(
            id="test", name="测试", location=loc, capabilities=["sunrise"]
        )
        ctx = DataContext(
            date=date(2026, 1, 1), viewpoint=vp, local_weather=None
        )
        assert ctx.date == date(2026, 1, 1)
        assert ctx.viewpoint.id == "test"
        assert ctx.local_weather is None

    def test_data_context_optional_defaults(self):
        """DataContext 可选字段默认 None"""
        loc = Location(lat=0, lon=0, altitude=0)
        vp = Viewpoint(id="x", name="x", location=loc, capabilities=[])
        ctx = DataContext(
            date=date(2026, 1, 1), viewpoint=vp, local_weather=None
        )
        assert ctx.sun_events is None
        assert ctx.moon_status is None
        assert ctx.stargazing_window is None
        assert ctx.target_weather is None
        assert ctx.light_path_weather is None
        assert ctx.l2_result is None
