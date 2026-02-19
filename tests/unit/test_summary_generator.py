"""tests/unit/test_summary_generator.py — SummaryGenerator 单元测试"""

from __future__ import annotations

import pytest

from gmp.core.models import ScoreResult
from gmp.output.summary_generator import SummaryGenerator


# 测试用显示名称映射（模拟 Plugin.display_name 提供的翻译）
_DISPLAY_NAMES: dict[str, str] = {
    "sunrise_golden_mountain": "日出金山",
    "sunset_golden_mountain": "日落金山",
    "cloud_sea": "云海",
    "stargazing": "观星",
    "frost": "雾凇",
    "clear_sky": "晴天",
    "snow_tree": "树挂积雪",
    "ice_icicle": "冰挂",
}


def _make_event(
    event_type: str = "cloud_sea",
    score: int = 85,
    status: str = "Recommended",
) -> ScoreResult:
    """构造最小 ScoreResult 用于测试"""
    return ScoreResult(
        event_type=event_type,
        total_score=score,
        status=status,
        breakdown={},
    )


class TestSummaryGeneratorEmptyEvents:
    """空事件列表 → 不推荐摘要"""

    def test_empty_events_returns_not_recommended(self) -> None:
        gen = SummaryGenerator()
        result = gen.generate([])
        assert "不推荐" in result


class TestSummaryGeneratorPerfectEvent:
    """有 Perfect 事件 → 完美观景日"""

    def test_single_perfect_event_contains_event_name(self) -> None:
        gen = SummaryGenerator(display_names=_DISPLAY_NAMES)
        events = [_make_event("sunrise_golden_mountain", 96, "Perfect")]
        result = gen.generate(events)
        assert "完美" in result
        assert "日出金山" in result


class TestSummaryGeneratorRecommended:
    """多个 Recommended → 列出 top 事件"""

    def test_multiple_recommended_lists_top_events(self) -> None:
        gen = SummaryGenerator(display_names=_DISPLAY_NAMES)
        events = [
            _make_event("cloud_sea", 90, "Recommended"),
            _make_event("sunrise_golden_mountain", 85, "Recommended"),
            _make_event("frost", 80, "Recommended"),
        ]
        result = gen.generate(events)
        assert "推荐" in result
        assert "云海" in result
        assert "日出金山" in result


class TestSummaryGeneratorPossibleOnly:
    """仅 Possible → 措辞保守"""

    def test_only_possible_events_conservative_wording(self) -> None:
        gen = SummaryGenerator()
        events = [
            _make_event("frost", 60, "Possible"),
            _make_event("cloud_sea", 55, "Possible"),
        ]
        result = gen.generate(events)
        assert "可能" in result
        # 不应包含 "完美" 或 "推荐"
        assert "完美" not in result


class TestSummaryGeneratorAllNotRecommended:
    """所有事件均 Not Recommended → 不推荐"""

    def test_all_not_recommended(self) -> None:
        gen = SummaryGenerator()
        events = [
            _make_event("frost", 30, "Not Recommended"),
            _make_event("cloud_sea", 20, "Not Recommended"),
        ]
        result = gen.generate(events)
        assert "不推荐" in result
