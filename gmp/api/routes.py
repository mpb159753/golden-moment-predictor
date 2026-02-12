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

import time
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, Path as PathParam, Query

from gmp.api.middleware import gmp_exception_handler
from gmp.api.schemas import ViewpointListResponse
from gmp.core.config_loader import EngineConfig, ViewpointConfig
from gmp.core.exceptions import GMPError
from gmp.core.log_config import setup_logging
from gmp.reporter.forecast_reporter import ForecastReporter
from gmp.reporter.timeline_reporter import TimelineReporter
from gmp.scorer.engine import ScoreEngine, create_default_engine

logger = structlog.get_logger(__name__)

# gmp 包目录 (gmp/)
_GMP_DIR = Path(__file__).resolve().parent.parent


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
        # 初始化日志 (使用配置)
        cfg = app.state.config
        setup_logging(level=cfg.log_level, fmt=cfg.log_format)

        # 如果未注入，则自动初始化
        if app.state.scheduler is None:
            from gmp.astro.astro_utils import AstroUtils
            from gmp.core.scheduler import GMPScheduler
            from gmp.fetcher.meteo_fetcher import MeteoFetcher

            vp_cfg = app.state.viewpoint_config

            from gmp.cache.memory_cache import MemoryCache
            from gmp.cache.repository import CacheRepository
            from gmp.cache.weather_cache import WeatherCache

            memory_cache = MemoryCache(ttl_seconds=cfg.memory_cache_ttl_seconds)
            repository = CacheRepository(db_path=cfg.db_path)
            cache = WeatherCache(
                memory_cache=memory_cache,
                repository=repository,
                ttl_db_seconds=cfg.db_cache_ttl_seconds,
            )
            fetcher = MeteoFetcher(cache=cache)
            astro = AstroUtils()
            score_engine = create_default_engine(cfg)

            app.state.scheduler = GMPScheduler(
                config=cfg,
                viewpoint_config=vp_cfg,
                fetcher=fetcher,
                astro=astro,
                score_engine=score_engine,
            )

        logger.info("gmp_started", version="1.0.0")
        yield
        logger.info("gmp_shutdown")

    app = FastAPI(
        title="GMP 景观预测引擎",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 注入依赖到 app.state
    app.state.config = config or EngineConfig.from_yaml(
        _GMP_DIR / "config" / "engine_config.yaml"
    )
    if viewpoint_config is None:
        viewpoint_config = ViewpointConfig()
        viewpoint_config.load(_GMP_DIR / "config" / "viewpoints")
    app.state.viewpoint_config = viewpoint_config
    app.state.scheduler = scheduler

    # Reporter 实例
    app.state.forecast_reporter = ForecastReporter()
    app.state.timeline_reporter = TimelineReporter()

    # 注册统一异常处理 (C3: 合并为单个 handler)
    app.add_exception_handler(GMPError, gmp_exception_handler)

    # ----------------------------------------------------------------
    # 路由
    # ----------------------------------------------------------------

    @app.get("/api/v1/viewpoints", response_model=ViewpointListResponse)
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
            viewpoint=viewpoint_id,
            days=days,
            events_filter=events,
            duration_ms=duration_ms,
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
            viewpoint=viewpoint_id,
            days=days,
            duration_ms=duration_ms,
        )

        return report

    return app


def get_app() -> FastAPI:
    """懒加载应用实例 (用于 uvicorn 启动)"""
    return create_app()
