"""structlog 日志配置 — 项目唯一日志框架。

所有模块必须通过 structlog.get_logger() 获取 logger，
严禁使用 logging.getLogger() 或 print() 进行日志输出。
"""

import io
import logging
import sys

import structlog


# structlog log level 名 → Python logging 数值
_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def _make_log_filter(min_level: str):
    """创建一个 structlog processor，过滤低于 min_level 的事件。"""
    threshold = _LEVEL_MAP.get(min_level.lower(), logging.INFO)

    def _filter(logger, method_name, event_dict):
        level = _LEVEL_MAP.get(method_name, logging.DEBUG)
        if level < threshold:
            raise structlog.DropEvent
        return event_dict

    return _filter


class _StderrLoggerFactory:
    """每次调用时解析当前 sys.stderr，避免持有已关闭的 file 引用。"""

    def __call__(self, *args, **kwargs):
        try:
            f = sys.stderr
            if f is None or f.closed:
                f = io.StringIO()  # fallback: 丢弃日志
        except Exception:
            f = io.StringIO()
        return structlog.PrintLogger(file=f)


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
            _make_log_filter(log_level),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=_StderrLoggerFactory(),
        cache_logger_on_first_use=False,
    )


