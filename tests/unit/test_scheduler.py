"""tests/unit/test_scheduler.py — GMPScheduler 单元测试"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from gmp.core.config_loader import ConfigManager, EngineConfig, ViewpointConfig, RouteConfig
from gmp.core.exceptions import (
    APITimeoutError,
    RouteNotFoundError,
    ServiceUnavailableError,
    ViewpointNotFoundError,
)
from gmp.core.models import (
    ForecastDay,
    Location,
    MoonStatus,
    PipelineResult,
    Route,
    RouteStop,
    ScoreResult,
    StargazingWindow,
    SunEvents,
    Target,
    Viewpoint,
)
from gmp.scoring.engine import ScoreEngine
from gmp.scoring.models import DataContext, DataRequirement


# CST timezone
_CST = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════
# Test Helpers
# ══════════════════════════════════════════════════════


def _make_viewpoint(
    *,
    vp_id: str = "test_vp",
    capabilities: list[str] | None = None,
    targets: list[Target] | None = None,
) -> Viewpoint:
    return Viewpoint(
        id=vp_id,
        name="测试观景台",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=capabilities or ["cloud_sea", "frost"],
        targets=targets or [],
    )


def _make_viewpoint_with_targets() -> Viewpoint:
    """带 Target 的观景台 (需要 L2)"""
    return Viewpoint(
        id="test_vp",
        name="测试观景台",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["sunrise", "sunset", "cloud_sea", "frost"],
        targets=[
            Target(
                name="贡嘎主峰",
                lat=29.58,
                lon=101.88,
                altitude=7556,
                weight="primary",
                applicable_events=None,
            ),
        ],
    )


def _make_clear_weather(days: int = 1, past_days: int = 0) -> pd.DataFrame:
    """生成晴天天气数据 DataFrame"""
    total_days = past_days + days
    hours_per_day = 24
    rows = []
    base_date = date.today() - timedelta(days=past_days)
    for d in range(total_days):
        current_date = base_date + timedelta(days=d)
        for h in range(hours_per_day):
            rows.append({
                "forecast_date": current_date.isoformat(),
                "forecast_hour": h,
                "temperature_2m": -3.0 + h * 0.5,
                "cloud_cover_total": 20,
                "cloud_cover_low": 70,
                "cloud_cover_medium": 5,
                "cloud_cover_high": 2,
                "cloud_base_altitude": 2800,
                "precipitation_probability": 0,
                "visibility": 30000,
                "wind_speed_10m": 3.0,
                "snowfall": 0.0,
                "rain": 0.0,
                "showers": 0.0,
                "weather_code": 1,
            })
    return pd.DataFrame(rows)


def _make_sun_events(target_date: date) -> SunEvents:
    """创建太阳事件"""
    return SunEvents(
        sunrise=datetime(target_date.year, target_date.month, target_date.day, 7, 28, tzinfo=_CST),
        sunset=datetime(target_date.year, target_date.month, target_date.day, 18, 35, tzinfo=_CST),
        sunrise_azimuth=108.5,
        sunset_azimuth=251.5,
        astronomical_dawn=datetime(target_date.year, target_date.month, target_date.day, 5, 55, tzinfo=_CST),
        astronomical_dusk=datetime(target_date.year, target_date.month, target_date.day, 19, 55, tzinfo=_CST),
    )


def _make_moon_status(target_date: date) -> MoonStatus:
    return MoonStatus(
        phase=35,
        elevation=-22.5,
        moonrise=datetime(target_date.year, target_date.month, target_date.day, 3, 15, tzinfo=_CST),
        moonset=datetime(target_date.year, target_date.month, target_date.day, 13, 40, tzinfo=_CST),
    )


def _make_stargazing_window(target_date: date) -> StargazingWindow:
    next_day = target_date + timedelta(days=1)
    return StargazingWindow(
        optimal_start=datetime(target_date.year, target_date.month, target_date.day, 19, 55, tzinfo=_CST),
        optimal_end=datetime(next_day.year, next_day.month, next_day.day, 3, 15, tzinfo=_CST),
        good_start=datetime(next_day.year, next_day.month, next_day.day, 3, 15, tzinfo=_CST),
        good_end=datetime(next_day.year, next_day.month, next_day.day, 5, 55, tzinfo=_CST),
        quality="optimal",
    )


def _make_l1_plugin(event_type: str = "cloud_sea", score: int = 80) -> MagicMock:
    """创建一个仅需 L1 数据的 Mock Plugin"""
    plugin = MagicMock()
    plugin.event_type = event_type
    plugin.display_name = "云海"
    plugin.data_requirement = DataRequirement(
        needs_l2_target=False,
        needs_l2_light_path=False,
        needs_astro=False,
        past_hours=0,
    )
    result = ScoreResult(
        event_type=event_type,
        total_score=score,
        status="Recommended",
        breakdown={"test": {"score": score, "max": 100}},
        time_window="06:00-09:00",
    )
    plugin.score.return_value = result
    plugin.dimensions.return_value = ["test"]
    return plugin


def _make_l2_plugin(event_type: str = "sunrise_golden_mountain") -> MagicMock:
    """创建一个需要 L2 + Astro 数据的 Mock Plugin"""
    plugin = MagicMock()
    plugin.event_type = event_type
    plugin.display_name = "日出金山"
    plugin.data_requirement = DataRequirement(
        needs_l2_target=True,
        needs_l2_light_path=True,
        needs_astro=True,
        past_hours=0,
    )
    result = ScoreResult(
        event_type=event_type,
        total_score=90,
        status="Recommended",
        breakdown={"light_path": {"score": 35, "max": 35}},
        time_window="07:15-07:45",
    )
    plugin.score.return_value = result
    plugin.dimensions.return_value = ["light_path", "target_visible", "local_clear"]
    return plugin


def _build_scheduler(
    *,
    viewpoint: Viewpoint | None = None,
    plugins: list | None = None,
    fetch_hourly_return: pd.DataFrame | None = None,
    fetch_multi_points_return: dict | None = None,
    fetch_hourly_side_effect=None,
):
    """构建 GMPScheduler 及其 mock 依赖"""
    from gmp.core.scheduler import GMPScheduler

    # ConfigManager mock
    config = MagicMock(spec=ConfigManager)
    config.config = EngineConfig()
    config.get_light_path_config.return_value = {"count": 10, "interval_km": 10.0}
    config.get_confidence_config.return_value = {"high": [1, 2], "medium": [3, 4], "low": [5, 16]}

    # ViewpointConfig mock
    vp = viewpoint or _make_viewpoint()
    viewpoint_config = MagicMock(spec=ViewpointConfig)
    viewpoint_config.get.return_value = vp

    # RouteConfig mock
    route_config = MagicMock(spec=RouteConfig)

    # MeteoFetcher mock
    fetcher = MagicMock()
    if fetch_hourly_side_effect is not None:
        fetcher.fetch_hourly.side_effect = fetch_hourly_side_effect
    else:
        fetcher.fetch_hourly.return_value = (
            fetch_hourly_return if fetch_hourly_return is not None
            else _make_clear_weather(days=7)
        )
    fetcher.fetch_multi_points.return_value = (
        fetch_multi_points_return if fetch_multi_points_return is not None
        else {}
    )

    # ScoreEngine — 使用真实注册
    score_engine = ScoreEngine()
    for p in (plugins or []):
        score_engine.register(p)

    # AstroUtils mock
    astro = MagicMock()
    today = date.today()
    astro.get_sun_events.return_value = _make_sun_events(today)
    astro.get_moon_status.return_value = _make_moon_status(today)
    astro.determine_stargazing_window.return_value = _make_stargazing_window(today)

    # GeoUtils mock
    geo = MagicMock()
    geo.calculate_light_path_points.return_value = [
        (29.8, 102.4), (29.85, 102.45), (29.9, 102.5),
    ]
    geo.calculate_bearing.return_value = 245.0
    geo.is_opposite_direction.return_value = True

    scheduler = GMPScheduler(
        config=config,
        viewpoint_config=viewpoint_config,
        route_config=route_config,
        fetcher=fetcher,
        score_engine=score_engine,
        astro=astro,
        geo=geo,
    )

    return scheduler, fetcher, viewpoint_config, route_config, astro, geo


# ══════════════════════════════════════════════════════
# Task 1: run() 单站预测
# ══════════════════════════════════════════════════════


class TestRunHappyPath:
    """run() 正常流程"""

    def test_run_1day_returns_pipeline_result_with_events(self):
        """运行 1 天 → PipelineResult 包含 forecast_days 和 events"""
        plugin = _make_l1_plugin("cloud_sea", score=85)
        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=1),
        )

        result = scheduler.run("test_vp", days=1)

        assert isinstance(result, PipelineResult)
        assert len(result.forecast_days) == 1
        assert result.forecast_days[0].events  # 至少有一个事件

    def test_run_7days_returns_7_forecast_days(self):
        """运行 7 天 → forecast_days 长度 7"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=7),
        )

        result = scheduler.run("test_vp", days=7)

        assert len(result.forecast_days) == 7

    def test_run_calls_plugin_score(self):
        """确认 Plugin.score() 被调用"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=1),
        )

        scheduler.run("test_vp", days=1)

        plugin.score.assert_called()

    def test_run_result_contains_meta(self):
        """PipelineResult 的 meta 字段包含 generated_at 等信息"""
        plugin = _make_l1_plugin()
        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=1),
        )

        result = scheduler.run("test_vp", days=1)

        assert "generated_at" in result.meta
        assert "data_freshness" in result.meta


class TestRunEventsFilter:
    """events 过滤测试"""

    def test_events_filter_l1_only_no_l2_fetch(self):
        """events=[\"cloud_sea\", \"frost\"] → 不触发 fetch_multi_points"""
        l1 = _make_l1_plugin("cloud_sea")
        l2 = _make_l2_plugin("sunrise_golden_mountain")
        scheduler, fetcher, *_ = _build_scheduler(
            viewpoint=_make_viewpoint_with_targets(),
            plugins=[l1, l2],
            fetch_hourly_return=_make_clear_weather(days=1),
        )

        scheduler.run("test_vp", days=1, events=["cloud_sea"])

        fetcher.fetch_multi_points.assert_not_called()

    def test_events_filter_l2_triggers_fetch(self):
        """events=[\"sunrise_golden_mountain\"] → 触发 fetch_multi_points"""
        l2 = _make_l2_plugin("sunrise_golden_mountain")
        scheduler, fetcher, *_ = _build_scheduler(
            viewpoint=_make_viewpoint_with_targets(),
            plugins=[l2],
            fetch_hourly_return=_make_clear_weather(days=1),
            fetch_multi_points_return={
                (29.58, 101.88): _make_clear_weather(days=1),
                (29.8, 102.4): _make_clear_weather(days=1),
            },
        )

        scheduler.run("test_vp", days=1, events=["sunrise_golden_mountain"])

        fetcher.fetch_multi_points.assert_called()


class TestRunDegradation:
    """降级测试 — 降级处理在 Fetcher 层完成，Scheduler 层验证结果正确性"""

    def test_fetcher_returns_data_produces_valid_result(self):
        """Fetcher 正常返回数据（含 stale cache 场景）→ Scheduler 产出有效结果"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=7),
        )

        result = scheduler.run("test_vp", days=7)

        assert isinstance(result, PipelineResult)
        assert len(result.forecast_days) == 7

    def test_no_cache_raises_service_unavailable(self):
        """MockFetcher 超时且无缓存 → ServiceUnavailableError"""
        plugin = _make_l1_plugin("cloud_sea")

        def side_effect(*args, **kwargs):
            raise APITimeoutError("open-meteo", 15)

        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_side_effect=side_effect,
        )

        with pytest.raises((APITimeoutError, ServiceUnavailableError)):
            scheduler.run("test_vp", days=1)


class TestRunOnDemandFetch:
    """数据按需获取测试"""

    def test_l1_only_no_multi_fetch(self):
        """仅 L1 Plugin 活跃 → fetch_multi_points 调用次数=0"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, fetcher, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=1),
        )

        scheduler.run("test_vp", days=1)

        fetcher.fetch_multi_points.assert_not_called()

    def test_golden_mountain_triggers_multi_fetch(self):
        """有 GoldenMountain → fetch_multi_points 被调用"""
        l2 = _make_l2_plugin("sunrise_golden_mountain")
        scheduler, fetcher, *_ = _build_scheduler(
            viewpoint=_make_viewpoint_with_targets(),
            plugins=[l2],
            fetch_hourly_return=_make_clear_weather(days=1),
            fetch_multi_points_return={
                (29.58, 101.88): _make_clear_weather(days=1),
            },
        )

        scheduler.run("test_vp", days=1)

        fetcher.fetch_multi_points.assert_called()

    def test_only_sunrise_fetches_sunrise_azimuth(self):
        """仅 sunrise Plugin 活跃 → 只获取 sunrise 方向光路"""
        sunrise_plugin = _make_l2_plugin("sunrise_golden_mountain")
        scheduler, fetcher, *_, astro, geo = _build_scheduler(
            viewpoint=_make_viewpoint_with_targets(),
            plugins=[sunrise_plugin],
            fetch_hourly_return=_make_clear_weather(days=1),
            fetch_multi_points_return={
                (29.58, 101.88): _make_clear_weather(days=1),
                (29.8, 102.4): _make_clear_weather(days=1),
            },
        )

        scheduler.run("test_vp", days=1)

        # geo.calculate_light_path_points 应该用 sunrise_azimuth(108.5) 被调用
        light_path_calls = geo.calculate_light_path_points.call_args_list
        azimuths = [call.kwargs.get("azimuth", call.args[2] if len(call.args) > 2 else None)
                    for call in light_path_calls]
        assert 108.5 in azimuths
        assert 251.5 not in azimuths  # sunset_azimuth 不应被使用


class TestRunMultiDayResilience:
    """多天循环容错"""

    def test_single_day_failure_others_succeed(self):
        """7 天预测中若某天 Plugin 评分异常 → 其他天正常"""
        call_count = 0

        def score_with_failure(context):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # 第 3 天异常
                raise ValueError("Plugin 内部错误")
            return ScoreResult(
                event_type="cloud_sea",
                total_score=80,
                status="Recommended",
                breakdown={"test": {"score": 80, "max": 100}},
                time_window="06:00-09:00",
            )

        plugin = _make_l1_plugin("cloud_sea")
        plugin.score.side_effect = score_with_failure

        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=7),
        )

        result = scheduler.run("test_vp", days=7)

        # 应该有 7 天的预测结果（第 3 天的 plugin 失败但不影响整体）
        assert len(result.forecast_days) == 7


# ══════════════════════════════════════════════════════
# Task 2: run_route() 线路预测
# ══════════════════════════════════════════════════════


class TestRunRoute:
    """run_route() 线路预测"""

    def test_route_with_2_stops_calls_run_twice(self):
        """线路有 2 个站 → 调用 run() 2 次 → 返回 2 个 PipelineResult"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, fetcher, vp_config, route_config, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=1),
        )

        # 设置线路
        route = Route(
            id="test_route",
            name="测试线路",
            stops=[
                RouteStop(viewpoint_id="vp_a", order=1),
                RouteStop(viewpoint_id="vp_b", order=2),
            ],
        )
        route_config.get.return_value = route

        # 每次 run() 返回不同的 viewpoint
        vp_a = _make_viewpoint(vp_id="vp_a")
        vp_b = _make_viewpoint(vp_id="vp_b")
        vp_config.get.side_effect = [vp_a, vp_b]

        results = scheduler.run_route("test_route", days=1)

        assert len(results) == 2
        assert all(isinstance(r, PipelineResult) for r in results)

    def test_single_stop_failure_continues(self):
        """单站失败 → 跳过, 继续其余站, 记录 warning"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, fetcher, vp_config, route_config, *_ = _build_scheduler(
            plugins=[plugin],
            fetch_hourly_return=_make_clear_weather(days=1),
        )

        route = Route(
            id="test_route",
            name="测试线路",
            stops=[
                RouteStop(viewpoint_id="vp_a", order=1),
                RouteStop(viewpoint_id="vp_b", order=2),
                RouteStop(viewpoint_id="vp_c", order=3),
            ],
        )
        route_config.get.return_value = route

        # vp_b 获取失败
        call_count = 0
        def get_side_effect(vp_id):
            nonlocal call_count
            call_count += 1
            if vp_id == "vp_b":
                raise ViewpointNotFoundError("vp_b")
            return _make_viewpoint(vp_id=vp_id)

        vp_config.get.side_effect = get_side_effect

        results = scheduler.run_route("test_route", days=1)

        # vp_b 失败跳过，只有 vp_a 和 vp_c 成功
        assert len(results) == 2

    def test_route_not_found_raises(self):
        """线路不存在 → RouteNotFoundError"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, _, _, route_config, *_ = _build_scheduler(
            plugins=[plugin],
        )

        route_config.get.side_effect = RouteNotFoundError("nonexistent")

        with pytest.raises(RouteNotFoundError):
            scheduler.run_route("nonexistent", days=1)


# ══════════════════════════════════════════════════════
# Task 3: run_with_data() 数据注入接口
# ══════════════════════════════════════════════════════


class TestRunWithData:
    """run_with_data() 数据注入接口"""

    def test_run_with_data_returns_pipeline_result(self):
        """传入 weather_data → 正常评分返回 PipelineResult"""
        plugin = _make_l1_plugin("cloud_sea", score=85)
        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
        )

        weather_data = {
            (29.75, 102.35): _make_clear_weather(days=1),
        }

        result = scheduler.run_with_data(
            viewpoint_id="test_vp",
            weather_data=weather_data,
            target_date=date.today(),
        )

        assert isinstance(result, PipelineResult)
        assert len(result.forecast_days) == 1

    def test_run_with_data_does_not_call_fetcher(self):
        """run_with_data 不调用 fetcher"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, fetcher, *_ = _build_scheduler(
            plugins=[plugin],
        )

        weather_data = {
            (29.75, 102.35): _make_clear_weather(days=1),
        }

        scheduler.run_with_data(
            viewpoint_id="test_vp",
            weather_data=weather_data,
            target_date=date.today(),
        )

        fetcher.fetch_hourly.assert_not_called()
        fetcher.fetch_multi_points.assert_not_called()

    def test_run_with_data_missing_coord_graceful(self):
        """weather_data 中缺少某坐标 → 仍返回结果（空天气数据 → 无事件）"""
        plugin = _make_l1_plugin("cloud_sea")
        scheduler, *_ = _build_scheduler(
            plugins=[plugin],
        )

        # 传入空的 weather_data
        weather_data: dict[tuple[float, float], pd.DataFrame] = {}

        result = scheduler.run_with_data(
            viewpoint_id="test_vp",
            weather_data=weather_data,
            target_date=date.today(),
        )

        assert isinstance(result, PipelineResult)
        assert len(result.forecast_days) == 1

    def test_run_with_data_events_filter(self):
        """run_with_data 支持 events 过滤"""
        l1 = _make_l1_plugin("cloud_sea")
        l2 = _make_l2_plugin("sunrise_golden_mountain")
        scheduler, *_ = _build_scheduler(
            viewpoint=_make_viewpoint_with_targets(),
            plugins=[l1, l2],
        )

        weather_data = {
            (29.75, 102.35): _make_clear_weather(days=1),
        }

        result = scheduler.run_with_data(
            viewpoint_id="test_vp",
            weather_data=weather_data,
            target_date=date.today(),
            events=["cloud_sea"],
        )

        # 只有 cloud_sea 的事件
        for day in result.forecast_days:
            for event in day.events:
                assert event.event_type == "cloud_sea"

