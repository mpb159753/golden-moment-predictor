"""tests/integration/test_pipeline.py — GMPScheduler 集成测试

验证端到端管线: 使用 Mock Fetcher + 真实 ScoreEngine + 真实 Plugin。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from gmp.core.config_loader import ConfigManager, EngineConfig, ViewpointConfig, RouteConfig
from gmp.core.models import (
    Location,
    MoonStatus,
    PipelineResult,
    Route,
    RouteStop,
    StargazingWindow,
    SunEvents,
    Target,
    Viewpoint,
)
from gmp.core.scheduler import GMPScheduler
from gmp.scoring.engine import ScoreEngine
from gmp.scoring.models import DataRequirement

_CST = timezone(timedelta(hours=8))


# ── Test Helpers ─────────────────────────────────────


def _make_viewpoint() -> Viewpoint:
    return Viewpoint(
        id="niubei_test",
        name="牛背山 (集成测试)",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["cloud_sea", "frost"],
        targets=[],
    )


def _make_viewpoint_with_targets() -> Viewpoint:
    return Viewpoint(
        id="niubei_test",
        name="牛背山 (集成测试)",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["cloud_sea", "frost", "sunrise"],
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


def _make_clear_weather_df(days: int = 1, base_date: date | None = None) -> pd.DataFrame:
    """生成逐小时天气 — 与 MeteoFetcher 输出格式一致"""
    base = base_date or date.today()
    rows = []
    for d in range(days):
        current_date = base + timedelta(days=d)
        for h in range(24):
            rows.append({
                "forecast_date": current_date.isoformat(),
                "forecast_hour": h,
                "temperature_2m": -3.0 + h * 0.5,
                "cloud_cover_total": 15,
                "cloud_cover_low": 65,
                "cloud_cover_medium": 5,
                "cloud_cover_high": 3,
                "cloud_base_altitude": 2800,
                "precipitation_probability": 0,
                "visibility": 35000,
                "wind_speed_10m": 2.5,
                "snowfall": 0.0,
                "rain": 0.0,
                "showers": 0.0,
                "weather_code": 1,
            })
    return pd.DataFrame(rows)


def _make_sun_events(target_date: date) -> SunEvents:
    return SunEvents(
        sunrise=datetime(target_date.year, target_date.month, target_date.day, 7, 28, tzinfo=_CST),
        sunset=datetime(target_date.year, target_date.month, target_date.day, 18, 35, tzinfo=_CST),
        sunrise_azimuth=108.5,
        sunset_azimuth=251.5,
        astronomical_dawn=datetime(target_date.year, target_date.month, target_date.day, 5, 55, tzinfo=_CST),
        astronomical_dusk=datetime(target_date.year, target_date.month, target_date.day, 19, 55, tzinfo=_CST),
    )


def _make_real_l1_plugin(event_type: str = "cloud_sea") -> MagicMock:
    """创建需要 L1 数据的真实 Plugin Mock"""
    from gmp.core.models import ScoreResult

    plugin = MagicMock()
    plugin.event_type = event_type
    plugin.display_name = "云海"
    plugin.data_requirement = DataRequirement(
        needs_l2_target=False,
        needs_l2_light_path=False,
        needs_astro=False,
        past_hours=0,
    )

    def _score(ctx):
        # 简单评分逻辑: 低云覆盖 >= 50% → 推荐
        weather = ctx.local_weather
        avg_low_cloud = weather["cloud_cover_low"].mean()
        score = min(100, int(avg_low_cloud * 1.2))
        if score >= 80:
            status = "Recommended"
        elif score >= 50:
            status = "Possible"
        else:
            return None
        return ScoreResult(
            event_type=event_type,
            total_score=score,
            status=status,
            breakdown={"cloud": {"score": score, "max": 100}},
            time_window="06:00-09:00",
        )

    plugin.score.side_effect = _score
    plugin.dimensions.return_value = ["cloud"]
    return plugin


def _build_integration_scheduler(
    *,
    viewpoint: Viewpoint | None = None,
    plugins: list | None = None,
    weather_data: pd.DataFrame | None = None,
):
    """构建集成测试用的 Scheduler"""
    config = MagicMock(spec=ConfigManager)
    config.config = EngineConfig()
    config.get_light_path_config.return_value = {"count": 10, "interval_km": 10.0}
    config.get_confidence_config.return_value = {"high": [1, 2], "medium": [3, 4], "low": [5, 16]}

    vp = viewpoint or _make_viewpoint()
    viewpoint_config = MagicMock(spec=ViewpointConfig)
    viewpoint_config.get.return_value = vp

    route_config = MagicMock(spec=RouteConfig)

    fetcher = MagicMock()
    fetcher.fetch_hourly.return_value = (
        weather_data if weather_data is not None
        else _make_clear_weather_df(days=7)
    )
    fetcher.fetch_multi_points.return_value = {}

    score_engine = ScoreEngine()
    for p in (plugins or []):
        score_engine.register(p)

    astro = MagicMock()
    today = date.today()
    astro.get_sun_events.return_value = _make_sun_events(today)
    astro.get_moon_status.return_value = MoonStatus(
        phase=35, elevation=-22.5,
        moonrise=datetime(today.year, today.month, today.day, 3, 15, tzinfo=_CST),
        moonset=datetime(today.year, today.month, today.day, 13, 40, tzinfo=_CST),
    )
    astro.determine_stargazing_window.return_value = StargazingWindow(
        optimal_start=datetime(today.year, today.month, today.day, 19, 55, tzinfo=_CST),
        optimal_end=datetime(today.year, today.month, today.day + 1 if today.day < 28 else 1, 3, 15, tzinfo=_CST),
        good_start=datetime(today.year, today.month, today.day + 1 if today.day < 28 else 1, 3, 15, tzinfo=_CST),
        good_end=datetime(today.year, today.month, today.day + 1 if today.day < 28 else 1, 5, 55, tzinfo=_CST),
        quality="optimal",
    )

    geo = MagicMock()
    geo.calculate_light_path_points.return_value = [(29.8, 102.4)]
    geo.calculate_bearing.return_value = 245.0

    scheduler = GMPScheduler(
        config=config,
        viewpoint_config=viewpoint_config,
        route_config=route_config,
        fetcher=fetcher,
        score_engine=score_engine,
        astro=astro,
        geo=geo,
    )
    return scheduler, fetcher, viewpoint_config, route_config


# ── 集成测试 ─────────────────────────────────────────


class TestPipelineEndToEnd:
    """端到端管线测试"""

    def test_full_pipeline_7days(self):
        """7 天完整管线: Mock Fetcher + Score Plugin → PipelineResult"""
        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, *_ = _build_integration_scheduler(
            plugins=[plugin],
            weather_data=_make_clear_weather_df(days=7),
        )

        result = scheduler.run("niubei_test", days=7)

        # 基本结构验证
        assert isinstance(result, PipelineResult)
        assert len(result.forecast_days) == 7

        # 每天应该都有评分结果 (天气条件好)
        for day in result.forecast_days:
            assert day.date  # 日期非空
            assert day.summary  # 摘要非空
            assert day.confidence in ("High", "Medium", "Low")

    def test_full_pipeline_has_events_with_good_weather(self):
        """好天气条件 → 每天都有 events"""
        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, *_ = _build_integration_scheduler(
            plugins=[plugin],
            weather_data=_make_clear_weather_df(days=3),
        )

        result = scheduler.run("niubei_test", days=3)

        events_count = sum(len(d.events) for d in result.forecast_days)
        assert events_count >= 3  # 至少每天一个事件

    def test_pipeline_meta_fields(self):
        """验证 meta 字段结构"""
        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, *_ = _build_integration_scheduler(
            plugins=[plugin],
            weather_data=_make_clear_weather_df(days=1),
        )

        result = scheduler.run("niubei_test", days=1)

        assert "generated_at" in result.meta
        assert "data_freshness" in result.meta


class TestPipelineRoute:
    """线路集成测试"""

    def test_route_2_stops_full_pipeline(self):
        """线路 2 站 → 各站独立评分"""
        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, fetcher, vp_config, route_config = _build_integration_scheduler(
            plugins=[plugin],
            weather_data=_make_clear_weather_df(days=3),
        )

        vp_a = _make_viewpoint()
        vp_b = Viewpoint(
            id="vp_b",
            name="折多山",
            location=Location(lat=30.05, lon=101.78, altitude=4298),
            capabilities=["cloud_sea"],
            targets=[],
        )
        vp_config.get.side_effect = [vp_a, vp_b]

        route = Route(
            id="test_route",
            name="测试线路",
            stops=[
                RouteStop(viewpoint_id="niubei_test", order=1),
                RouteStop(viewpoint_id="vp_b", order=2),
            ],
        )
        route_config.get.return_value = route

        results = scheduler.run_route("test_route", days=3)

        assert len(results) == 2
        for r in results:
            assert isinstance(r, PipelineResult)
            assert len(r.forecast_days) == 3


class TestPipelineRunWithData:
    """run_with_data 集成测试"""

    def test_run_with_data_produces_results(self):
        """注入历史数据 → 产出评分结果"""
        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, *_ = _build_integration_scheduler(plugins=[plugin])

        target_date = date.today() - timedelta(days=30)
        weather_data = {
            (29.75, 102.35): _make_clear_weather_df(days=1, base_date=target_date),
        }

        result = scheduler.run_with_data(
            viewpoint_id="niubei_test",
            weather_data=weather_data,
            target_date=target_date,
        )

        assert isinstance(result, PipelineResult)
        assert len(result.forecast_days) == 1
        assert result.meta["mode"] == "backtest"
        assert result.meta["data_freshness"] == "archive"

    def test_run_with_data_fetcher_not_called(self):
        """run_with_data 不使用 fetcher"""
        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, fetcher, *_ = _build_integration_scheduler(plugins=[plugin])

        target_date = date.today() - timedelta(days=30)
        weather_data = {
            (29.75, 102.35): _make_clear_weather_df(days=1, base_date=target_date),
        }

        scheduler.run_with_data(
            viewpoint_id="niubei_test",
            weather_data=weather_data,
            target_date=target_date,
        )

        fetcher.fetch_hourly.assert_not_called()
        fetcher.fetch_multi_points.assert_not_called()


# ── 多 Plugin 协同评分 ──────────────────────────────────


def _load_engine_config() -> dict:
    """从 engine_config.yaml 加载配置"""
    import yaml
    from pathlib import Path
    config_path = Path(__file__).resolve().parents[2] / "config" / "engine_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def _make_real_plugin_weather_df(days: int = 1, base_date: date | None = None) -> pd.DataFrame:
    """生成兼容真实 Plugin 的天气 DataFrame — 列名与 MeteoFetcher 输出一致。"""
    base = base_date or date.today()
    rows = []
    for d in range(days):
        current_date = base + timedelta(days=d)
        for h in range(24):
            rows.append({
                "forecast_date": current_date.isoformat(),
                "forecast_hour": h,
                "temperature_2m": -3.0,  # 低温 → 触发 FrostPlugin
                "cloud_cover_total": 15,
                "cloud_cover_low": 65,
                "cloud_cover_medium": 5,
                "cloud_cover_high": 3,
                "cloud_base_altitude": 2800,  # 低于站点(3660m) → 触发 CloudSea
                "precipitation_probability": 0,
                "visibility": 35000,
                "wind_speed_10m": 2.0,
                "snowfall": 0.0,
                "rain": 0.0,
                "showers": 0.0,
                "weather_code": 1,
            })
    return pd.DataFrame(rows)


class TestMultiPluginCoordination:
    """多 Plugin 协同评分 — 使用真实 Plugin 实现"""

    def test_cloud_sea_and_frost_both_produce_scores(self):
        """CloudSeaPlugin + FrostPlugin 在低温晴天同时触发"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin
        from gmp.scoring.plugins.frost import FrostPlugin

        raw_config = _load_engine_config()
        cloud_sea_plugin = CloudSeaPlugin(
            config=raw_config["scoring"]["cloud_sea"],
            safety_config=raw_config["safety"],
        )
        frost_plugin = FrostPlugin(config=raw_config["scoring"]["frost"])

        weather = _make_real_plugin_weather_df(days=3)
        scheduler, *_ = _build_integration_scheduler(
            plugins=[cloud_sea_plugin, frost_plugin],
            weather_data=weather,
        )

        result = scheduler.run("niubei_test", days=3)

        assert isinstance(result, PipelineResult)
        assert len(result.forecast_days) == 3

        # 每天应有 2 个事件 (cloud_sea + frost)
        for day in result.forecast_days:
            event_types = {e.event_type for e in day.events}
            assert "cloud_sea" in event_types, f"{day.date}: CloudSea 未触发"
            assert "frost" in event_types, f"{day.date}: Frost 未触发"

    def test_plugins_produce_independent_scores(self):
        """各 Plugin 独立评分，互不干扰"""
        from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin
        from gmp.scoring.plugins.frost import FrostPlugin

        raw_config = _load_engine_config()
        cloud_sea_plugin = CloudSeaPlugin(
            config=raw_config["scoring"]["cloud_sea"],
            safety_config=raw_config["safety"],
        )
        frost_plugin = FrostPlugin(config=raw_config["scoring"]["frost"])

        scheduler, *_ = _build_integration_scheduler(
            plugins=[cloud_sea_plugin, frost_plugin],
            weather_data=_make_real_plugin_weather_df(days=1),
        )

        result = scheduler.run("niubei_test", days=1)

        events = result.forecast_days[0].events
        assert len(events) == 2

        cloud_sea_result = next(e for e in events if e.event_type == "cloud_sea")
        frost_result = next(e for e in events if e.event_type == "frost")

        # 各自有独立的评分和 breakdown
        assert cloud_sea_result.total_score > 0
        assert frost_result.total_score > 0
        assert set(cloud_sea_result.breakdown.keys()) != set(frost_result.breakdown.keys())


# ── 降级场景 ──────────────────────────────────────────


class TestPipelineDegradation:
    """降级场景 — 验证 Fetcher 异常时 Scheduler 的行为"""

    def test_fetcher_timeout_propagates(self):
        """Fetcher 超时 → 异常传播到调用方"""
        from gmp.core.exceptions import APITimeoutError

        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, fetcher, *_ = _build_integration_scheduler(plugins=[plugin])

        fetcher.fetch_hourly.side_effect = APITimeoutError("open-meteo", 15)

        with pytest.raises(APITimeoutError):
            scheduler.run("niubei_test", days=1)

    def test_fetcher_generic_error_propagates(self):
        """Fetcher 通用异常 → 异常传播"""
        plugin = _make_real_l1_plugin("cloud_sea")
        scheduler, fetcher, *_ = _build_integration_scheduler(plugins=[plugin])

        fetcher.fetch_hourly.side_effect = ConnectionError("Network unreachable")

        with pytest.raises(ConnectionError):
            scheduler.run("niubei_test", days=1)

