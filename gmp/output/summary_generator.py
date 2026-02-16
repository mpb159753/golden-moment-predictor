"""gmp/output/summary_generator.py — 文字摘要生成器

根据评分事件列表生成单日文字摘要。
"""

from __future__ import annotations

from gmp.core.models import ScoreResult

# event_type → 中文显示名称
EVENT_DISPLAY_NAMES: dict[str, str] = {
    "sunrise_golden_mountain": "日出金山",
    "sunset_golden_mountain": "日落金山",
    "cloud_sea": "云海",
    "stargazing": "观星",
    "frost": "雾凇",
    "snow_tree": "树挂积雪",
    "ice_icicle": "冰挂",
}


class SummaryGenerator:
    """基于规则的文字摘要生成器"""

    def __init__(self, mode: str = "rule") -> None:
        self._mode = mode

    def generate(self, events: list[ScoreResult]) -> str:
        """基于事件列表生成单日文字摘要

        规则:
        - 无事件 → "不推荐 — 条件不佳"
        - 所有事件 Not Recommended → "不推荐 — 条件不佳"
        - 有 Perfect → "完美观景日 — {top_events}"
        - 有 Recommended → "推荐观景 — {top_events}"
        - 仅 Possible → "可能可见 — {top_events}"
        """
        if not events:
            return "不推荐 — 条件不佳"

        # 按分数降序排列
        sorted_events = sorted(
            events, key=lambda e: e.total_score, reverse=True
        )

        # 收集各等级
        statuses = {e.status for e in sorted_events}

        # 取 top 事件名称 (最多 3 个)
        top_names = self._top_event_names(sorted_events, max_count=3)

        if "Perfect" in statuses:
            return f"完美观景日 — {top_names}"
        elif "Recommended" in statuses:
            return f"推荐观景 — {top_names}"
        elif "Possible" in statuses:
            return f"可能可见 — {top_names}"
        else:
            return "不推荐 — 条件不佳"

    def _top_event_names(
        self, sorted_events: list[ScoreResult], max_count: int = 3
    ) -> str:
        """取前 N 个事件的显示名称，用 + 连接"""
        names: list[str] = []
        for event in sorted_events[:max_count]:
            name = EVENT_DISPLAY_NAMES.get(event.event_type, event.event_type)
            names.append(name)
        return "+".join(names)
