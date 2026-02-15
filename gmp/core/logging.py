"""structlog 日志配置 — 项目唯一日志框架。

所有模块必须通过 structlog.get_logger() 获取 logger，
严禁使用 logging.getLogger() 或 print() 进行日志输出。
"""

import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """配置 structlog processors 链。

    参见设计文档 08-operations.md §8.5

    Usage::

        import structlog
        logger = structlog.get_logger()
        logger.info("event_happened", key="value")
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
