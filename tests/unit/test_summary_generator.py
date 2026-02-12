"""SummaryGenerator 独立单元测试

覆盖所有分支路径:
- 无事件 → "不推荐 — 全天降水"
- 仅 Perfect → "极佳观景日"
- 仅 Recommended → "推荐出行"
- 仅 Possible → "部分景观可见"
- 全部 Not Recommended → "不推荐 — 无优质景观"
- 混合状态 → Perfect 优先
- 无效模式 → ValueError
"""

from __future__ import annotations

import pytest

from gmp.reporter.summary_generator import SummaryGenerator


class TestSummaryGenerator:
    """SummaryGenerator 测试集"""

    def setup_method(self) -> None:
        self.gen = SummaryGenerator(mode="rule")

    def test_no_events(self) -> None:
        """无事件 → 不推荐"""
        text, mode = self.gen.generate([])
        assert mode == "rule"
        assert "不推荐" in text
        assert "全天降水" in text

    def test_perfect_events(self) -> None:
        """仅 Perfect 事件 → 极佳观景日"""
        events = [
            {"event_type": "stargazing", "total_score": 98, "status": "Perfect"},
            {"event_type": "cloud_sea", "total_score": 95, "status": "Perfect"},
        ]
        text, mode = self.gen.generate(events)
        assert mode == "rule"
        assert "极佳观景日" in text
        assert "完美暗夜" in text
        assert "壮观云海" in text

    def test_recommended_only(self) -> None:
        """仅 Recommended 事件 → 推荐出行"""
        events = [
            {"event_type": "sunrise_golden_mountain", "total_score": 87,
             "status": "Recommended"},
        ]
        text, mode = self.gen.generate(events)
        assert "推荐出行" in text
        assert "日照金山" in text

    def test_possible_only(self) -> None:
        """仅 Possible 事件 → 部分景观可见"""
        events = [
            {"event_type": "frost", "total_score": 55, "status": "Possible"},
        ]
        text, mode = self.gen.generate(events)
        assert "部分景观可见" in text
        assert "雾凇" in text

    def test_all_not_recommended(self) -> None:
        """全部 Not Recommended → 不推荐 — 无优质景观"""
        events = [
            {"event_type": "frost", "total_score": 30, "status": "Not Recommended"},
            {"event_type": "cloud_sea", "total_score": 20, "status": "Not Recommended"},
        ]
        text, mode = self.gen.generate(events)
        assert "不推荐" in text
        assert "无优质景观" in text

    def test_mixed_events_perfect_first(self) -> None:
        """混合状态 — Perfect 优先"""
        events = [
            {"event_type": "frost", "total_score": 55, "status": "Possible"},
            {"event_type": "stargazing", "total_score": 98, "status": "Perfect"},
            {"event_type": "sunrise_golden_mountain", "total_score": 87,
             "status": "Recommended"},
        ]
        text, mode = self.gen.generate(events)
        assert "极佳观景日" in text
        # 确认事件名按 Perfect → Recommended → Possible 排列
        assert "完美暗夜" in text
        assert "日照金山" in text
        assert "雾凇" in text

    def test_invalid_mode(self) -> None:
        """无效模式 → ValueError"""
        with pytest.raises(ValueError, match="不支持的模式"):
            SummaryGenerator(mode="invalid")

    def test_llm_mode_fallback(self) -> None:
        """LLM 模式降级为规则模式"""
        gen = SummaryGenerator(mode="llm")
        events = [
            {"event_type": "cloud_sea", "total_score": 95, "status": "Perfect"},
        ]
        text, mode = gen.generate(events)
        assert mode == "llm"
        # 内容仍由规则生成
        assert "极佳观景日" in text

    def test_event_display_names(self) -> None:
        """每种事件类型的中文展示名正确"""
        event_types = [
            ("sunrise_golden_mountain", "日照金山"),
            ("sunset_golden_mountain", "日落金山"),
            ("stargazing", "完美暗夜"),
            ("cloud_sea", "壮观云海"),
            ("frost", "雾凇"),
            ("snow_tree", "树挂积雪"),
            ("ice_icicle", "冰挂"),
        ]
        for etype, display in event_types:
            events = [{"event_type": etype, "total_score": 95, "status": "Perfect"}]
            text, _ = self.gen.generate(events)
            assert display in text, f"事件 {etype} 应显示为 {display}"
