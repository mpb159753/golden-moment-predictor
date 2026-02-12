"""GMP 输出层 — Reporter + CLI

提供三种输出器:
- ForecastReporter: JSON 推荐事件输出
- TimelineReporter: JSON 逐小时时间轴
- CLIFormatter: 终端彩色格式化输出

以及辅助组件:
- SummaryGenerator: 每日摘要生成器
- BaseReporter: 输出层抽象基类
"""

from gmp.reporter.base import BaseReporter
from gmp.reporter.cli_formatter import CLIFormatter
from gmp.reporter.forecast_reporter import ForecastReporter
from gmp.reporter.summary_generator import SummaryGenerator
from gmp.reporter.timeline_reporter import TimelineReporter

__all__ = [
    "BaseReporter",
    "CLIFormatter",
    "ForecastReporter",
    "SummaryGenerator",
    "TimelineReporter",
]
