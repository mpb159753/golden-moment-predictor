"""GMP 日志配置 — 使用 structlog 统一全项目日志

设计依据: design/08-operations.md §8.4-8.5

配置项由 engine_config.yaml 的 logging 段控制:
  logging:
    level: "INFO"       # DEBUG / INFO / WARNING / ERROR
    format: "console"   # console / json
"""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(level: str = "INFO", fmt: str = "console") -> None:
    """初始化 structlog + 标准 logging 的统一配置

    Args:
        level: 日志级别 (DEBUG / INFO / WARNING / ERROR)
        fmt: 输出格式 ("console" = 彩色终端, "json" = JSON 行)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # structlog 处理器链
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if fmt == "json":
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 标准 logging 的 formatter 使用 structlog 的处理器
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
