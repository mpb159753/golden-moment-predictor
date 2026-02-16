"""gmp/output/cli_formatter.py — 终端格式化输出

将 PipelineResult 转换为终端可读的表格和详细输出。
"""

from __future__ import annotations

from gmp.core.models import PipelineResult, ScoreResult
from gmp.output.summary_generator import EVENT_DISPLAY_NAMES


# ANSI 颜色码
_COLORS = {
    "Perfect": "\033[95m",       # 亮品红
    "Recommended": "\033[92m",   # 亮绿
    "Possible": "\033[93m",      # 亮黄
    "Not Recommended": "\033[91m",  # 亮红
}
_RESET = "\033[0m"


class CLIFormatter:
    """终端格式化输出"""

    def __init__(self, color_enabled: bool = True) -> None:
        self._color = color_enabled

    def format_forecast(self, result: PipelineResult) -> str:
        """生成终端表格输出"""
        lines: list[str] = []
        header = f"📍 {result.viewpoint.name} ({result.viewpoint.id})"
        lines.append(header)
        lines.append("=" * 60)

        for day in result.forecast_days:
            lines.append(f"\n📅 {day.date}  {day.summary}")
            lines.append("-" * 60)
            lines.append(
                f"{'事件':<25} {'分数':>5}  {'状态':<20}"
            )
            lines.append("-" * 60)

            sorted_events = sorted(
                day.events, key=lambda e: e.total_score, reverse=True
            )
            for event in sorted_events:
                display = EVENT_DISPLAY_NAMES.get(
                    event.event_type, event.event_type
                )
                status = self._colorize_status(event.status)
                lines.append(
                    f"{display:<25} {event.total_score:>5}  "
                    f"{status}"
                )

        lines.append("")
        return "\n".join(lines)

    def format_detail(self, result: PipelineResult) -> str:
        """生成详细输出 (含 score_breakdown)"""
        lines: list[str] = []
        header = f"📍 {result.viewpoint.name} ({result.viewpoint.id})"
        lines.append(header)
        lines.append("=" * 60)

        for day in result.forecast_days:
            lines.append(f"\n📅 {day.date}  {day.summary}")
            lines.append("-" * 60)

            sorted_events = sorted(
                day.events, key=lambda e: e.total_score, reverse=True
            )
            for event in sorted_events:
                display = EVENT_DISPLAY_NAMES.get(
                    event.event_type, event.event_type
                )
                status = self._colorize_status(event.status)
                lines.append(
                    f"\n  🎯 {display}  "
                    f"Score: {event.total_score}  {status}"
                )
                if event.time_window:
                    lines.append(f"     ⏰ {event.time_window}")

                # breakdown 详情
                if event.breakdown:
                    lines.append("     📊 Breakdown:")
                    for dim, vals in event.breakdown.items():
                        score = vals.get("score", 0)
                        max_val = vals.get("max", 0)
                        lines.append(
                            f"        {dim}: {score}/{max_val}"
                        )

        lines.append("")
        return "\n".join(lines)

    def _colorize_status(self, status: str) -> str:
        """根据 status 着色"""
        if not self._color:
            return status
        color = _COLORS.get(status, "")
        if color:
            return f"{color}{status}{_RESET}"
        return status
