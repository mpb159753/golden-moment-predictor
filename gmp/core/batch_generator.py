"""gmp/core/batch_generator.py — 批量生成编排器

遍历所有观景台/线路→调用 Scheduler 评分→生成 JSON 文件→归档。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

import structlog

from gmp.scoring.engine import _UNIVERSAL_CAPABILITIES


if TYPE_CHECKING:
    from gmp.core.config_loader import RouteConfig, ViewpointConfig
    from gmp.core.models import PipelineResult
    from gmp.core.scheduler import GMPScheduler
    from gmp.output.forecast_reporter import ForecastReporter
    from gmp.output.json_file_writer import JSONFileWriter
    from gmp.output.timeline_reporter import TimelineReporter

logger = structlog.get_logger()

_CST = timezone(timedelta(hours=8))


class BatchGenerator:
    """批量生成编排器 — 遍历观景台/线路、调用 Scheduler、写入文件"""

    def __init__(
        self,
        scheduler: GMPScheduler,
        viewpoint_config: ViewpointConfig,
        route_config: RouteConfig,
        forecast_reporter: ForecastReporter,
        timeline_reporter: TimelineReporter,
        json_writer: JSONFileWriter,
        output_dir: str = "public/data",
    ) -> None:
        self._scheduler = scheduler
        self._viewpoint_config = viewpoint_config
        self._route_config = route_config
        self._forecast_reporter = forecast_reporter
        self._timeline_reporter = timeline_reporter
        self._json_writer = json_writer
        self._output_dir = output_dir

    def generate_all(
        self,
        days: int = 7,
        events: list[str] | None = None,
        fail_fast: bool = False,
        no_archive: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict:
        """批量生成所有观景台+线路的预测

        Returns:
            {
                "viewpoints_processed": int,
                "routes_processed": int,
                "failed_viewpoints": list[str],
                "failed_routes": list[str],
                "output_dir": str,
                "archive_dir": str | None,
            }
        """
        failed_viewpoints: list[str] = []
        failed_routes: list[str] = []
        successful_viewpoints: list[str] = []
        successful_routes: list[str] = []

        all_viewpoints = self._viewpoint_config.list_all()
        all_routes = self._route_config.list_all()
        total = len(all_viewpoints) + len(all_routes)
        current = 0

        _report = progress_callback or (lambda _msg: None)
        _report(
            f"🚀 开始批量生成: {len(all_viewpoints)} 个观景台, "
            f"{len(all_routes)} 条线路, 预测 {days} 天"
        )

        # 1. 遍历所有 viewpoints
        for vp in all_viewpoints:
            current += 1
            result = self._process_viewpoint(vp.id, days, events, fail_fast)
            if result is not None:
                successful_viewpoints.append(vp.id)
                _report(
                    f"📊 [{current}/{total}] ✅ 观景台 {vp.id} ({vp.name})"
                )
            else:
                failed_viewpoints.append(vp.id)
                _report(
                    f"📊 [{current}/{total}] ❌ 观景台 {vp.id} ({vp.name}) — 失败"
                )

        # 2. 遍历所有 routes
        for route in all_routes:
            current += 1
            route_result = self._process_route(
                route.id, days, events, fail_fast
            )
            if route_result is not None:
                successful_routes.append(route.id)
                _report(
                    f"📊 [{current}/{total}] ✅ 线路 {route.id} ({route.name})"
                )
            else:
                failed_routes.append(route.id)
                _report(
                    f"📊 [{current}/{total}] ❌ 线路 {route.id} ({route.name}) — 失败"
                )

        # 3. 生成 index.json (富对象格式，含 name/location/capabilities)
        vp_index = []
        for vp_id in successful_viewpoints:
            vp = self._viewpoint_config.get(vp_id)
            vp_index.append({
                "id": vp.id,
                "name": vp.name,
                "groups": vp.groups,
                "location": {
                    "lat": vp.location.lat,
                    "lon": vp.location.lon,
                    "altitude": vp.location.altitude,
                },
                "capabilities": list(set(vp.capabilities + _UNIVERSAL_CAPABILITIES)),
                "forecast_url": f"viewpoints/{vp.id}/forecast.json",
            })

        route_index = []
        for route_id in successful_routes:
            route = self._route_config.get(route_id)
            stops = []
            for s in route.stops:
                try:
                    stop_vp = self._viewpoint_config.get(s.viewpoint_id)
                    stop_name = stop_vp.name
                except Exception:
                    stop_name = s.viewpoint_id
                stops.append({"viewpoint_id": s.viewpoint_id, "name": stop_name})
            route_index.append({
                "id": route.id,
                "name": route.name,
                "stops": stops,
                "forecast_url": f"routes/{route.id}/forecast.json",
            })

        self._json_writer.write_index(
            viewpoints=vp_index,
            routes=route_index,
        )

        # 4. 生成 meta.json
        now = datetime.now(_CST)
        self._json_writer.write_meta(
            {
                "generated_at": now.isoformat(),
                "viewpoints_count": len(successful_viewpoints),
                "routes_count": len(successful_routes),
            }
        )

        # 5. 生成 poster.json
        from gmp.output.poster_generator import PosterGenerator

        poster_gen = PosterGenerator(self._output_dir)
        poster_data = poster_gen.generate(
            self._viewpoint_config, days=min(days, 7)
        )
        self._json_writer.write_poster(poster_data)

        # 6. 归档
        archive_dir: str | None = None
        if not no_archive:
            timestamp = now.strftime("%Y-%m-%dT%H-%M")
            self._json_writer.archive(timestamp)
            archive_dir = timestamp


        return {
            "viewpoints_processed": len(successful_viewpoints),
            "routes_processed": len(successful_routes),
            "failed_viewpoints": failed_viewpoints,
            "failed_routes": failed_routes,
            "output_dir": self._output_dir,
            "archive_dir": archive_dir,
        }

    def _process_viewpoint(
        self,
        viewpoint_id: str,
        days: int,
        events: list[str] | None,
        fail_fast: bool = False,
    ) -> PipelineResult | None:
        """处理单个观景台：评分 + 文件生成，失败返回 None"""
        try:
            result = self._scheduler.run(
                viewpoint_id, days=days, events=events
            )
        except Exception:
            if fail_fast:
                raise
            logger.warning(
                "batch.viewpoint_failed",
                viewpoint=viewpoint_id,
                exc_info=True,
            )
            return None

        # 生成 forecast + timeline 并写入文件
        forecast = self._forecast_reporter.generate(result)

        # 多日 timeline：每天生成 timeline_{date}.json
        today = datetime.now(_CST).date()
        timeline: dict | None = None
        for fd in result.forecast_days:
            fd_date = date.fromisoformat(fd.date)
            tl = self._timeline_reporter.generate(result, fd_date)
            self._json_writer.write_viewpoint_timeline(
                viewpoint_id, fd.date, tl
            )
            if fd_date == today:
                timeline = tl

        # 当日或第一天的 timeline 写入主 timeline.json（向后兼容）
        if timeline is None and result.forecast_days:
            first_date = date.fromisoformat(result.forecast_days[0].date)
            timeline = self._timeline_reporter.generate(result, first_date)

        self._json_writer.write_viewpoint(
            viewpoint_id, forecast, timeline or {}
        )

        return result

    def _process_route(
        self,
        route_id: str,
        days: int,
        events: list[str] | None,
        fail_fast: bool = False,
    ) -> dict | None:
        """处理单条线路：评分 + 文件生成，失败返回 None"""
        try:
            results = self._scheduler.run_route(
                route_id, days=days, events=events
            )
        except Exception:
            if fail_fast:
                raise
            logger.warning(
                "batch.route_failed",
                route=route_id,
                exc_info=True,
            )
            return None

        route = self._route_config.get(route_id)
        forecast = self._forecast_reporter.generate_route(results, route)
        self._json_writer.write_route(route_id, forecast)

        return forecast
