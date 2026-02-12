"""CLIFormatter — 终端彩色格式化输出

以 ANSI 彩色文本在终端展示预测结果，支持 --no-color 模式。

设计依据:
- implementation-plans/module-08-reporter.md
- design/06-class-sequence.md §6.4
"""

from __future__ import annotations

import unicodedata

from gmp.reporter.base import BaseReporter
from gmp.scorer.plugin import score_to_status  # 复用评分分段逻辑

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
        box_width = max(38, _display_width(title) + 6)
        lines.append(self._colorize(f"╔{'═' * box_width}╗", "cyan"))
        # 使用显示宽度居中
        pad = box_width - 4 - _display_width(title)
        left_pad = pad // 2
        right_pad = pad - left_pad
        lines.append(self._colorize(
            f"║  {' ' * left_pad}{title}{' ' * right_pad}  ║", "cyan"
        ))
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

                # CJK 对齐: 目标显示宽度 8 列
                name_width = _display_width(display_name)
                pad = max(0, 8 - name_width)
                lines.append(
                    f"   {emoji} {display_name}{' ' * pad} ⭐ {score_str}"
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
        """分数格式化 + 颜色

        颜色分段与 score_to_status (plugin.py) 保持一致:
        >=95 green, >=80 cyan, >=50 yellow, <50 red
        """
        text = f"{score}/100"
        status = score_to_status(score)
        color_map = {
            "Perfect": "green",
            "Recommended": "cyan",
            "Possible": "yellow",
            "Not Recommended": "red",
        }
        return self._colorize(text, color_map.get(status, "white"))

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


# ======================================================================
# 模块级辅助函数
# ======================================================================

def _display_width(text: str) -> int:
    """计算字符串在终端中的实际显示宽度

    CJK 字符和全角符号占 2 列宽度，其余占 1 列。
    ANSI 转义序列不计入宽度。
    """
    width = 0
    in_escape = False
    for ch in text:
        if ch == "\033":
            in_escape = True
            continue
        if in_escape:
            if ch == "m":
                in_escape = False
            continue
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("W", "F") else 1
    return width
