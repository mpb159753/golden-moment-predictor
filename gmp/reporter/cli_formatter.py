"""CLIFormatter — 终端彩色格式化输出

以 ANSI 彩色文本在终端展示预测结果，支持 --no-color 模式。

设计依据:
- implementation-plans/module-08-reporter.md
- design/06-class-sequence.md §6.4
"""

from __future__ import annotations

from gmp.reporter.base import BaseReporter

# ANSI 颜色码
_COLORS = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "dim":     "\033[2m",
}


class CLIFormatter(BaseReporter):
    """终端彩色格式化输出"""

    def __init__(self, color_enabled: bool = True) -> None:
        self._color = color_enabled

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def generate(self, scheduler_result: dict) -> str:
        """生成终端友好的格式化文本

        示例:
        ╔══════════════════════════════════════╗
        ║     🏔️ 牛背山 · 7日景观预测         ║
        ╚══════════════════════════════════════╝

        📅 2026-02-11 (High)
        ────────────────────
        🌅 日照金山  ⭐ 87/100  ✅ Recommended
           光路: 35/35  目标: 32/40  本地: 20/25
        🌌 观星     ⭐ 98/100  🏆 Perfect
           基准: 100  云量: -2  风速: 0
        """
        viewpoint = scheduler_result.get("viewpoint", "未知")
        forecast_days = scheduler_result.get("forecast_days", [])
        days_count = len(forecast_days)

        lines: list[str] = []

        # 标题框
        title = f"🏔️  {viewpoint} · {days_count}日景观预测"
        box_width = max(38, len(title) + 6)
        lines.append(self._colorize(f"╔{'═' * box_width}╗", "cyan"))
        lines.append(self._colorize(f"║  {title:^{box_width - 4}}  ║", "cyan"))
        lines.append(self._colorize(f"╚{'═' * box_width}╝", "cyan"))
        lines.append("")

        # 每日预测
        for day in forecast_days:
            date_str = day.get("date", "")
            confidence = day.get("confidence", "")
            events = day.get("events", [])

            # 日期行
            conf_color = {"High": "green", "Medium": "yellow", "Low": "red"}.get(
                confidence, "white"
            )
            lines.append(
                f"📅 {self._colorize(date_str, 'bold')}"
                f" ({self._colorize(confidence, conf_color)})"
            )
            lines.append(self._colorize("─" * 30, "dim"))

            if not events:
                lines.append(
                    f"   {self._colorize('❌ 不推荐 — 无优质景观', 'red')}"
                )
                lines.append("")
                continue

            for ev in events:
                event_type = ev.get("event_type", "")
                display_name = ev.get("display_name", event_type)
                score = ev.get("total_score", 0)
                status = ev.get("status", "")
                breakdown = ev.get("breakdown", {})

                emoji = self._event_emoji(event_type)
                status_icon = self._status_emoji(status)
                score_str = self._format_score(score)

                lines.append(
                    f"   {emoji} {display_name:<8} ⭐ {score_str}"
                    f"  {status_icon} {status}"
                )

                # breakdown 明细
                if breakdown:
                    dims: list[str] = []
                    for dim, val in breakdown.items():
                        if isinstance(val, dict):
                            s = val.get("score", 0)
                            m = val.get("max", 0)
                            dims.append(f"{dim}: {s}/{m}")
                        else:
                            dims.append(f"{dim}: {val}")
                    detail_line = "  ".join(dims)
                    lines.append(
                        f"      {self._colorize(detail_line, 'dim')}"
                    )

            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 格式化辅助
    # ------------------------------------------------------------------

    def _format_score(self, score: int) -> str:
        """分数格式化 + 颜色"""
        text = f"{score}/100"
        if score >= 95:
            return self._colorize(text, "green")
        if score >= 80:
            return self._colorize(text, "cyan")
        if score >= 50:
            return self._colorize(text, "yellow")
        return self._colorize(text, "red")

    def _colorize(self, text: str, level: str) -> str:
        """ANSI 颜色包装

        当 color_enabled=False 时返回纯文本。
        """
        if not self._color:
            return text
        code = _COLORS.get(level, "")
        reset = _COLORS["reset"]
        if not code:
            return text
        return f"{code}{text}{reset}"

    @staticmethod
    def _status_emoji(status: str) -> str:
        """状态对应 emoji

        Perfect     → 🏆
        Recommended → ✅
        Possible    → ⚠️
        Not Recommended → ❌
        """
        return {
            "Perfect": "🏆",
            "Recommended": "✅",
            "Possible": "⚠️",
            "Not Recommended": "❌",
        }.get(status, "❓")

    @staticmethod
    def _event_emoji(event_type: str) -> str:
        """事件类型对应 emoji"""
        return {
            "sunrise_golden_mountain": "🌅",
            "sunset_golden_mountain": "🌇",
            "stargazing": "🌌",
            "cloud_sea": "☁️",
            "frost": "❄️",
            "snow_tree": "🌲",
            "ice_icicle": "🧊",
        }.get(event_type, "🔮")
