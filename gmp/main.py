"""GMP 应用入口 — API 服务 + CLI 预测双模式

用法:
  # CLI 预测
  python -m gmp.main predict niubei_gongga --days 3 --events cloud_sea,frost

  # API 服务
  python -m gmp.main serve --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# gmp 包目录
_GMP_DIR = Path(__file__).resolve().parent


def _run_predict(args: argparse.Namespace) -> None:
    """CLI 预测模式"""
    from gmp.astro.astro_utils import AstroUtils
    from gmp.core.config_loader import EngineConfig, ViewpointConfig
    from gmp.core.log_config import setup_logging
    from gmp.core.scheduler import GMPScheduler
    from gmp.fetcher.meteo_fetcher import MeteoFetcher
    from gmp.reporter.cli_formatter import CLIFormatter
    from gmp.reporter.forecast_reporter import ForecastReporter
    from gmp.scorer.engine import create_default_engine

    # 加载配置
    config = EngineConfig.from_yaml(_GMP_DIR / "config" / "engine_config.yaml")

    # 初始化日志 (使用配置)
    setup_logging(level=config.log_level, fmt=config.log_format)

    viewpoint_config = ViewpointConfig()
    viewpoint_config.load(_GMP_DIR / "config" / "viewpoints")

    # 初始化缓存层
    from gmp.cache.memory_cache import MemoryCache
    from gmp.cache.repository import CacheRepository
    from gmp.cache.weather_cache import WeatherCache

    memory_cache = MemoryCache(ttl_seconds=config.memory_cache_ttl_seconds)
    repository = CacheRepository(db_path=config.db_path)
    cache = WeatherCache(
        memory_cache=memory_cache,
        repository=repository,
        ttl_db_seconds=config.db_cache_ttl_seconds,
    )

    # 初始化依赖
    fetcher = MeteoFetcher(cache=cache)
    astro = AstroUtils()

    # 使用工厂函数注册全部 Plugin (C5: 消除重复)
    score_engine = create_default_engine(config)

    scheduler = GMPScheduler(
        config=config,
        viewpoint_config=viewpoint_config,
        fetcher=fetcher,
        astro=astro,
        score_engine=score_engine,
    )

    # 解析 events
    events_list: list[str] | None = None
    if args.events:
        events_list = [e.strip() for e in args.events.split(",") if e.strip()]

    # 运行预测
    result = scheduler.run(
        viewpoint_id=args.viewpoint_id,
        days=args.days,
        events=events_list,
    )

    # 输出
    if args.json:
        reporter = ForecastReporter()
        report = reporter.generate(result)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        formatter = CLIFormatter(color_enabled=not args.no_color)
        output = formatter.generate(result)
        print(output)


def _run_serve(args: argparse.Namespace) -> None:
    """API 服务模式"""
    try:
        import uvicorn
    except ImportError:
        print("错误: 需要安装 uvicorn，请执行 pip install uvicorn")
        sys.exit(1)

    print(f"🚀 GMP API 服务启动中 → http://{args.host}:{args.port}")
    print("   按 Ctrl+C 停止")

    uvicorn.run(
        "gmp.api.routes:get_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=False,
    )


def main() -> None:
    """应用入口"""
    parser = argparse.ArgumentParser(
        description="GMP 景观预测引擎 — 川西旅行景观预测工具",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ---- CLI 预测模式 ----
    cli_parser = subparsers.add_parser("predict", help="运行景观预测")
    cli_parser.add_argument("viewpoint_id", help="观景台 ID")
    cli_parser.add_argument(
        "--days", type=int, default=7, help="预测天数 (1-7, 默认 7)"
    )
    cli_parser.add_argument(
        "--events", type=str, default=None,
        help="逗号分隔的事件类型过滤 (如 cloud_sea,frost)",
    )
    cli_parser.add_argument(
        "--no-color", action="store_true", help="禁用终端颜色输出",
    )
    cli_parser.add_argument(
        "--json", action="store_true", help="输出 JSON 格式 (而非 CLI 彩色)",
    )
    cli_parser.set_defaults(func=_run_predict)

    # ---- API 服务模式 ----
    api_parser = subparsers.add_parser("serve", help="启动 REST API 服务")
    api_parser.add_argument(
        "--host", default="0.0.0.0", help="监听地址 (默认 0.0.0.0)"
    )
    api_parser.add_argument(
        "--port", type=int, default=8000, help="监听端口 (默认 8000)"
    )
    api_parser.set_defaults(func=_run_serve)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
