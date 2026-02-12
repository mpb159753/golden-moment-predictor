"""共享测试 Fixture — Module 09 API/E2E 测试公共代码

使用真实组件替代 MagicMock，只在外部边界 (AstroUtils) 使用 mock。
MeteoFetcher 使用 MockMeteoFetcher 提供预制天气数据，
Scheduler、Analyzer、ScoreEngine 等全部使用真实实例。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

from gmp.api.routes import create_app
from gmp.astro.astro_utils import AstroUtils
from gmp.core.config_loader import EngineConfig, ViewpointConfig
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
from gmp.fetcher.mock_fetcher import MockMeteoFetcher
from gmp.scorer.engine import ScoreEngine, create_default_engine

# UTC+8
CST = timezone(timedelta(hours=8))


class SimplePlugin:
    """最小化 mock Plugin — 用于集成/E2E 测试"""

    def __init__(self, event_type: str, display_name: str = "",
                 score_value: int = 80):
        self.event_type = event_type
        self.display_name = display_name or event_type
        self.data_requirement = DataRequirement()
        self._score_value = score_value

    def check_trigger(self, l1_data: dict) -> bool:
        return True

    def score(self, context) -> ScoreResult:
        return ScoreResult(
            total_score=self._score_value,
            status="Recommended" if self._score_value >= 80 else "Possible",
            breakdown={
                "main": {"score": self._score_value, "max": 100,
                         "detail": "测试维度"},
            },
        )


def make_viewpoint() -> Viewpoint:
    """创建标准测试观景台"""
    return Viewpoint(
        id="niubei_gongga",
        name="牛背山",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["sunrise", "sunset", "stargazing", "cloud_sea", "frost",
                       "snow_tree", "ice_icicle"],
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


def make_clear_weather(target_date: date, hours: int = 24) -> pd.DataFrame:
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


def make_sun_events(target_date: date) -> SunEvents:
    """创建标准测试太阳事件"""
    d = target_date
    return SunEvents(
        sunrise=datetime(d.year, d.month, d.day, 7, 15, tzinfo=CST),
        sunset=datetime(d.year, d.month, d.day, 18, 30, tzinfo=CST),
        sunrise_azimuth=108.5,
        sunset_azimuth=251.5,
        astronomical_dawn=datetime(d.year, d.month, d.day, 5, 40, tzinfo=CST),
        astronomical_dusk=datetime(d.year, d.month, d.day, 20, 5, tzinfo=CST),
    )


def make_viewpoint_config(viewpoint: Viewpoint | None = None) -> ViewpointConfig:
    """创建标准测试用 ViewpointConfig (使用真实实例 + 手动注入)"""
    vp = viewpoint or make_viewpoint()
    vp_config = ViewpointConfig()
    # 手动注入观景台数据到内部存储
    vp_config._viewpoints = {vp.id: vp}
    return vp_config


def make_mock_astro() -> MagicMock:
    """创建 AstroUtils mock (唯一需要 mock 的外部依赖: 天文计算精度随日期变化)"""
    astro = MagicMock(spec=AstroUtils)
    se = make_sun_events(date.today() + timedelta(days=1))
    astro.get_sun_events.return_value = se
    astro.get_moon_status.return_value = MoonStatus(phase=15, elevation=-10.0)
    astro.determine_stargazing_window.return_value = StargazingWindow(
        good_start=se.astronomical_dusk,
        good_end=se.astronomical_dawn,
        quality="good",
    )
    return astro


def build_mock_scheduler(
    viewpoint: Viewpoint | None = None,
    plugins: list | None = None,
    scenario: str = "clear",
) -> GMPScheduler:
    """构建使用真实组件的 Scheduler (仅 AstroUtils mock)"""
    config = EngineConfig()
    vp = viewpoint or make_viewpoint()
    vp_config = make_viewpoint_config(vp)

    # 使用 MockMeteoFetcher 代替 MagicMock
    fetcher = MockMeteoFetcher(scenario=scenario)

    astro = make_mock_astro()

    engine = ScoreEngine()
    if plugins is None:
        plugins = [
            SimplePlugin("cloud_sea", "云海", 85),
            SimplePlugin("frost", "雾凇", 70),
        ]
    for p in plugins:
        engine.register(p)

    return GMPScheduler(
        config=config,
        viewpoint_config=vp_config,
        fetcher=fetcher,
        astro=astro,
        score_engine=engine,
    )


def create_test_client(scheduler=None) -> TestClient:
    """创建测试用 TestClient (使用真实组件)"""
    vp_config = make_viewpoint_config()

    if scheduler is None:
        scheduler = build_mock_scheduler()

    app = create_app(
        config=EngineConfig(),
        viewpoint_config=vp_config,
        scheduler=scheduler,
    )
    return TestClient(app)
