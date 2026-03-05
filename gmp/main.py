"""GMP CLI 入口 — 川西旅行景观预测引擎

所有命令通过 ``python -m gmp.main`` 或安装后的 ``gmp`` 调用。
"""

from __future__ import annotations

import json
import unicodedata
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
from gmp.scoring.plugins.clear_sky import ClearSkyPlugin
from gmp.scoring.plugins.cloud_sea import CloudSeaPlugin
from gmp.scoring.plugins.frost import FrostPlugin
from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin
# from gmp.scoring.plugins.ice_icicle import IceIciclePlugin  # 暂停
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
    gm_cfg = config.get_plugin_config("golden_mountain")
    engine.register(GoldenMountainPlugin("sunrise_golden_mountain", gm_cfg))
    engine.register(GoldenMountainPlugin("sunset_golden_mountain", gm_cfg))
    engine.register(StargazingPlugin(config.get_plugin_config("stargazing")))
    engine.register(CloudSeaPlugin(
        config.get_plugin_config("cloud_sea"),
        config.get_safety_config(),
    ))
    engine.register(FrostPlugin(config.get_plugin_config("frost")))
    engine.register(ClearSkyPlugin(config.get_plugin_config("clear_sky")))
    engine.register(SnowTreePlugin(config.get_plugin_config("snow_tree")))
    # engine.register(IceIciclePlugin(config.get_plugin_config("ice_icicle")))  # 暂停


def _create_core_components(
    config_path: str = "config/engine_config.yaml",
) -> tuple[
    GMPScheduler, ViewpointConfig, RouteConfig, ConfigManager,
    CacheRepository, MeteoFetcher, ScoreEngine,
]:
    """创建核心依赖组件栈

    Returns:
        (scheduler, viewpoint_config, route_config, config_manager,
         cache_repo, fetcher, engine)
    """
    viewpoint_config, route_config, config_manager = _load_configs(config_path)

    repo = CacheRepository(config_manager.config.db_path)
    cache = WeatherCache(
        repo, config_manager.config.data_freshness
    )
    fetcher = MeteoFetcher(cache)

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

    return scheduler, viewpoint_config, route_config, config_manager, repo, fetcher, engine


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
    display_names: dict[str, str] | None = None,
) -> BatchGenerator:
    """创建 BatchGenerator 及输出层组件"""
    from gmp.core.batch_generator import BatchGenerator

    forecast_reporter = ForecastReporter(display_names=display_names)
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

    scheduler, viewpoint_config, _, config_manager, repo, fetcher, _engine = (
        _create_core_components(config_path)
    )

    return Backtester(
        scheduler=scheduler,
        fetcher=fetcher,
        config=config_manager,
        cache_repo=repo,
        viewpoint_config=viewpoint_config,
    )


def _display_width(s: str) -> int:
    """计算字符串在终端中的显示宽度（中文占 2 列）"""
    w = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        w += 2 if eaw in ("W", "F") else 1
    return w


def _pad(s: str, width: int) -> str:
    """将字符串填充到指定显示宽度（兼容中文）"""
    return s + " " * max(0, width - _display_width(s))


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
        scheduler, _, _, _, _, _, engine = _create_core_components(config)
        dn = engine.display_names
        events_list = _parse_events(events)
        result = scheduler.run(viewpoint_id, days=days, events=events_list)

        if output_format == "json":
            forecast = ForecastReporter(display_names=dn).generate(result)
            json_output = json.dumps(forecast, ensure_ascii=False, indent=2)
            if output_file:
                Path(output_file).write_text(json_output, encoding="utf-8")
                click.echo(f"已输出到: {output_file}")
            else:
                click.echo(json_output)
        else:
            formatter = CLIFormatter(display_names=dn)
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
        scheduler, _, route_config, _, _, _, engine = _create_core_components(config)
        dn = engine.display_names
        events_list = _parse_events(events)
        results = scheduler.run_route(route_id, days=days, events=events_list)

        if output_format == "json":
            route = route_config.get(route_id)
            forecast = ForecastReporter(display_names=dn).generate_route(results, route)
            click.echo(json.dumps(forecast, ensure_ascii=False, indent=2))
        else:
            formatter = CLIFormatter(display_names=dn)
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
        scheduler, viewpoint_config, route_config, config_manager, _, _, engine = (
            _create_core_components(config)
        )
        batch_gen = create_batch_generator(
            scheduler, viewpoint_config, route_config, config_manager,
            output_dir=output_dir, archive_dir=archive_dir,
            display_names=engine.display_names,
        )

        events_list = _parse_events(events)
        result = batch_gen.generate_all(
            days=days,
            events=events_list,
            fail_fast=fail_fast,
            no_archive=no_archive,
            progress_callback=click.echo,
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
    capability_zh: dict[str, str] = {
        "clear_sky": "晴天",
        "sunrise": "日出",
        "sunset": "日落",
        "cloud_sea": "云海",
        "stargazing": "星空",
        "snow_tree": "雾凇",
        "frost": "霜冻",
        "ice_icicle": "冰挂",
        "autumn_foliage": "红叶",
        "waterfall": "瀑布",
        "geology": "地质",
    }

    def _cap_zh(cap: str) -> str:
        return capability_zh.get(cap, cap)

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
                "capabilities": [_cap_zh(c) for c in vp.capabilities],
            }
            for vp in viewpoints
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"{_pad('ID', 30)}{_pad('名称', 24)}{_pad('海拔(m)', 10)}景观类型")
        click.echo("-" * 84)
        for vp in viewpoints:
            caps = ", ".join(_cap_zh(c) for c in vp.capabilities)
            alt = str(vp.location.altitude)
            click.echo(
                f"{_pad(vp.id, 30)}{_pad(vp.name, 24)}{_pad(alt, 10)}{caps}"
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
        click.echo(f"{_pad('ID', 22)}{_pad('名称', 18)}{_pad('站数', 8)}站点")
        click.echo("-" * 78)
        for r in routes:
            stops = " → ".join(s.viewpoint_id for s in r.stops)
            click.echo(
                f"{_pad(r.id, 22)}{_pad(r.name, 18)}{_pad(str(len(r.stops)), 8)}{stops}"
            )


@cli.command()
@click.argument("viewpoint_id")
@click.option("--days", default=10, type=click.IntRange(1, 16), help="预测天数 (1-16)")
@click.option(
    "--output",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="输出格式",
)
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def debug(
    viewpoint_id: str,
    days: int,
    output_format: str,
    config: str,
) -> None:
    """诊断日照金山评分 — 逐天输出每个决策点的判断依据"""
    from datetime import timedelta

    from gmp.data.astro_utils import AstroUtils
    from gmp.scoring.plugins.golden_mountain import GoldenMountainPlugin

    try:
        scheduler, viewpoint_config, _, config_manager, _, _ = (
            _create_core_components(config)
        )
        viewpoint = viewpoint_config.get(viewpoint_id)

        # 创建 sunrise/sunset 两个 GoldenMountain Plugin 实例
        gm_cfg = config_manager.get_plugin_config("golden_mountain")
        plugins = [
            GoldenMountainPlugin("sunrise_golden_mountain", gm_cfg),
            GoldenMountainPlugin("sunset_golden_mountain", gm_cfg),
        ]

        # 仅保留 viewpoint 实际配置了的 capability
        from gmp.scoring.engine import _CAPABILITY_EVENT_MAP
        allowed_events: set[str] = set()
        for cap in viewpoint.capabilities:
            mapped = _CAPABILITY_EVENT_MAP.get(cap, [cap])
            allowed_events.update(mapped)
        plugins = [p for p in plugins if p.event_type in allowed_events]

        if not plugins:
            click.echo(f"⚠️  观景台 {viewpoint_id} 没有配置 sunrise/sunset capability")
            return

        # 获取天气数据（复用 scheduler 内部逻辑）
        result = scheduler.run(viewpoint_id, days=days)

        # 然后对每天用 debug_score 重新诊断
        astro = AstroUtils()
        today = _DateTime.now(
            tz=__import__("datetime").timezone(timedelta(hours=8))
        ).date()

        all_debug: list[dict] = []
        for day_offset in range(days):
            target_date = today + timedelta(days=day_offset)
            target_date_str = target_date.isoformat()

            # 取当天本地天气
            local_weather = scheduler._fetcher.fetch_hourly(
                lat=viewpoint.location.lat,
                lon=viewpoint.location.lon,
                days=days,
            )
            day_weather = local_weather[
                local_weather["forecast_date"] == target_date_str
            ].copy()

            if day_weather.empty:
                all_debug.append({
                    "date": target_date_str,
                    "events": [{"event_type": p.event_type, "decision": "rejected",
                                "reason": "无天气数据"} for p in plugins],
                })
                continue

            # 天文数据
            sun_events = astro.get_sun_events(
                viewpoint.location.lat,
                viewpoint.location.lon,
                target_date,
            )

            # 目标天气
            target_weather: dict[str, __import__("pandas").DataFrame] = {}
            if viewpoint.targets:
                import pandas as pd
                fetcher = scheduler._fetcher
                for target in viewpoint.targets:
                    try:
                        tw = fetcher.fetch_hourly(
                            lat=target.lat, lon=target.lon, days=days,
                        )
                        day_tw = tw[tw["forecast_date"] == target_date_str].copy()
                        if not day_tw.empty:
                            target_weather[target.name] = day_tw
                    except Exception:
                        pass

            # 光路天气 (简化: 使用 None，debug_score 会跳过)
            from gmp.scoring.models import DataContext
            ctx = DataContext(
                date=target_date,
                viewpoint=viewpoint,
                local_weather=day_weather,
                sun_events=sun_events,
                target_weather=target_weather if target_weather else None,
                light_path_weather=None,
            )

            day_results = []
            for plugin in plugins:
                diag = plugin.debug_score(ctx)
                diag["date"] = target_date_str
                day_results.append(diag)

            all_debug.append({
                "date": target_date_str,
                "days_ahead": day_offset + 1,
                "events": day_results,
            })

        if output_format == "json":
            import json as _json
            output = {
                "viewpoint_id": viewpoint_id,
                "viewpoint_name": viewpoint.name,
                "diagnostics": all_debug,
            }
            click.echo(_json.dumps(output, ensure_ascii=False, indent=2))
        else:
            _format_debug_table(viewpoint, all_debug)

    except ViewpointNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        raise SystemExit(1)
    except GMPError as e:
        click.echo(f"GMP 错误: {e}", err=True)
        raise SystemExit(3)


def _format_debug_table(viewpoint: object, all_debug: list[dict]) -> None:
    """格式化调试诊断表格输出"""
    click.echo(f"🔍 日照金山诊断: {viewpoint.name} ({viewpoint.id})")
    click.echo("=" * 60)

    for day_data in all_debug:
        days_ahead = day_data.get("days_ahead", "?")
        click.echo(f"\n📅 {day_data['date']} (T+{days_ahead})")

        for event in day_data["events"]:
            et = event["event_type"]
            icon = "🌅" if "sunrise" in et else "🌇"
            click.echo(f"  {icon} {et}:")

            steps = event.get("steps", [])
            for step in steps:
                name = step["step"]
                passed = step.get("passed", False)
                mark = "✅" if passed else "❌"

                if name == "astro_check":
                    if passed:
                        click.echo(
                            f"    {mark} 天文数据: "
                            f"sun_azimuth={step['sun_azimuth']}°"
                        )
                    else:
                        click.echo(f"    {mark} 天文数据: 缺失")

                elif name == "cloud_trigger":
                    click.echo(
                        f"    {mark} 云量触发: "
                        f"平均云量 {step['avg_cloud']}% "
                        f"{'<' if passed else '≥'} "
                        f"阈值 {step['threshold']}%"
                    )

                elif name == "target_match":
                    targets = step.get("targets", [])
                    matched = step["matched_count"]
                    click.echo(
                        f"    {mark} Target 匹配: "
                        f"{matched}/{len(targets)} 个匹配"
                    )
                    for t in targets:
                        t_mark = "✓" if t["matched"] else "✗"
                        ae = t.get("applicable_events")
                        ae_str = (
                            f"显式={ae}" if ae else "自动计算"
                        )
                        click.echo(
                            f"      {t_mark} {t['name']} "
                            f"(bearing={t['bearing']}°, {ae_str})"
                        )

                elif name == "scoring":
                    click.echo(
                        f"    📊 评分: "
                        f"光路={step['s_light']}({step['light_path_cloud']}%), "
                        f"目标={step['s_target']}({step['target_cloud']}%), "
                        f"本地={step['s_local']}({step['local_cloud']}%)"
                    )
                    if step["vetoed"]:
                        dims = ", ".join(step.get("veto_dims", []))
                        click.echo(
                            f"    ❌ 一票否决: {dims} → 总分 0"
                        )
                    else:
                        click.echo(
                            f"    ✅ 总分: {step['total']}"
                        )

            # 如果没有 steps（如无天气数据），显示 reason
            if not steps:
                reason = event.get("reason", "未知")
                click.echo(f"    ❌ {reason}")


if __name__ == "__main__":
    cli()
