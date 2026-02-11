"""CLIFormatter 单元测试

测试用例:
- test_output_not_empty: 有内容输出
- test_no_color_mode: 无 ANSI 转义码
- test_emoji_mapping: 状态 emoji 正确
"""

from __future__ import annotations

import pytest

from gmp.reporter.cli_formatter import CLIFormatter


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

def _make_scheduler_result() -> dict:
    """构造 Scheduler 输出"""
    return {
        "viewpoint": "牛背山",
        "forecast_days": [
            {
                "date": "2026-02-11",
                "confidence": "High",
                "events": [
                    {
                        "event_type": "sunrise_golden_mountain",
                        "display_name": "日照金山",
                        "total_score": 87,
                        "status": "Recommended",
                        "breakdown": {
                            "light_path": {"score": 35, "max": 35},
                            "target_visible": {"score": 32, "max": 40},
                            "local_clear": {"score": 20, "max": 25},
                        },
                    },
                    {
                        "event_type": "stargazing",
                        "display_name": "观星",
                        "total_score": 98,
                        "status": "Perfect",
                        "breakdown": {
                            "base": {"score": 100, "max": 100},
                            "cloud": {"score": -2, "max": 0},
                            "wind": {"score": 0, "max": 0},
                        },
                    },
                ],
            },
            {
                "date": "2026-02-12",
                "confidence": "High",
                "events": [],
            },
        ],
        "meta": {"api_calls": 14, "cache_hits": 2},
    }


# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────

class TestCLIFormatter:
    """CLIFormatter 测试集"""

    def test_output_not_empty(self) -> None:
        """有内容输出"""
        fmt = CLIFormatter(color_enabled=True)
        output = fmt.generate(_make_scheduler_result())
        assert len(output) > 0
        assert "牛背山" in output

    def test_no_color_mode(self) -> None:
        """无 ANSI 转义码"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.generate(_make_scheduler_result())

        # ANSI 转义码以 \033[ 开头
        assert "\033[" not in output

    def test_color_mode_has_ansi(self) -> None:
        """彩色模式包含 ANSI 转义码"""
        fmt = CLIFormatter(color_enabled=True)
        output = fmt.generate(_make_scheduler_result())

        # 应包含 ANSI 转义码
        assert "\033[" in output

    def test_emoji_mapping(self) -> None:
        """状态 emoji 正确"""
        assert CLIFormatter._status_emoji("Perfect") == "🏆"
        assert CLIFormatter._status_emoji("Recommended") == "✅"
        assert CLIFormatter._status_emoji("Possible") == "⚠️"
        assert CLIFormatter._status_emoji("Not Recommended") == "❌"
        assert CLIFormatter._status_emoji("Unknown") == "❓"

    def test_event_emoji_mapping(self) -> None:
        """事件类型 emoji 正确"""
        assert CLIFormatter._event_emoji("sunrise_golden_mountain") == "🌅"
        assert CLIFormatter._event_emoji("stargazing") == "🌌"
        assert CLIFormatter._event_emoji("cloud_sea") == "☁️"
        assert CLIFormatter._event_emoji("frost") == "❄️"
        assert CLIFormatter._event_emoji("snow_tree") == "🌲"
        assert CLIFormatter._event_emoji("ice_icicle") == "🧊"

    def test_score_formatting_colors(self) -> None:
        """分数格式化 — 不同分段颜色"""
        fmt = CLIFormatter(color_enabled=True)

        # Perfect (>=95) → green
        score_95 = fmt._format_score(95)
        assert "95/100" in score_95
        assert "\033[32m" in score_95  # green

        # Recommended (>=80) → cyan
        score_87 = fmt._format_score(87)
        assert "87/100" in score_87
        assert "\033[36m" in score_87  # cyan

        # Possible (>=50) → yellow
        score_67 = fmt._format_score(67)
        assert "67/100" in score_67
        assert "\033[33m" in score_67  # yellow

        # Not Recommended (<50) → red
        score_30 = fmt._format_score(30)
        assert "30/100" in score_30
        assert "\033[31m" in score_30  # red

    def test_no_color_score(self) -> None:
        """无颜色模式下分数不含 ANSI"""
        fmt = CLIFormatter(color_enabled=False)
        score = fmt._format_score(87)
        assert "87/100" in score
        assert "\033[" not in score

    def test_empty_events_shows_no_recommend(self) -> None:
        """无事件日显示不推荐"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.generate(_make_scheduler_result())
        assert "不推荐" in output

    def test_breakdown_in_output(self) -> None:
        """评分明细出现在输出中"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.generate(_make_scheduler_result())
        # breakdown 包含 "light_path: 35/35"
        assert "light_path" in output
        assert "35/35" in output

    def test_title_box(self) -> None:
        """标题框包含观景台名称"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.generate(_make_scheduler_result())
        assert "╔" in output
        assert "╚" in output
        assert "牛背山" in output
