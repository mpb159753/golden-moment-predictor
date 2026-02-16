"""GMP CLI 入口 — 川西旅行景观预测引擎

所有命令通过 ``python -m gmp.main`` 或安装后的 ``gmp`` 调用。
"""

from __future__ import annotations

import json
from datetime import datetime as _DateTime
from pathlib import Path
from typing import TYPE_CHECKING

import click
import structlog

from gmp.cache.repository import CacheRepository
from gmp.cache.weather_cache import WeatherCache
from gmp.core.config_loader import ConfigManager, RouteConfig, ViewpointConfig
from gmp.core.exceptions import (
    GMPError,
    InvalidDateError,
    ServiceUnavailableError,
    ViewpointNotFoundError,
)
from gmp.core.logging import setup_logging
from gmp.core.scheduler import GMPScheduler
from gmp.data.astro_utils import AstroUtils
from gmp.data.geo_utils import GeoUtils
from gmp.data.meteo_fetcher import MeteoFetcher
from gmp.output.cli_formatter import CLIFormatter
from gmp.output.forecast_reporter import ForecastReporter
from gmp.output.json_file_writer import JSONFileWriter
from gmp.output.timeline_reporter import TimelineReporter
from gmp.scoring.engine import ScoreEngine
from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin
from gmp.scoring.plugins.frost import FrostPlugin
from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin
from gmp.scoring.plugins.ice_icicle import IceIciclePlugin
from gmp.scoring.plugins.snow_tree import SnowTreePlugin
from gmp.scoring.plugins.stargazing import StargazingPlugin

if TYPE_CHECKING:
    from gmp.backtest.backtester import Backtester
    from gmp.core.batch_generator import BatchGenerator


# ==================== 组件初始化工厂 ====================


def _load_configs(
    config_path: str = "config/engine_config.yaml",
) -> tuple[ViewpointConfig, RouteConfig, ConfigManager]:
    """加载所有配置文件"""
    config_manager = ConfigManager(config_path)
    viewpoint_config = ViewpointConfig()
    viewpoint_config.load("config/viewpoints/")
    route_config = RouteConfig()
    route_config.load("config/routes/")
    return viewpoint_config, route_config, config_manager


def _register_plugins(engine: ScoreEngine, config: ConfigManager) -> None:
    """注册所有评分 Plugin"""
    engine.register(GoldenMountainPlugin("sunrise_golden_mountain", config))
    engine.register(GoldenMountainPlugin("sunset_golden_mountain", config))
    engine.register(StargazingPlugin(config))
    engine.register(CloudSeaPlugin(config))
    engine.register(FrostPlugin(config))
    engine.register(SnowTreePlugin(config))
    engine.register(IceIciclePlugin(config))


def _create_core_components(
    config_path: str = "config/engine_config.yaml",
) -> tuple[
    GMPScheduler, ViewpointConfig, RouteConfig, ConfigManager,
    CacheRepository, MeteoFetcher,
]:
    """创建核心依赖组件栈

    Returns:
        (scheduler, viewpoint_config, route_config, config_manager,
         cache_repo, fetcher)
    """
    viewpoint_config, route_config, config_manager = _load_configs(config_path)

    repo = CacheRepository(config_manager.config.db_path)
    cache = WeatherCache(
        repo, config_manager.config.data_freshness
    )
    fetcher = MeteoFetcher(cache, config_manager.config.timeout)

    engine = ScoreEngine()
    _register_plugins(engine, config_manager)

    astro = AstroUtils()
    geo = GeoUtils()

    scheduler = GMPScheduler(
        config=config_manager,
        viewpoint_config=viewpoint_config,
        route_config=route_config,
        fetcher=fetcher,
        score_engine=engine,
        astro=astro,
        geo=geo,
    )

    return scheduler, viewpoint_config, route_config, config_manager, repo, fetcher


def create_scheduler(
    config_path: str = "config/engine_config.yaml",
) -> GMPScheduler:
    """创建 Scheduler 及其核心依赖组件"""
    scheduler, *_ = _create_core_components(config_path)
    return scheduler


def create_batch_generator(
    scheduler: GMPScheduler,
    viewpoint_config: ViewpointConfig,
    route_config: RouteConfig,
    config: ConfigManager,
    output_dir: str = "public/data",
    archive_dir: str = "archive",
) -> BatchGenerator:
    """创建 BatchGenerator 及输出层组件"""
    from gmp.core.batch_generator import BatchGenerator

    forecast_reporter = ForecastReporter()
    timeline_reporter = TimelineReporter()
    json_writer = JSONFileWriter(output_dir=output_dir, archive_dir=archive_dir)

    return BatchGenerator(
        scheduler=scheduler,
        viewpoint_config=viewpoint_config,
        route_config=route_config,
        forecast_reporter=forecast_reporter,
        timeline_reporter=timeline_reporter,
        json_writer=json_writer,
        output_dir=output_dir,
    )


def create_backtester(
    config_path: str = "config/engine_config.yaml",
) -> Backtester:
    """创建 Backtester 及其依赖"""
    from gmp.backtest.backtester import Backtester

    scheduler, viewpoint_config, _, config_manager, repo, fetcher = (
        _create_core_components(config_path)
    )

    return Backtester(
        scheduler=scheduler,
        fetcher=fetcher,
        config=config_manager,
        cache_repo=repo,
        viewpoint_config=viewpoint_config,
    )


def _parse_events(events: str | None) -> list[str] | None:
    """解析逗号分隔的事件字符串为列表"""
    if not events:
        return None
    return [e.strip() for e in events.split(",") if e.strip()]


# ==================== CLI 命令 ====================


@click.group()
@click.option("--log-level", default="INFO", help="日志级别")
def cli(log_level: str) -> None:
    """GMP — 川西旅行景观预测引擎。"""
    setup_logging(log_level)


@cli.command()
@click.argument("viewpoint_id")
@click.option("--days", default=7, type=click.IntRange(1, 16), help="预测天数 (1-16)")
@click.option("--events", default=None, help="逗号分隔的事件过滤")
@click.option(
    "--output",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="输出格式",
)
@click.option("--detail", is_flag=True, help="显示评分明细")
@click.option(
    "--output-file",
    default=None,
    type=click.Path(),
    help="输出 JSON 文件路径 (仅 --output json)",
)
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def predict(
    viewpoint_id: str,
    days: int,
    events: str | None,
    output_format: str,
    detail: bool,
    output_file: str | None,
    config: str,
) -> None:
    """对指定观景台生成预测"""
    try:
        scheduler = create_scheduler(config)
        events_list = _parse_events(events)
        result = scheduler.run(viewpoint_id, days=days, events=events_list)

        if output_format == "json":
            forecast = ForecastReporter().generate(result)
            json_output = json.dumps(forecast, ensure_ascii=False, indent=2)
            if output_file:
                Path(output_file).write_text(json_output, encoding="utf-8")
                click.echo(f"已输出到: {output_file}")
            else:
                click.echo(json_output)
        else:
            formatter = CLIFormatter()
            if detail:
                click.echo(formatter.format_detail(result))
            else:
                click.echo(formatter.format_forecast(result))
    except ViewpointNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        raise SystemExit(1)
    except ServiceUnavailableError as e:
        click.echo(f"服务不可用: {e}", err=True)
        raise SystemExit(2)
    except GMPError as e:
        click.echo(f"GMP 错误: {e}", err=True)
        raise SystemExit(3)


@cli.command("predict-route")
@click.argument("route_id")
@click.option("--days", default=7, type=click.IntRange(1, 16), help="预测天数 (1-16)")
@click.option("--events", default=None, help="逗号分隔的事件过滤")
@click.option(
    "--output",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="输出格式",
)
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def predict_route(
    route_id: str,
    days: int,
    events: str | None,
    output_format: str,
    config: str,
) -> None:
    """对指定线路生成预测"""
    try:
        scheduler, _, route_config, *_ = _create_core_components(config)
        events_list = _parse_events(events)
        results = scheduler.run_route(route_id, days=days, events=events_list)

        if output_format == "json":
            route = route_config.get(route_id)
            forecast = ForecastReporter().generate_route(results, route)
            click.echo(json.dumps(forecast, ensure_ascii=False, indent=2))
        else:
            formatter = CLIFormatter()
            route = route_config.get(route_id)
            # 线路头信息
            lines: list[str] = [
                f"🗺️  线路: {route.name} ({route.id})  |  共 {len(route.stops)} 站",
                "=" * 60,
            ]
            # 按站序展示每站预测（results 已按 route.stops 顺序排列）
            for pr in results:
                lines.append(formatter.format_forecast(pr))
            click.echo("\n".join(lines))
    except ViewpointNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        raise SystemExit(1)
    except ServiceUnavailableError as e:
        click.echo(f"服务不可用: {e}", err=True)
        raise SystemExit(2)
    except GMPError as e:
        click.echo(f"GMP 错误: {e}", err=True)
        raise SystemExit(3)


@cli.command("generate-all")
@click.option("--days", default=7, type=click.IntRange(1, 16), help="预测天数 (1-16)")
@click.option("--events", default=None, help="逗号分隔的事件过滤")
@click.option("--fail-fast", is_flag=True, help="单站失败时立即中止")
@click.option("--no-archive", is_flag=True, help="跳过历史归档")
@click.option(
    "--output",
    "output_dir",
    default="public/data",
    type=click.Path(),
    help="JSON 输出目录",
)
@click.option(
    "--archive",
    "archive_dir",
    default="archive",
    type=click.Path(),
    help="历史归档目录",
)
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def generate_all(
    days: int,
    events: str | None,
    fail_fast: bool,
    no_archive: bool,
    output_dir: str,
    archive_dir: str,
    config: str,
) -> None:
    """批量生成所有观景台和线路的预测 JSON 文件"""
    try:
        scheduler, viewpoint_config, route_config, config_manager, *_ = (
            _create_core_components(config)
        )
        batch_gen = create_batch_generator(
            scheduler, viewpoint_config, route_config, config_manager,
            output_dir=output_dir, archive_dir=archive_dir,
        )

        events_list = _parse_events(events)
        result = batch_gen.generate_all(
            days=days,
            events=events_list,
            fail_fast=fail_fast,
            no_archive=no_archive,
        )

        click.echo(f"✅ 生成完成")
        click.echo(
            f"   观景台: {result['viewpoints_processed']} 成功"
            f", {len(result['failed_viewpoints'])} 失败"
        )
        click.echo(
            f"   线路: {result['routes_processed']} 成功"
            f", {len(result['failed_routes'])} 失败"
        )
        click.echo(f"   输出目录: {result['output_dir']}")
        if result.get("archive_dir"):
            click.echo(f"   归档目录: {result['archive_dir']}")
    except GMPError as e:
        click.echo(f"GMP 错误: {e}", err=True)
        raise SystemExit(3)


@cli.command()
@click.argument("viewpoint_id")
@click.option(
    "--date",
    "target_date",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="目标日期 (YYYY-MM-DD)",
)
@click.option("--events", default=None, help="逗号分隔的事件过滤")
@click.option("--save", is_flag=True, help="保存回测结果到数据库")
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def backtest(
    viewpoint_id: str,
    target_date: _DateTime,
    events: str | None,
    save: bool,
    config: str,
) -> None:
    """对历史日期进行回测"""
    try:
        backtester = create_backtester(config)
        events_list = _parse_events(events)

        report = backtester.run(
            viewpoint_id=viewpoint_id,
            target_date=target_date.date(),
            events=events_list,
            save=save,
        )

        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    except ViewpointNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        raise SystemExit(1)
    except InvalidDateError as e:
        click.echo(f"日期错误: {e}", err=True)
        raise SystemExit(1)
    except GMPError as e:
        click.echo(f"GMP 错误: {e}", err=True)
        raise SystemExit(3)


@cli.command("list-viewpoints")
@click.option(
    "--output",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="输出格式",
)
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def list_viewpoints(output_format: str, config: str) -> None:
    """列出所有可用观景台"""
    viewpoint_config, _, _ = _load_configs(config)
    viewpoints = viewpoint_config.list_all()

    if output_format == "json":
        data = [
            {
                "id": vp.id,
                "name": vp.name,
                "location": {
                    "lat": vp.location.lat,
                    "lon": vp.location.lon,
                    "altitude": vp.location.altitude,
                },
                "capabilities": vp.capabilities,
            }
            for vp in viewpoints
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"{'ID':<25} {'名称':<15} {'海拔(m)':<10} {'景观类型'}")
        click.echo("-" * 70)
        for vp in viewpoints:
            caps = ", ".join(vp.capabilities)
            click.echo(
                f"{vp.id:<25} {vp.name:<15} {vp.location.altitude:<10} {caps}"
            )


@cli.command("list-routes")
@click.option(
    "--output",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="输出格式",
)
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def list_routes(output_format: str, config: str) -> None:
    """列出所有可用线路"""
    _, route_config, _ = _load_configs(config)
    routes = route_config.list_all()

    if output_format == "json":
        data = [
            {
                "id": r.id,
                "name": r.name,
                "stops_count": len(r.stops),
                "stops": [
                    {"viewpoint_id": s.viewpoint_id, "order": s.order}
                    for s in r.stops
                ],
            }
            for r in routes
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"{'ID':<20} {'名称':<15} {'站数':<8} {'站点'}")
        click.echo("-" * 70)
        for r in routes:
            stops = " → ".join(s.viewpoint_id for s in r.stops)
            click.echo(
                f"{r.id:<20} {r.name:<15} {len(r.stops):<8} {stops}"
            )


if __name__ == "__main__":
    cli()
