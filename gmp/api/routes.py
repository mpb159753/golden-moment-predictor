"""FastAPI 路由定义 — GMP REST API

设计依据:
- design/05-api.md: 全部 API 定义
- design/07-code-interface.md §7.4: api/ 目录
- design/08-operations.md §8.4-8.5: 结构化日志

端点:
  GET /api/v1/viewpoints            观景台列表 (分页)
  GET /api/v1/forecast/{id}         景观预测报告
  GET /api/v1/timeline/{id}         逐小时时间轴
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Path as PathParam, Query

from gmp.api.middleware import gmp_exception_handler, service_unavailable_handler
from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.core.exceptions import GMPError, ViewpointNotFoundError
from gmp.reporter.forecast_reporter import ForecastReporter
from gmp.reporter.timeline_reporter import TimelineReporter
from gmp.scorer.cloud_sea import CloudSeaPlugin
from gmp.scorer.engine import ScoreEngine
from gmp.scorer.frost import FrostPlugin
from gmp.scorer.golden_mountain import GoldenMountainPlugin
from gmp.scorer.ice_icicle import IceIciclePlugin
from gmp.scorer.snow_tree import SnowTreePlugin
from gmp.scorer.stargazing import StargazingPlugin

logger = logging.getLogger(__name__)

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _viewpoint_to_dict(vp) -> dict:
    """将 Viewpoint dataclass 转换为 API 响应 dict"""
    return {
        "id": vp.id,
        "name": vp.name,
        "location": {
            "lat": vp.location.lat,
            "lon": vp.location.lon,
            "altitude": vp.location.altitude,
        },
        "capabilities": vp.capabilities,
        "targets": [
            {
                "name": t.name,
                "altitude": t.altitude,
                "weight": t.weight,
                "applicable_events": t.applicable_events,
            }
            for t in vp.targets
        ],
    }


def _create_score_engine() -> ScoreEngine:
    """创建并注册所有评分 Plugin"""
    engine = ScoreEngine()
    engine.register(GoldenMountainPlugin("sunrise_golden_mountain"))
    engine.register(GoldenMountainPlugin("sunset_golden_mountain"))
    engine.register(StargazingPlugin())
    engine.register(CloudSeaPlugin())
    engine.register(FrostPlugin())
    engine.register(SnowTreePlugin())
    engine.register(IceIciclePlugin())
    return engine


def create_app(
    config: EngineConfig | None = None,
    viewpoint_config: ViewpointConfig | None = None,
    scheduler=None,
) -> FastAPI:
    """FastAPI 应用工厂

    允许测试注入 mock 依赖。在生产模式下 lifespan 自动初始化。

    Args:
        config: 引擎配置 (None=从 YAML 加载)
        viewpoint_config: 观景台配置 (None=从 viewpoints/ 加载)
        scheduler: GMPScheduler 实例 (None=自动创建)
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        # 如果未注入，则自动初始化
        if app.state.scheduler is None:
            from gmp.astro.astro_utils import AstroUtils
            from gmp.core.scheduler import GMPScheduler
            from gmp.fetcher.meteo_fetcher import MeteoFetcher

            cfg = app.state.config
            vp_cfg = app.state.viewpoint_config

            fetcher = MeteoFetcher(cfg)
            astro = AstroUtils()
            score_engine = _create_score_engine()

            app.state.scheduler = GMPScheduler(
                config=cfg,
                viewpoint_config=vp_cfg,
                fetcher=fetcher,
                astro=astro,
                score_engine=score_engine,
            )

        logger.info("gmp_started", extra={"version": "1.0.0"})
        yield
        logger.info("gmp_shutdown")

    app = FastAPI(
        title="GMP 景观预测引擎",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 注入依赖到 app.state
    app.state.config = config or EngineConfig.from_yaml(
        _PROJECT_ROOT / "config" / "engine_config.yaml"
    )
    if viewpoint_config is None:
        viewpoint_config = ViewpointConfig()
        viewpoint_config.load(_PROJECT_ROOT / "config" / "viewpoints")
    app.state.viewpoint_config = viewpoint_config
    app.state.scheduler = scheduler

    # Reporter 实例
    app.state.forecast_reporter = ForecastReporter()
    app.state.timeline_reporter = TimelineReporter()

    # 注册异常处理
    app.add_exception_handler(GMPError, gmp_exception_handler)

    # ServiceUnavailableError (统一定义在 exceptions 模块)
    from gmp.core.exceptions import ServiceUnavailableError
    app.add_exception_handler(
        ServiceUnavailableError, service_unavailable_handler
    )

    # ----------------------------------------------------------------
    # 路由
    # ----------------------------------------------------------------

    @app.get("/api/v1/viewpoints")
    def list_viewpoints(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    ) -> dict:
        """获取观景台列表

        响应字段: viewpoints[], pagination{page, page_size, total, total_pages}
        """
        result = app.state.viewpoint_config.list_all(
            page=page, page_size=page_size
        )

        viewpoints = [
            _viewpoint_to_dict(vp) for vp in result["viewpoints"]
        ]

        return {
            "viewpoints": viewpoints,
            "pagination": result["pagination"],
        }

    @app.get("/api/v1/forecast/{viewpoint_id}")
    def get_forecast(
        viewpoint_id: str = PathParam(..., description="观景台 ID"),
        days: int = Query(7, ge=1, le=7, description="预测天数"),
        events: str | None = Query(
            None, description="逗号分隔的事件类型过滤"
        ),
    ) -> dict:
        """获取景观预测报告

        响应: ForecastReporter 生成的 JSON

        错误:
        - 404: ViewpointNotFound
        - 422: InvalidParameter (days > 7, 由 FastAPI 自动校验)
        """
        start_time = time.monotonic()

        # 解析 events 参数
        events_list: list[str] | None = None
        if events:
            events_list = [e.strip() for e in events.split(",") if e.strip()]

        # 运行预测
        scheduler_result = app.state.scheduler.run(
            viewpoint_id=viewpoint_id,
            days=days,
            events=events_list,
        )

        # 格式化输出
        report = app.state.forecast_reporter.generate(scheduler_result)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "forecast_generated",
            extra={
                "viewpoint": viewpoint_id,
                "days": days,
                "events_filter": events,
                "duration_ms": duration_ms,
            },
        )

        return report

    @app.get("/api/v1/timeline/{viewpoint_id}")
    def get_timeline(
        viewpoint_id: str = PathParam(..., description="观景台 ID"),
        days: int = Query(7, ge=1, le=7, description="预测天数"),
    ) -> dict:
        """获取逐小时时间轴数据

        响应: TimelineReporter 生成的 JSON
        """
        start_time = time.monotonic()

        scheduler_result = app.state.scheduler.run(
            viewpoint_id=viewpoint_id,
            days=days,
        )

        report = app.state.timeline_reporter.generate(scheduler_result)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "timeline_generated",
            extra={
                "viewpoint": viewpoint_id,
                "days": days,
                "duration_ms": duration_ms,
            },
        )

        return report

    return app


# 默认应用实例 (用于 uvicorn 启动)
app = create_app()
