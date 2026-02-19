"""gmp/core/scheduler.py — GMPScheduler 核心调度器

串联 Plugin 收集→数据获取→评分 的核心管线。
聚焦于单站/线路评分，批量生成由 BatchGenerator 负责。
"""

from __future__ import annotations


from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import structlog

from gmp.core.exceptions import (
    APITimeoutError,
    RouteNotFoundError,
    ServiceUnavailableError,
)
from gmp.core.models import (
    ForecastDay,
    PipelineResult,
    ScoreResult,
    days_ahead_to_confidence,
)
from gmp.output.summary_generator import SummaryGenerator
from gmp.scoring.models import DataContext, DataRequirement

if TYPE_CHECKING:
    from gmp.core.config_loader import ConfigManager, RouteConfig, ViewpointConfig
    from gmp.core.models import Viewpoint
    from gmp.data.astro_utils import AstroUtils
    from gmp.data.geo_utils import GeoUtils
    from gmp.data.meteo_fetcher import MeteoFetcher
    from gmp.scoring.engine import ScoreEngine

import pandas as pd

logger = structlog.get_logger()

_CST = timezone(timedelta(hours=8))


class GMPScheduler:
    """核心评分编排器 — 串联 Plugin 收集→数据获取→评分"""

    def __init__(
        self,
        config: ConfigManager,
        viewpoint_config: ViewpointConfig,
        route_config: RouteConfig,
        fetcher: MeteoFetcher,
        score_engine: ScoreEngine,
        astro: AstroUtils,
        geo: GeoUtils,
    ) -> None:
        self._config = config
        self._viewpoint_config = viewpoint_config
        self._route_config = route_config
        self._fetcher = fetcher
        self._score_engine = score_engine
        self._astro = astro
        self._geo = geo
        self._summary_gen = SummaryGenerator(
            mode=getattr(config.config, "summary_mode", "rule"),
            display_names=score_engine.display_names,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        viewpoint_id: str,
        days: int = 7,
        events: list[str] | None = None,
    ) -> PipelineResult:
        """单站点多日预测 — 核心主流程"""
        # 1. 获取 Viewpoint 配置
        viewpoint = self._viewpoint_config.get(viewpoint_id)

        # 2. 筛选活跃 Plugin (使用今天作为基准日期)
        today = datetime.now(_CST).date()
        active_plugins = self._score_engine.filter_active_plugins(
            capabilities=viewpoint.capabilities,
            target_date=today,
            events_filter=events,
        )

        if not active_plugins:
            return self._empty_result(viewpoint, days, today)

        # 3. 聚合数据需求
        aggregated_req = self._score_engine.collect_requirements(active_plugins)

        # 4. L1: 获取本地天气 (一次性获取 days 天)
        data_freshness = "fresh"
        local_weather = self._fetcher.fetch_hourly(
            lat=viewpoint.location.lat,
            lon=viewpoint.location.lon,
            days=days,
            past_days=1 if aggregated_req.past_hours > 0 else 0,
        )

        # 按需获取 L2 远程数据 (一次性获取 days 天)
        target_weather_all: dict[tuple[float, float], pd.DataFrame] = {}

        if aggregated_req.needs_l2_target and viewpoint.targets:
            target_coords = [(t.lat, t.lon) for t in viewpoint.targets]
            try:
                target_weather_all = self._fetcher.fetch_multi_points(
                    target_coords, days=days
                )
            except Exception:
                logger.warning("scheduler.target_weather_failed", viewpoint=viewpoint_id)

        # 按需获取 L2 光路天气 (一次性获取 days 天)
        # 用 day0 的方位角统一获取 — 7天范围内方位角变化 <1°，误差可忽略
        light_path_weather_pre: list[dict] | None = None
        if aggregated_req.needs_l2_light_path:
            day0_sun = self._astro.get_sun_events(
                viewpoint.location.lat, viewpoint.location.lon, today
            )
            light_path_weather_pre = self._fetch_light_path_weather(
                viewpoint=viewpoint,
                active_plugins=active_plugins,
                sun_events=day0_sun,
                days=days,
            )

        # 5. 逐日循环评分
        forecast_days: list[ForecastDay] = []
        for day_offset in range(days):
            target_date = today + timedelta(days=day_offset)
            days_ahead = day_offset + 1
            confidence = days_ahead_to_confidence(
                days_ahead,
                config=self._config.get_confidence_config(),
            )

            try:
                day_result = self._score_single_day(
                    viewpoint=viewpoint,
                    target_date=target_date,
                    active_plugins=active_plugins,
                    aggregated_req=aggregated_req,
                    local_weather=local_weather,
                    target_weather_all=target_weather_all,
                    light_path_weather_pre=light_path_weather_pre,
                    confidence=confidence,
                    data_freshness=data_freshness,
                )
            except Exception:
                logger.warning(
                    "scheduler.day_failed",
                    viewpoint=viewpoint_id,
                    date=str(target_date),
                    exc_info=True,
                )
                day_result = ForecastDay(
                    date=target_date.isoformat(),
                    summary="数据获取失败",
                    best_event=None,
                    events=[],
                    confidence=confidence,
                )

            forecast_days.append(day_result)

        # 6. 构建 meta
        meta = {
            "generated_at": datetime.now(_CST).isoformat(),
            "data_freshness": data_freshness,
            "hourly_weather": self._extract_hourly_weather(local_weather),
        }

        return PipelineResult(
            viewpoint=viewpoint,
            forecast_days=forecast_days,
            meta=meta,
        )

    def run_route(
        self,
        route_id: str,
        days: int = 7,
        events: list[str] | None = None,
    ) -> list[PipelineResult]:
        """线路多站预测"""
        route = self._route_config.get(route_id)

        results: list[PipelineResult] = []
        for stop in route.stops:
            try:
                result = self.run(stop.viewpoint_id, days=days, events=events)
                results.append(result)
            except Exception:
                logger.warning(
                    "scheduler.route_stop_failed",
                    route=route_id,
                    viewpoint=stop.viewpoint_id,
                    exc_info=True,
                )
                continue

        return results

    def run_with_data(
        self,
        viewpoint_id: str,
        weather_data: dict[tuple[float, float], pd.DataFrame],
        target_date: date,
        events: list[str] | None = None,
    ) -> PipelineResult:
        """数据注入接口 — 回测用，不调用 fetcher，使用传入的天气数据。

        Args:
            viewpoint_id: 观景台 ID
            weather_data: 预获取的天气数据 {(lat, lon): DataFrame}
            target_date: 目标日期
            events: 事件过滤
        """
        import pandas as pd

        viewpoint = self._viewpoint_config.get(viewpoint_id)

        # 筛选活跃 Plugin
        active_plugins = self._score_engine.filter_active_plugins(
            capabilities=viewpoint.capabilities,
            target_date=target_date,
            events_filter=events,
        )

        if not active_plugins:
            return self._empty_result(viewpoint, 1, target_date)

        aggregated_req = self._score_engine.collect_requirements(active_plugins)

        # 从 weather_data 中提取本地天气
        local_key = (
            round(viewpoint.location.lat, 2),
            round(viewpoint.location.lon, 2),
        )
        local_weather = weather_data.get(local_key, pd.DataFrame())

        # 提取目标天气
        target_weather_all: dict[tuple[float, float], pd.DataFrame] = {}
        if aggregated_req.needs_l2_target and viewpoint.targets:
            for target in viewpoint.targets:
                tkey = (round(target.lat, 2), round(target.lon, 2))
                if tkey in weather_data:
                    target_weather_all[tkey] = weather_data[tkey]

        # 使用 _score_single_day 评分
        confidence = days_ahead_to_confidence(
            0,  # 回测 → days_ahead=0
            config=self._config.get_confidence_config(),
        )

        try:
            day_result = self._score_single_day(
                viewpoint=viewpoint,
                target_date=target_date,
                active_plugins=active_plugins,
                aggregated_req=aggregated_req,
                local_weather=local_weather,
                target_weather_all=target_weather_all,
                confidence=confidence,
                data_freshness="archive",
            )
        except Exception:
            logger.warning(
                "scheduler.run_with_data_failed",
                viewpoint=viewpoint_id,
                date=str(target_date),
                exc_info=True,
            )
            day_result = ForecastDay(
                date=target_date.isoformat(),
                summary="数据处理失败",
                best_event=None,
                events=[],
                confidence=confidence,
            )

        meta = {
            "generated_at": datetime.now(_CST).isoformat(),
            "data_freshness": "archive",
            "mode": "backtest",
        }

        return PipelineResult(
            viewpoint=viewpoint,
            forecast_days=[day_result],
            meta=meta,
        )


    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _score_single_day(
        self,
        *,
        viewpoint: Viewpoint,
        target_date: date,
        active_plugins: list,
        aggregated_req: DataRequirement,
        local_weather: pd.DataFrame,
        target_weather_all: dict[tuple[float, float], pd.DataFrame],
        light_path_weather_pre: list[dict] | None = None,
        confidence: str,
        data_freshness: str,
    ) -> ForecastDay:
        """评分单日 — 构建 DataContext 并遍历 Plugin"""
        # 切片当天本地天气 (forecast_date 为字符串，需转换 target_date)
        target_date_str = target_date.isoformat()
        day_weather = local_weather[
            local_weather["forecast_date"] == target_date_str
        ].copy()
        if day_weather.empty:
            return ForecastDay(
                date=target_date.isoformat(),
                summary="无可用天气数据",
                best_event=None,
                events=[],
                confidence=confidence,
            )

        # 天文数据 (按需)
        sun_events = None
        moon_status = None
        stargazing_window = None
        if aggregated_req.needs_astro:
            sun_events = self._astro.get_sun_events(
                viewpoint.location.lat,
                viewpoint.location.lon,
                target_date,
            )
            moon_status = self._astro.get_moon_status(
                viewpoint.location.lat,
                viewpoint.location.lon,
                sun_events.sunset,
            )
            stargazing_window = self._astro.determine_stargazing_window(
                sun_events, moon_status
            )

        # L2 光路天气 — 使用循环外预获取的数据
        light_path_weather = light_path_weather_pre

        # L2 目标天气 — 切片当天
        target_weather: dict[str, pd.DataFrame] | None = None
        if aggregated_req.needs_l2_target and viewpoint.targets:
            target_weather = {}
            for target in viewpoint.targets:
                key = (round(target.lat, 2), round(target.lon, 2))
                if key in target_weather_all:
                    tw = target_weather_all[key]
                    day_tw = tw[tw["forecast_date"] == target_date_str].copy()
                    if not day_tw.empty:
                        target_weather[target.name] = day_tw

        # 构建 DataContext
        ctx = DataContext(
            date=target_date,
            viewpoint=viewpoint,
            local_weather=day_weather,
            sun_events=sun_events,
            moon_status=moon_status,
            stargazing_window=stargazing_window,
            target_weather=target_weather,
            light_path_weather=light_path_weather,
            data_freshness=data_freshness,
        )

        # 遍历 Plugin 评分
        events: list[ScoreResult] = []
        for plugin in active_plugins:
            try:
                result = plugin.score(ctx)
                if result is not None:
                    result.confidence = confidence
                    events.append(result)
            except Exception:
                logger.warning(
                    "scheduler.plugin_score_failed",
                    plugin=plugin.event_type,
                    date=str(target_date),
                    exc_info=True,
                )

        # 生成 summary
        summary = self._summary_gen.generate(events)
        best_event = max(events, key=lambda e: e.total_score) if events else None

        return ForecastDay(
            date=target_date.isoformat(),
            summary=summary,
            best_event=best_event,
            events=events,
            confidence=confidence,
        )

    def _fetch_light_path_weather(
        self,
        *,
        viewpoint: Viewpoint,
        active_plugins: list,
        sun_events: Any,
        days: int,
    ) -> list[dict] | None:
        """根据活跃 Plugin 判断需要哪个方向的光路"""
        from gmp.core.models import SunEvents as SunEventsType

        light_path_cfg = self._config.get_light_path_config()
        count = light_path_cfg.get("count", 10)
        interval_km = light_path_cfg.get("interval_km", 10.0)

        azimuths_to_fetch: list[float] = []
        for p in active_plugins:
            if p.event_type == "sunrise_golden_mountain":
                azimuths_to_fetch.append(sun_events.sunrise_azimuth)
            elif p.event_type == "sunset_golden_mountain":
                azimuths_to_fetch.append(sun_events.sunset_azimuth)

        if not azimuths_to_fetch:
            return None

        all_path_weather: list[dict] = []
        for azimuth in azimuths_to_fetch:
            path_points = self._geo.calculate_light_path_points(
                viewpoint.location.lat,
                viewpoint.location.lon,
                azimuth,
                count=count,
                interval_km=interval_km,
            )
            try:
                path_data = self._fetcher.fetch_multi_points(path_points, days=days)
                all_path_weather.append({
                    "azimuth": azimuth,
                    "points": path_points,
                    "weather": path_data,
                })
            except Exception:
                logger.warning(
                    "scheduler.light_path_fetch_failed",
                    azimuth=azimuth,
                    exc_info=True,
                )

        return all_path_weather if all_path_weather else None

    def _extract_hourly_weather(
        self, local_weather: pd.DataFrame
    ) -> dict[str, dict[int, dict]]:
        """从 DataFrame 提取逐时天气 → {date: {hour: {temperature, cloud_cover, weather_icon}}}

        weather_icon 映射规则:
        - cloud_cover < 20% → "clear"
        - cloud_cover < 50% → "partly_cloudy"
        - cloud_cover < 80% 且 precip_prob >= 50% 且 temp < 0 → "snow"
        - cloud_cover < 80% 且 precip_prob >= 50% → "rain"
        - 其他 → "cloudy"
        """
        if local_weather.empty:
            return {}

        import numpy as np

        cc = local_weather.get("cloud_cover_total", pd.Series(0, index=local_weather.index))
        temp = local_weather.get("temperature_2m", pd.Series(0, index=local_weather.index))
        pp = local_weather.get("precipitation_probability", pd.Series(0, index=local_weather.index))

        # 向量化 weather_icon 映射
        conditions = [
            cc < 20,
            cc < 50,
            (pp >= 50) & (temp < 0),
            pp >= 50,
        ]
        choices = ["clear", "partly_cloudy", "snow", "rain"]
        icons = np.select(conditions, choices, default="cloudy")

        result: dict[str, dict[int, dict]] = {}
        for i, (date_str, hour) in enumerate(
            zip(local_weather["forecast_date"], local_weather["forecast_hour"])
        ):
            hour_int = int(hour)
            if date_str not in result:
                result[date_str] = {}
            result[date_str][hour_int] = {
                "temperature": float(temp.iloc[i]),
                "cloud_cover": float(cc.iloc[i]),
                "weather_icon": str(icons[i]),
            }

        return result

    def _empty_result(
        self,
        viewpoint: Viewpoint,
        days: int,
        start_date: date,
    ) -> PipelineResult:
        """无活跃 Plugin 时返回空结果"""
        forecast_days = []
        for i in range(days):
            target_date = start_date + timedelta(days=i)
            forecast_days.append(
                ForecastDay(
                    date=target_date.isoformat(),
                    summary="无适用评分项",
                    best_event=None,
                    events=[],
                    confidence=days_ahead_to_confidence(
                        i + 1,
                        config=self._config.get_confidence_config(),
                    ),
                )
            )
        return PipelineResult(
            viewpoint=viewpoint,
            forecast_days=forecast_days,
            meta={
                "generated_at": datetime.now(_CST).isoformat(),
                "data_freshness": "fresh",
            },
        )
