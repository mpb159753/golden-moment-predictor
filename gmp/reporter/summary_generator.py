"""SummaryGenerator — 每日摘要生成器

基于规则或 LLM 生成当日景观摘要。
初期仅实现 rule 模式；llm 模式预留接口。

设计依据: implementation-plans/module-08-reporter.md
"""

from __future__ import annotations

# 事件类型 → 中文展示名映射
_EVENT_DISPLAY_NAMES: dict[str, str] = {
    "sunrise_golden_mountain": "日照金山",
    "sunset_golden_mountain": "日落金山",
    "stargazing": "完美暗夜",
    "cloud_sea": "壮观云海",
    "frost": "雾凇",
    "snow_tree": "树挂积雪",
    "ice_icicle": "冰挂",
}


class SummaryGenerator:
    """每日摘要生成器"""

    def __init__(self, mode: str = "rule") -> None:
        """
        Args:
            mode: 摘要生成模式 ("rule" | "llm")
        """
        if mode not in ("rule", "llm"):
            raise ValueError(f"不支持的模式: {mode}，仅支持 'rule' 或 'llm'")
        self._mode = mode

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def generate(self, events: list[dict]) -> tuple[str, str]:
        """生成每日摘要

        Args:
            events: 当日事件列表，每个事件包含:
                - event_type: str
                - total_score: int
                - status: str  ("Perfect" | "Recommended" | "Possible" | "Not Recommended")

        Returns:
            (summary_text, mode)
            mode 固定为 "rule" 或 "llm"
        """
        if self._mode == "rule":
            return self._rule_based(events), "rule"
        return self._llm_enhanced(events), "llm"

    # ------------------------------------------------------------------
    # 规则模式
    # ------------------------------------------------------------------

    def _rule_based(self, events: list[dict]) -> str:
        """基于规则生成摘要

        逻辑:
        1. 统计 Perfect + Recommended 的事件
        2. 拼接事件中文名称
        3. 添加前缀:
           - 有 Perfect 事件 → "极佳观景日"
           - 仅有 Recommended → "推荐出行"
           - 仅有 Possible → "部分景观可见"
           - 无事件 → "不推荐 — 全天降水"
        """
        if not events:
            return "不推荐 — 全天降水"

        # 分类事件
        perfect: list[str] = []
        recommended: list[str] = []
        possible: list[str] = []

        for ev in events:
            status = ev.get("status", "")
            event_type = ev.get("event_type", "")
            display = _EVENT_DISPLAY_NAMES.get(event_type, event_type)

            if status == "Perfect":
                perfect.append(display)
            elif status == "Recommended":
                recommended.append(display)
            elif status == "Possible":
                possible.append(display)
            # "Not Recommended" 不纳入摘要

        # 优先展示高等级事件
        highlights = perfect + recommended + possible

        if not highlights:
            return "不推荐 — 无优质景观"

        event_names = "+".join(highlights)

        if perfect:
            prefix = "极佳观景日"
        elif recommended:
            prefix = "推荐出行"
        else:
            prefix = "部分景观可见"

        return f"{prefix} — {event_names}"

    # ------------------------------------------------------------------
    # LLM 模式 (预留)
    # ------------------------------------------------------------------

    def _llm_enhanced(self, events: list[dict]) -> str:
        """LLM 增强摘要 — 预留接口

        TODO: 集成 LLM API，基于事件详情生成更自然的摘要语言。
        当前降级为规则模式。
        """
        return self._rule_based(events)
