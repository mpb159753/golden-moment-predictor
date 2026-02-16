"""tests/unit/test_cli_formatter.py — CLIFormatter 单元测试"""

from __future__ import annotations

from gmp.core.models import (
    ForecastDay,
    Location,
    PipelineResult,
    ScoreResult,
    Viewpoint,
)
from gmp.output.cli_formatter import CLIFormatter


# ── helpers ──


def _make_event(
    event_type: str = "cloud_sea",
    score: int = 85,
    status: str = "Recommended",
    time_window: str = "06:00 - 09:00",
    breakdown: dict | None = None,
) -> ScoreResult:
    return ScoreResult(
        event_type=event_type,
        total_score=score,
        status=status,
        breakdown=breakdown or {"gap": {"score": 50, "max": 50}},
        time_window=time_window,
        confidence="High",
    )


def _make_viewpoint() -> Viewpoint:
    return Viewpoint(
        id="niubei_gongga",
        name="牛背山",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["sunrise", "cloud_sea"],
        targets=[],
    )


def _make_pipeline_result(
    events: list[ScoreResult] | None = None,
    date_str: str = "2026-02-12",
) -> PipelineResult:
    if events is None:
        events = [
            _make_event("cloud_sea", 90, "Recommended"),
            _make_event("sunrise_golden_mountain", 85, "Recommended"),
        ]
    day = ForecastDay(
        date=date_str,
        summary="推荐观景 — 云海+日出金山",
        best_event=events[0] if events else None,
        events=events,
        confidence="High",
    )
    return PipelineResult(
        viewpoint=_make_viewpoint(),
        forecast_days=[day],
        meta={
            "generated_at": "2026-02-12T05:00:00+08:00",
            "engine_version": "4.0.0",
        },
    )


# ── format_forecast 测试 ──


class TestCLIFormatterFormatForecast:
    """format_forecast() — 终端表格输出"""

    def test_output_contains_date(self) -> None:
        """输出包含日期"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.format_forecast(_make_pipeline_result())
        assert "2026-02-12" in output

    def test_output_contains_display_name(self) -> None:
        """输出包含中文显示名称"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.format_forecast(_make_pipeline_result())
        assert "云海" in output

    def test_output_contains_score(self) -> None:
        """输出包含分数"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.format_forecast(_make_pipeline_result())
        assert "90" in output

    def test_output_contains_status(self) -> None:
        """输出包含状态"""
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.format_forecast(_make_pipeline_result())
        assert "Recommended" in output


# ── 颜色着色测试 ──


class TestCLIFormatterColorize:
    """不同 status 的着色"""

    def test_perfect_has_color_escape(self) -> None:
        """Perfect 状态有颜色转义序列"""
        fmt = CLIFormatter(color_enabled=True)
        colored = fmt._colorize_status("Perfect")
        assert "\033[" in colored
        assert "Perfect" in colored

    def test_recommended_has_color_escape(self) -> None:
        fmt = CLIFormatter(color_enabled=True)
        colored = fmt._colorize_status("Recommended")
        assert "\033[" in colored

    def test_possible_has_color_escape(self) -> None:
        fmt = CLIFormatter(color_enabled=True)
        colored = fmt._colorize_status("Possible")
        assert "\033[" in colored

    def test_not_recommended_has_color_escape(self) -> None:
        fmt = CLIFormatter(color_enabled=True)
        colored = fmt._colorize_status("Not Recommended")
        assert "\033[" in colored

    def test_different_statuses_have_different_colors(self) -> None:
        """不同状态使用不同颜色"""
        fmt = CLIFormatter(color_enabled=True)
        perfect = fmt._colorize_status("Perfect")
        recommended = fmt._colorize_status("Recommended")
        possible = fmt._colorize_status("Possible")
        not_rec = fmt._colorize_status("Not Recommended")
        # 至少 Perfect 和 Not Recommended 应不同
        assert perfect != not_rec

    def test_color_disabled_no_escape(self) -> None:
        """color_enabled=False 时无转义序列"""
        fmt = CLIFormatter(color_enabled=False)
        plain = fmt._colorize_status("Perfect")
        assert "\033[" not in plain
        assert "Perfect" in plain


# ── format_detail 测试 ──


class TestCLIFormatterFormatDetail:
    """format_detail() — 详细输出含 breakdown"""

    def test_detail_contains_breakdown(self) -> None:
        """detail 模式包含 breakdown 信息"""
        event = _make_event(
            "cloud_sea",
            90,
            "Recommended",
            breakdown={
                "gap": {"score": 50, "max": 50},
                "density": {"score": 20, "max": 30},
            },
        )
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.format_detail(
            _make_pipeline_result(events=[event])
        )
        assert "gap" in output
        assert "density" in output

    def test_detail_contains_score_values(self) -> None:
        """detail 输出包含具体分数值"""
        event = _make_event(
            "cloud_sea",
            90,
            "Recommended",
            breakdown={
                "gap": {"score": 50, "max": 50},
            },
        )
        fmt = CLIFormatter(color_enabled=False)
        output = fmt.format_detail(
            _make_pipeline_result(events=[event])
        )
        assert "50" in output
