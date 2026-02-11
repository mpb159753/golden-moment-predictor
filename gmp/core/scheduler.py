"""GMPScheduler — Plugin 驱动的主调度引擎

系统的 "大脑"，负责协调所有子系统完成一次完整的预测流程:
  1. 接收用户请求 (viewpoint_id, days, events)
  2. 收集活跃 Plugin (capabilities ∩ season ∩ events)
  3. 聚合 DataRequirement
  4. Phase 1: 获取本地天气 (一次性获取)
  5. 遍历每一天:
     a. 按需获取天文数据
     b. L1 本地滤网
     c. Plugin 触发检查
     d. Phase 2: 按需获取远程天气
     e. L2 远程滤网
     f. 构建 DataContext + Plugin 循环评分
  6. 汇总结果

设计依据:
- design/01-architecture.md §1.4, §1.5
- design/03-scoring-plugins.md §3.2
- design/04-data-flow-example.md Stage 0-5
- design/06-class-sequence.md §6.1, §6.5, §6.6
- design/08-operations.md §8.2, §8.7, §8.9
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from gmp.analyzer.local_analyzer import LocalAnalyzer
from gmp.analyzer.remote_analyzer import RemoteAnalyzer
from gmp.astro.astro_utils import AstroUtils
from gmp.astro.geo_utils import GeoUtils
from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.core.models import (
    AnalysisResult,
    DataContext,
    DataRequirement,
    ScoreResult,
    Viewpoint,
)
from gmp.core.pipeline import AnalyzerPipeline
from gmp.fetcher.meteo_fetcher import MeteoFetcher
from gmp.scorer.engine import ScoreEngine

logger = logging.getLogger(__name__)

# UTC+8 北京时间
_CST = timezone(timedelta(hours=8))

# capability → event_type 映射表
_CAPABILITY_EVENT_MAP: dict[str, list[str]] = {
    "sunrise": ["sunrise_golden_mountain"],
    "sunset": ["sunset_golden_mountain"],
    "stargazing": ["stargazing"],
    "cloud_sea": ["cloud_sea"],
    "frost": ["frost"],
    "snow_tree": ["snow_tree"],
    "ice_icicle": ["ice_icicle"],
}


class GMPScheduler:
    """主调度器 — Plugin 驱动的预测引擎"""

    def __init__(
        self,
        config: EngineConfig,
        viewpoint_config: ViewpointConfig,
        fetcher: MeteoFetcher,
        astro: AstroUtils,
        score_engine: ScoreEngine,
    ) -> None:
        self._config = config
        self._viewpoint_config = viewpoint_config
        self._fetcher = fetcher
        self._astro = astro
        self._geo = GeoUtils()
        self._local_analyzer = LocalAnalyzer(config)
        self._remote_analyzer = RemoteAnalyzer(config)
        self._score_engine = score_engine
        self._pipeline = AnalyzerPipeline(self._local_analyzer, self._remote_analyzer)

        # 统计计数器
        self._api_calls = 0
        self._cache_hits = 0

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def run(
        self,
        viewpoint_id: str,
        days: int = 7,
        events: list[str] | None = None,
    ) -> dict:
        """执行预测

        Args:
            viewpoint_id: 观景台 ID
            days: 预测天数 (1-7)
            events: 事件类型过滤列表，None=全部

        Returns:
            {
                "viewpoint": str,
                "forecast_days": [
                    {
                        "date": str,
                        "confidence": str,
                        "events": [ScoreResult, ...],
                    }, ...
                ],
                "meta": {"api_calls": int, "cache_hits": int}
            }
        """
        self._api_calls = 0
        self._cache_hits = 0

        viewpoint = self._viewpoint_config.get(viewpoint_id)
        days = max(1, min(7, days))

        # Phase 1: 一次性获取本地天气
        local_weather_all = self._fetcher.fetch_hourly(
            viewpoint.location.lat,
            viewpoint.location.lon,
            days=days,
        )
        self._api_calls += 1

        forecast_days: list[dict] = []

        for day_offset in range(days):
            target_date = date.today() + timedelta(days=day_offset + 1)
            confidence = self._determine_confidence(day_offset + 1)

            # 当天本地天气切片
            local_weather_day = self._slice_day(local_weather_all, target_date)
            if local_weather_day.empty:
                forecast_days.append({
                    "date": str(target_date),
                    "confidence": confidence,
                    "events": [],
                })
                continue

            # 收集活跃 Plugin + 聚合需求
            active_plugins = self._collect_active_plugins(
                viewpoint, events, target_date
            )
            if not active_plugins:
                forecast_days.append({
                    "date": str(target_date),
                    "confidence": confidence,
                    "events": [],
                })
                continue

            requirement = self._score_engine.collect_requirements(active_plugins)

            # L1 本地滤网
            l1_context = {
                "site_altitude": viewpoint.location.altitude,
                "target_hour": 7,  # 默认日出分析小时
                "viewpoint": viewpoint,
            }
            l1_result = self._local_analyzer.analyze(local_weather_day, l1_context)

            if not l1_result.passed:
                forecast_days.append({
                    "date": str(target_date),
                    "confidence": confidence,
                    "events": [],
                })
                continue

            # Plugin 触发检查
            triggered: list[Any] = []
            for p in active_plugins:
                try:
                    if p.check_trigger(l1_result.details):
                        triggered.append(p)
                except Exception:
                    logger.warning("Plugin %s check_trigger 异常，跳过",
                                   getattr(p, "event_type", "unknown"), exc_info=True)

            if not triggered:
                forecast_days.append({
                    "date": str(target_date),
                    "confidence": confidence,
                    "events": [],
                })
                continue

            # 构建 DataContext (按需填充天文+远程数据)
            triggered_requirement = self._score_engine.collect_requirements(triggered)
            ctx = self._build_data_context(
                viewpoint, target_date, local_weather_day, triggered_requirement
            )

            # Phase 2: 按需 L2 远程分析
            need_l2 = (
                triggered_requirement.needs_l2_target
                or triggered_requirement.needs_l2_light_path
            )
            if need_l2 and ctx.target_weather:
                l2_context = {
                    "target_weather": ctx.target_weather or {},
                    "light_path_weather": ctx.light_path_weather or [],
                    "target_hour": 7,
                    "target_weights": {
                        t.name: t.weight for t in viewpoint.targets
                    },
                }
                l2_result = self._remote_analyzer.analyze(pd.DataFrame(), l2_context)
                ctx.l2_result = l2_result

            # Plugin 循环评分 (错误隔离)
            day_events: list[dict] = []
            for p in triggered:
                try:
                    result = p.score(ctx)
                    day_events.append({
                        "event_type": getattr(p, "event_type", "unknown"),
                        "display_name": getattr(p, "display_name", ""),
                        "total_score": result.total_score,
                        "status": result.status,
                        "breakdown": result.breakdown,
                    })
                except Exception:
                    logger.error(
                        "Plugin %s 评分异常，跳过",
                        getattr(p, "event_type", "unknown"),
                        exc_info=True,
                    )

            forecast_days.append({
                "date": str(target_date),
                "confidence": confidence,
                "events": day_events,
            })

        return {
            "viewpoint": viewpoint.name,
            "forecast_days": forecast_days,
            "meta": {
                "api_calls": self._api_calls,
                "cache_hits": self._cache_hits,
            },
        }

    # ------------------------------------------------------------------
    # Plugin 收集
    # ------------------------------------------------------------------

    def _collect_active_plugins(
        self,
        viewpoint: Viewpoint,
        events_filter: list[str] | None,
        target_date: date,
    ) -> list:
        """收集活跃 Plugin

        过滤条件:
        1. plugin.event_type 对应的 capability 在 viewpoint.capabilities 中
        2. events_filter 为 None 或包含 plugin.event_type
        3. plugin.data_requirement.season_months 为 None 或包含当月
        """
        # 构建 capability → event_types 反向索引
        allowed_event_types: set[str] = set()
        for cap in viewpoint.capabilities:
            mapped = _CAPABILITY_EVENT_MAP.get(cap, [cap])
            allowed_event_types.update(mapped)

        active: list = []
        for plugin in self._score_engine.all_plugins():
            event_type = getattr(plugin, "event_type", None)
            if event_type is None:
                continue

            # 1. capability 过滤
            if event_type not in allowed_event_types:
                continue

            # 2. events 参数过滤
            if events_filter is not None and event_type not in events_filter:
                continue

            # 3. season 过滤
            req: DataRequirement = getattr(
                plugin, "data_requirement", DataRequirement()
            )
            if req.season_months is not None:
                if target_date.month not in req.season_months:
                    continue

            active.append(plugin)

        return active

    # ------------------------------------------------------------------
    # DataContext 构建
    # ------------------------------------------------------------------

    def _build_data_context(
        self,
        viewpoint: Viewpoint,
        target_date: date,
        local_weather_day: pd.DataFrame,
        requirement: DataRequirement,
    ) -> DataContext:
        """构建共享数据上下文

        根据 requirement 按需填充:
        - needs_astro → get_sun_events + get_moon_status + determine_stargazing_window
        - needs_l2_target → fetch_multi_points(targets)
        - needs_l2_light_path → calculate_light_path_points + fetch_multi_points
        """
        ctx = DataContext(
            date=target_date,
            viewpoint=viewpoint,
            local_weather=local_weather_day,
        )

        # ---- 天文数据 ----
        if requirement.needs_astro:
            try:
                sun_events = self._astro.get_sun_events(
                    viewpoint.location.lat,
                    viewpoint.location.lon,
                    target_date,
                )
                ctx.sun_events = sun_events

                # 月球状态 (日落时刻)
                moon_status = self._astro.get_moon_status(
                    viewpoint.location.lat,
                    viewpoint.location.lon,
                    sun_events.sunset,
                )
                ctx.moon_status = moon_status

                # 观星窗口
                stargazing_window = self._astro.determine_stargazing_window(
                    sun_events, moon_status
                )
                ctx.stargazing_window = stargazing_window
            except Exception:
                logger.warning("天文数据计算异常", exc_info=True)

        # 日照金山需要天文数据来确定光路方向，即使 needs_astro 为 False
        # 也需要 sun_events 来处理 target 方向匹配和光路计算
        sun_events_for_lp = ctx.sun_events
        if sun_events_for_lp is None and (
            requirement.needs_l2_target or requirement.needs_l2_light_path
        ):
            try:
                sun_events_for_lp = self._astro.get_sun_events(
                    viewpoint.location.lat,
                    viewpoint.location.lon,
                    target_date,
                )
                ctx.sun_events = sun_events_for_lp
            except Exception:
                logger.warning("获取光路用日出方位角失败", exc_info=True)

        # ---- L2 目标天气 ----
        if requirement.needs_l2_target and viewpoint.targets:
            try:
                target_coords = [
                    (t.lat, t.lon) for t in viewpoint.targets
                ]
                target_data = self._fetcher.fetch_multi_points(target_coords, days=1)
                self._api_calls += len(target_data)

                target_weather: dict[str, pd.DataFrame] = {}
                for t in viewpoint.targets:
                    key = (round(t.lat, 2), round(t.lon, 2))
                    if key in target_data:
                        target_weather[t.name] = target_data[key]
                ctx.target_weather = target_weather
            except Exception:
                logger.warning("目标天气获取失败", exc_info=True)

        # ---- L2 光路天气 ----
        if requirement.needs_l2_light_path and sun_events_for_lp is not None:
            try:
                # 使用日出方位角生成光路检查点
                azimuth = sun_events_for_lp.sunrise_azimuth
                light_path_points = self._geo.calculate_light_path_points(
                    viewpoint.location.lat,
                    viewpoint.location.lon,
                    azimuth,
                    count=self._config.light_path_count,
                    interval_km=self._config.light_path_interval_km,
                )

                # 坐标去重后批量获取
                lp_data = self._fetcher.fetch_multi_points(light_path_points, days=1)
                self._api_calls += len(lp_data)

                # 构建光路天气列表
                light_path_weather: list[dict] = []
                for i, (lat, lon) in enumerate(light_path_points):
                    key = (round(lat, 2), round(lon, 2))
                    df = lp_data.get(key, pd.DataFrame())
                    if not df.empty:
                        row = df.iloc[0]
                        light_path_weather.append({
                            "point_name": f"LP_{i + 1}",
                            "lat": lat,
                            "lon": lon,
                            "low_cloud": float(row.get("cloud_cover_low", 0)),
                            "mid_cloud": float(
                                row.get("cloud_cover_medium",
                                       row.get("cloud_cover_mid", 0))
                            ),
                            "combined": float(
                                row.get("cloud_cover_low", 0)
                            ) + float(
                                row.get("cloud_cover_medium",
                                       row.get("cloud_cover_mid", 0))
                            ),
                        })
                ctx.light_path_weather = light_path_weather
            except Exception:
                logger.warning("光路天气获取失败", exc_info=True)

        return ctx

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_confidence(days_ahead: int) -> str:
        """置信度映射: T+1~2=High, T+3~4=Medium, T+5~7=Low"""
        if days_ahead <= 2:
            return "High"
        if days_ahead <= 4:
            return "Medium"
        return "Low"

    def _match_targets_by_direction(
        self,
        viewpoint: Viewpoint,
        sun_events: Any,
    ) -> list[dict]:
        """根据方位角自动匹配 Target 适用事件

        逻辑:
        1. 计算 viewpoint → target 方位角
        2. 日出: is_opposite_direction(bearing, sunrise_azimuth) → sunrise 匹配
        3. 日落: is_opposite_direction(bearing, sunset_azimuth) → sunset 匹配
        4. 如果 target.applicable_events 不为 None，使用手动指定
        """
        results: list[dict] = []

        for target in viewpoint.targets:
            bearing = self._geo.calculate_bearing(
                viewpoint.location.lat,
                viewpoint.location.lon,
                target.lat,
                target.lon,
            )

            if target.applicable_events is not None:
                matched_events = target.applicable_events
            else:
                matched_events = []
                if sun_events is not None:
                    if self._geo.is_opposite_direction(
                        bearing, sun_events.sunrise_azimuth
                    ):
                        matched_events.append("sunrise_golden_mountain")
                    if self._geo.is_opposite_direction(
                        bearing, sun_events.sunset_azimuth
                    ):
                        matched_events.append("sunset_golden_mountain")

            results.append({
                "target": target,
                "bearing": bearing,
                "matched_events": matched_events,
            })

        return results

    @staticmethod
    def _slice_day(
        weather_all: pd.DataFrame, target_date: date
    ) -> pd.DataFrame:
        """从多天天气数据中切取指定日期的数据"""
        if weather_all.empty:
            return weather_all

        date_str = str(target_date)

        if "forecast_date" in weather_all.columns:
            return weather_all[weather_all["forecast_date"] == date_str].copy()

        # 尝试从 time 列提取日期
        if "time" in weather_all.columns:
            dates = pd.to_datetime(weather_all["time"]).dt.date.astype(str)
            return weather_all[dates == date_str].copy()

        return weather_all
