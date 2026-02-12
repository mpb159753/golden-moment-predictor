"""Module 07 集成测试 — GMPScheduler + AnalyzerPipeline

所有外部依赖 (MeteoFetcher, AstroUtils) 使用 mock 替代，
确保测试不依赖网络、天文库精度或当前日期。

测试用例覆盖:
  - 完整晴天管线 (含分数/breakdown/status 传递)
  - 雨天 L1 拦截
  - events 过滤
  - 置信度映射 (配置驱动)
  - L1 context 传递 (viewpoint + sun_events → matched_targets)
  - 7 天预测结构
  - 季节过滤
  - Plugin 异常隔离 (score + check_trigger)
  - 需求聚合
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from gmp.analyzer.local_analyzer import LocalAnalyzer
from gmp.analyzer.remote_analyzer import RemoteAnalyzer
from gmp.astro.astro_utils import AstroUtils
from gmp.astro.geo_utils import GeoUtils
from gmp.fetcher.meteo_fetcher import MeteoFetcher
from gmp.core.config_loader import EngineConfig, ViewpointConfig
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
from gmp.core.pipeline import AnalyzerPipeline
from gmp.core.scheduler import GMPScheduler
from gmp.scorer.engine import ScoreEngine

# UTC+8
_CST = timezone(timedelta(hours=8))


# ======================================================================
# Fixtures
# ======================================================================


def _make_viewpoint(
    capabilities: list[str] | None = None,
    targets: list[Target] | None = None,
) -> Viewpoint:
    """创建标准测试观景台"""
    if capabilities is None:
        capabilities = ["sunrise", "sunset", "stargazing", "cloud_sea", "frost"]
    if targets is None:
        targets = [
            Target(
                name="贡嘎山",
                lat=29.58,
                lon=101.88,
                altitude=7556,
                weight="primary",
                applicable_events=None,
            ),
            Target(
                name="田海子山",
                lat=30.15,
                lon=101.75,
                altitude=5820,
                weight="secondary",
                applicable_events=["sunset"],
            ),
        ]
    return Viewpoint(
        id="test_vp",
        name="测试观景台",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=capabilities,
        targets=targets,
    )


def _make_clear_weather(target_date: date, hours: int = 24) -> pd.DataFrame:
    """生成晴天天气 DataFrame (L1 安全检查通过)"""
    rows = []
    for h in range(hours):
        rows.append({
            "forecast_date": str(target_date),
            "forecast_hour": h,
            "temperature_2m": -2.0 + h * 0.5,
            "cloud_cover_total": 8,
            "cloud_cover_low": 60,   # 高低云 → 云海触发
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


def _make_rainy_weather(target_date: date, hours: int = 24) -> pd.DataFrame:
    """生成雨天天气 DataFrame (L1 安全检查不通过)"""
    rows = []
    for h in range(hours):
        rows.append({
            "forecast_date": str(target_date),
            "forecast_hour": h,
            "temperature_2m": 15.0,
            "cloud_cover_total": 95,
            "cloud_cover_low": 80,
            "cloud_cover_mid": 70,
            "cloud_cover_medium": 70,
            "cloud_cover_high": 50,
            "precipitation_probability": 90,
            "visibility": 500,
            "wind_speed_10m": 25.0,
            "weather_code": 63,
            "snowfall": 0,
            "rain": 5.0,
            "showers": 2.0,
        })
    return pd.DataFrame(rows)


def _make_sun_events(target_date: date) -> SunEvents:
    """创建标准日出/日落事件"""
    d = target_date
    return SunEvents(
        sunrise=datetime(d.year, d.month, d.day, 7, 15, tzinfo=_CST),
        sunset=datetime(d.year, d.month, d.day, 18, 30, tzinfo=_CST),
        sunrise_azimuth=108.5,
        sunset_azimuth=251.5,
        astronomical_dawn=datetime(d.year, d.month, d.day, 5, 40, tzinfo=_CST),
        astronomical_dusk=datetime(d.year, d.month, d.day, 20, 5, tzinfo=_CST),
    )


def _make_moon_status() -> MoonStatus:
    return MoonStatus(phase=15, elevation=-10.0)


def _make_stargazing_window(sun_events: SunEvents) -> StargazingWindow:
    return StargazingWindow(
        good_start=sun_events.astronomical_dusk,
        good_end=sun_events.astronomical_dawn,
        quality="good",
    )


class _SimplePlugin:
    """用于测试的简单 mock Plugin"""

    def __init__(
        self,
        event_type: str,
        display_name: str = "",
        data_requirement: DataRequirement | None = None,
        trigger: bool = True,
        score_value: int = 80,
        raise_on_score: bool = False,
        raise_on_trigger: bool = False,
    ):
        self.event_type = event_type
        self.display_name = display_name or event_type
        self.data_requirement = data_requirement or DataRequirement()
        self._trigger = trigger
        self._score_value = score_value
        self._raise_on_score = raise_on_score
        self._raise_on_trigger = raise_on_trigger

    def check_trigger(self, l1_data: dict) -> bool:
        if self._raise_on_trigger:
            raise RuntimeError(f"Plugin {self.event_type} check_trigger 模拟异常")
        return self._trigger

    def score(self, context: DataContext) -> ScoreResult:
        if self._raise_on_score:
            raise RuntimeError(f"Plugin {self.event_type} 模拟异常")
        return ScoreResult(
            total_score=self._score_value,
            status="Recommended",
            breakdown={"test": {"score": self._score_value, "max": 100}},
        )


def _build_scheduler(
    viewpoint: Viewpoint | None = None,
    plugins: list | None = None,
    weather_all: pd.DataFrame | None = None,
    sun_events: SunEvents | None = None,
) -> GMPScheduler:
    """构建一个完整的 GMPScheduler (所有外部依赖 mock)"""
    config = EngineConfig()

    vp_config = MagicMock(spec=ViewpointConfig)
    vp = viewpoint or _make_viewpoint()
    vp_config.get.return_value = vp

    fetcher = MagicMock(spec=MeteoFetcher)
    if weather_all is not None:
        fetcher.fetch_hourly.return_value = weather_all
    else:
        # 默认返回晴天 7 天数据
        frames = []
        for d in range(7):
            target_d = date.today() + timedelta(days=d + 1)
            frames.append(_make_clear_weather(target_d))
        fetcher.fetch_hourly.return_value = pd.concat(frames, ignore_index=True)

    fetcher.fetch_multi_points.return_value = {}

    astro = MagicMock(spec=AstroUtils)
    se = sun_events or _make_sun_events(date.today() + timedelta(days=1))
    astro.get_sun_events.return_value = se
    astro.get_moon_status.return_value = _make_moon_status()
    astro.determine_stargazing_window.return_value = _make_stargazing_window(se)

    engine = ScoreEngine()
    if plugins:
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


# ======================================================================
# 测试用例
# ======================================================================


class TestFullPipelineClearDay:
    """晴天完整管线: L1 通过 → Plugin 触发 → 评分"""

    def test_clear_day_has_events(self):
        plugins = [
            _SimplePlugin("cloud_sea", "云海", score_value=85),
            _SimplePlugin("frost", "雾凇", score_value=70),
        ]
        vp = _make_viewpoint(capabilities=["cloud_sea", "frost"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run("test_vp", days=1)

        assert result["viewpoint"] == "测试观景台"
        assert len(result["forecast_days"]) == 1

        day = result["forecast_days"][0]
        assert day["confidence"] == "High"
        assert len(day["events"]) == 2

        event_types = {e["event_type"] for e in day["events"]}
        assert "cloud_sea" in event_types
        assert "frost" in event_types

    def test_clear_day_score_values(self):
        """T1: 验证 scheduler 正确传递 Plugin 返回的完整字段"""
        plugins = [_SimplePlugin("cloud_sea", "云海", score_value=87)]
        vp = _make_viewpoint(capabilities=["cloud_sea"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run("test_vp", days=1)
        day = result["forecast_days"][0]
        event = day["events"][0]

        # 验证所有字段正确传递
        assert event["total_score"] == 87
        assert event["event_type"] == "cloud_sea"
        assert event["display_name"] == "云海"
        assert event["status"] == "Recommended"
        assert "test" in event["breakdown"]
        assert event["breakdown"]["test"]["score"] == 87
        assert event["breakdown"]["test"]["max"] == 100


class TestFullPipelineRainyDay:
    """雨天: L1 拦截, events=[], 不触发远程调用"""

    def test_rainy_day_no_events(self):
        plugins = [_SimplePlugin("cloud_sea")]
        vp = _make_viewpoint(capabilities=["cloud_sea"])

        tomorrow = date.today() + timedelta(days=1)
        rainy = _make_rainy_weather(tomorrow)

        scheduler = _build_scheduler(
            viewpoint=vp, plugins=plugins, weather_all=rainy
        )

        result = scheduler.run("test_vp", days=1)
        day = result["forecast_days"][0]
        assert day["events"] == []

    def test_rainy_day_no_remote_calls(self):
        plugins = [
            _SimplePlugin(
                "sunrise_golden_mountain",
                data_requirement=DataRequirement(
                    needs_l2_target=True, needs_l2_light_path=True
                ),
            )
        ]
        vp = _make_viewpoint(capabilities=["sunrise"])
        tomorrow = date.today() + timedelta(days=1)
        rainy = _make_rainy_weather(tomorrow)

        scheduler = _build_scheduler(
            viewpoint=vp, plugins=plugins, weather_all=rainy
        )

        result = scheduler.run("test_vp", days=1)

        # fetch_multi_points 不应被调用 (因为 L1 拦截)
        scheduler._fetcher.fetch_multi_points.assert_not_called()


class TestEventsFilterSkipsL2:
    """仅请求 cloud_sea+frost 时不触发 L2 远程调用"""

    def test_simple_plugins_skip_l2(self):
        plugins = [
            _SimplePlugin("cloud_sea"),
            _SimplePlugin("frost"),
            _SimplePlugin(
                "sunrise_golden_mountain",
                data_requirement=DataRequirement(
                    needs_l2_target=True, needs_l2_light_path=True
                ),
            ),
        ]
        vp = _make_viewpoint(capabilities=["cloud_sea", "frost", "sunrise"])

        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run(
            "test_vp", days=1, events=["cloud_sea", "frost"]
        )

        # 仅 L1 Plugin → 不需要远程数据
        scheduler._fetcher.fetch_multi_points.assert_not_called()

        day = result["forecast_days"][0]
        event_types = {e["event_type"] for e in day["events"]}
        assert "sunrise_golden_mountain" not in event_types


class TestConfidenceMapping:
    """置信度映射: 从 EngineConfig 读取配置"""

    @pytest.mark.parametrize(
        "days_ahead, expected",
        [(1, "High"), (2, "High"), (3, "Medium"), (4, "Medium"),
         (5, "Low"), (6, "Low"), (7, "Low")],
    )
    def test_confidence(self, days_ahead, expected):
        scheduler = _build_scheduler()
        assert scheduler._determine_confidence(days_ahead) == expected


class TestL1ContextPassesViewpointAndSunEvents:
    """T3: 验证 L1 context 传递了 viewpoint 和 sun_events (方位角匹配由 LocalAnalyzer 完成)"""

    def test_l1_context_contains_viewpoint(self):
        """scheduler 传给 L1 的 context 包含 viewpoint，确保 matched_targets 可计算"""
        vp = _make_viewpoint(
            capabilities=["sunrise"],
            targets=[
                Target(
                    name="贡嘎山", lat=29.58, lon=101.88,
                    altitude=7556, weight="primary",
                    applicable_events=None,
                ),
            ],
        )
        plugins = [
            _SimplePlugin(
                "sunrise_golden_mountain",
                data_requirement=DataRequirement(
                    needs_l2_target=True, needs_astro=True,
                ),
            )
        ]
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        # 通过 patch 捕获 L1 analyze 调用参数
        original_analyze = scheduler._local_analyzer.analyze
        captured_contexts = []

        def spy_analyze(data, context):
            captured_contexts.append(context)
            return original_analyze(data, context)

        scheduler._local_analyzer.analyze = spy_analyze
        scheduler.run("test_vp", days=1)

        assert len(captured_contexts) >= 1
        ctx = captured_contexts[0]
        assert "viewpoint" in ctx
        assert ctx["viewpoint"].id == "test_vp"
        assert len(ctx["viewpoint"].targets) == 1
        assert ctx["viewpoint"].targets[0].name == "贡嘎山"


class TestSevenDayForecastStructure:
    """7 天预测结构完整性"""

    def test_7day_structure(self):
        plugins = [_SimplePlugin("cloud_sea")]
        vp = _make_viewpoint(capabilities=["cloud_sea"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run("test_vp", days=7)

        assert len(result["forecast_days"]) == 7
        for day in result["forecast_days"]:
            assert "date" in day
            assert "confidence" in day
            assert "events" in day
            assert isinstance(day["events"], list)

        assert "meta" in result
        assert "api_calls" in result["meta"]


class TestSeasonFilter:
    """非当季 Plugin 被正确跳过"""

    def test_out_of_season_plugin_skipped(self):
        current_month = date.today().month
        # 创建一个不在当前月份的 Plugin
        off_season_months = [(current_month + 6) % 12 or 12]

        plugins = [
            _SimplePlugin(
                "cloud_sea",
                data_requirement=DataRequirement(season_months=off_season_months),
            ),
            _SimplePlugin("frost"),  # 无季节限制
        ]
        vp = _make_viewpoint(capabilities=["cloud_sea", "frost"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run("test_vp", days=1)
        day = result["forecast_days"][0]

        event_types = {e["event_type"] for e in day["events"]}
        assert "cloud_sea" not in event_types
        assert "frost" in event_types

    def test_in_season_plugin_active(self):
        current_month = date.today().month

        plugins = [
            _SimplePlugin(
                "cloud_sea",
                data_requirement=DataRequirement(
                    season_months=[current_month]
                ),
            ),
        ]
        vp = _make_viewpoint(capabilities=["cloud_sea"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        target_date = date.today() + timedelta(days=1)
        active = scheduler._collect_active_plugins(
            vp, None, target_date
        )
        assert len(active) == 1


class TestPluginErrorIsolation:
    """单个 Plugin 异常不影响其他 Plugin"""

    def test_error_plugin_skipped(self):
        plugins = [
            _SimplePlugin("cloud_sea", score_value=85),
            _SimplePlugin("frost", raise_on_score=True),  # 评分异常
        ]
        vp = _make_viewpoint(capabilities=["cloud_sea", "frost"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run("test_vp", days=1)
        day = result["forecast_days"][0]

        # 异常的 frost 被跳过，cloud_sea 正常
        event_types = {e["event_type"] for e in day["events"]}
        assert "cloud_sea" in event_types
        assert "frost" not in event_types

    def test_error_plugin_count(self):
        plugins = [
            _SimplePlugin("cloud_sea", score_value=85),
            _SimplePlugin("frost", raise_on_score=True),
        ]
        vp = _make_viewpoint(capabilities=["cloud_sea", "frost"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run("test_vp", days=1)
        day = result["forecast_days"][0]
        assert len(day["events"]) == 1

    def test_check_trigger_error_isolation(self):
        """T2: check_trigger 抛异常时该 Plugin 被跳过，其他 Plugin 正常"""
        plugins = [
            _SimplePlugin("cloud_sea", score_value=85),
            _SimplePlugin("frost", raise_on_trigger=True),  # check_trigger 异常
        ]
        vp = _make_viewpoint(capabilities=["cloud_sea", "frost"])
        scheduler = _build_scheduler(viewpoint=vp, plugins=plugins)

        result = scheduler.run("test_vp", days=1)
        day = result["forecast_days"][0]

        event_types = {e["event_type"] for e in day["events"]}
        assert "cloud_sea" in event_types
        assert "frost" not in event_types


class TestRequirementAggregation:
    """多 Plugin 需求聚合正确"""

    def test_aggregate_requirements(self):
        p1 = _SimplePlugin(
            "cloud_sea",
            data_requirement=DataRequirement(),
        )
        p2 = _SimplePlugin(
            "sunrise_golden_mountain",
            data_requirement=DataRequirement(
                needs_l2_target=True, needs_l2_light_path=True
            ),
        )
        p3 = _SimplePlugin(
            "stargazing",
            data_requirement=DataRequirement(needs_astro=True),
        )

        engine = ScoreEngine()
        engine.register(p1)
        engine.register(p2)
        engine.register(p3)

        req = engine.collect_requirements([p1, p2, p3])
        assert req.needs_l2_target is True
        assert req.needs_l2_light_path is True
        assert req.needs_astro is True

    def test_no_l2_requirement(self):
        p1 = _SimplePlugin("cloud_sea")
        p2 = _SimplePlugin("frost")

        engine = ScoreEngine()
        engine.register(p1)
        engine.register(p2)

        req = engine.collect_requirements([p1, p2])
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False


class TestAnalyzerPipeline:
    """AnalyzerPipeline L1→L2 管线测试"""

    def test_l1_fail_skips_l2(self):
        config = EngineConfig()
        local = LocalAnalyzer(config)
        remote = RemoteAnalyzer(config)
        pipeline = AnalyzerPipeline(local, remote)

        tomorrow = date.today() + timedelta(days=1)
        rainy = _make_rainy_weather(tomorrow)

        result = pipeline.run(
            rainy,
            {"site_altitude": 3660, "target_hour": 7},
            need_l2=True,
        )

        assert result["l1"].passed is False
        assert result["l2"] is None

    def test_l1_pass_no_l2_needed(self):
        config = EngineConfig()
        local = LocalAnalyzer(config)
        remote = RemoteAnalyzer(config)
        pipeline = AnalyzerPipeline(local, remote)

        tomorrow = date.today() + timedelta(days=1)
        clear = _make_clear_weather(tomorrow)

        result = pipeline.run(
            clear,
            {"site_altitude": 3660, "target_hour": 7},
            need_l2=False,
        )

        assert result["l1"].passed is True
        assert result["l2"] is None

    def test_l1_pass_l2_runs(self):
        config = EngineConfig()
        local = LocalAnalyzer(config)
        remote = RemoteAnalyzer(config)
        pipeline = AnalyzerPipeline(local, remote)

        tomorrow = date.today() + timedelta(days=1)
        clear = _make_clear_weather(tomorrow)

        result = pipeline.run(
            clear,
            {
                "site_altitude": 3660,
                "target_hour": 7,
                "target_weather": {},
                "light_path_weather": [],
            },
            need_l2=True,
        )

        assert result["l1"].passed is True
        assert result["l2"] is not None


class TestSliceDay:
    """_slice_day 天气数据日期切片"""

    def test_slice_exact_date(self):
        tomorrow = date.today() + timedelta(days=1)
        day_after = date.today() + timedelta(days=2)

        df1 = _make_clear_weather(tomorrow)
        df2 = _make_clear_weather(day_after)
        combined = pd.concat([df1, df2], ignore_index=True)

        sliced = GMPScheduler._slice_day(combined, tomorrow)
        assert len(sliced) == 24
        assert all(sliced["forecast_date"] == str(tomorrow))

    def test_slice_empty(self):
        tomorrow = date.today() + timedelta(days=1)
        sliced = GMPScheduler._slice_day(pd.DataFrame(), tomorrow)
        assert sliced.empty


class TestCustomTargetHour:
    """C1: 验证 default_target_hour 配置被正确传递"""

    def test_custom_target_hour_in_l1_context(self):
        """配置 default_target_hour=6 后，L1 context 中 target_hour 应为 6"""
        config = EngineConfig(default_target_hour=6)

        vp = _make_viewpoint(capabilities=["cloud_sea"])
        vp_config = MagicMock(spec=ViewpointConfig)
        vp_config.get.return_value = vp

        tomorrow = date.today() + timedelta(days=1)
        fetcher = MagicMock(spec=MeteoFetcher)
        fetcher.fetch_hourly.return_value = _make_clear_weather(tomorrow)
        fetcher.fetch_multi_points.return_value = {}

        se = _make_sun_events(tomorrow)
        astro = MagicMock(spec=AstroUtils)
        astro.get_sun_events.return_value = se
        astro.get_moon_status.return_value = _make_moon_status()
        astro.determine_stargazing_window.return_value = _make_stargazing_window(se)

        engine = ScoreEngine()
        engine.register(_SimplePlugin("cloud_sea"))

        scheduler = GMPScheduler(
            config=config,
            viewpoint_config=vp_config,
            fetcher=fetcher,
            astro=astro,
            score_engine=engine,
        )

        # 通过 spy 捕获 L1 analyze 参数
        original_analyze = scheduler._local_analyzer.analyze
        captured = []

        def spy(data, context):
            captured.append(context)
            return original_analyze(data, context)

        scheduler._local_analyzer.analyze = spy
        scheduler.run("test_vp", days=1)

        assert len(captured) >= 1
        assert captured[0]["target_hour"] == 6
