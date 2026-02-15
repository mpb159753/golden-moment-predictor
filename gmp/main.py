"""GMP CLI 入口 — 占位模块，将在 M14 中实现完整功能。"""

import click

from gmp.core.logging import setup_logging


@click.group()
@click.option("--log-level", default="INFO", help="日志级别")
def cli(log_level: str) -> None:
    """GMP — 川西旅行景观预测引擎。"""
    setup_logging(log_level)


if __name__ == "__main__":
    cli()
