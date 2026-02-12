"""ForecastReporter 单元测试

测试用例:
- test_clear_day_output: 晴天输出包含多个事件
- test_rainy_day_output: 雨天 events=[]
- test_score_breakdown_format: score_breakdown 含 score+max
- test_meta_fields: meta.generated_at 为 ISO 8601
"""

from __future__ import annotations

import pytest

from gmp.reporter.forecast_reporter import ForecastReporter
from gmp.reporter.summary_generator import SummaryGenerator


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

def _make_clear_day_result() -> dict:
    """构造晴天 Scheduler 输出 (含 4 个事件)"""
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
                        "time_window": "07:15 - 07:45",
                        "breakdown": {
                            "light_path": {"score": 35, "max": 35, "detail": "10点均值云量8%"},
                            "target_visible": {"score": 32, "max": 40, "detail": "贡嘎高+中云13%"},
                            "local_clear": {"score": 20, "max": 25, "detail": "本地总云22%"},
                        },
                    },
                    {
                        "event_type": "stargazing",
                        "display_name": "观星",
                        "total_score": 98,
                        "status": "Perfect",
                        "time_window": "19:55 - 03:15",
                        "secondary_window": "03:15 - 05:55",
                        "breakdown": {
                            "base": {"score": 100, "max": 100, "detail": "optimal: 完美暗夜"},
                            "cloud": {"score": -2, "max": 0, "detail": "夜间平均云量3%"},
                            "wind": {"score": 0, "max": 0, "detail": "2.8km/h ≤20"},
                        },
                    },
                    {
                        "event_type": "cloud_sea",
                        "display_name": "云海",
                        "total_score": 95,
                        "status": "Perfect",
                        "time_window": "06:00 - 09:00",
                        "breakdown": {
                            "gap": {"score": 50, "max": 50, "detail": "高差1060m > 800m"},
                            "density": {"score": 25, "max": 30, "detail": "低云75%"},
                            "wind": {"score": 20, "max": 20, "detail": "风速2.8km/h"},
                        },
                    },
                    {
                        "event_type": "frost",
                        "display_name": "雾凇",
                        "total_score": 67,
                        "status": "Possible",
                        "time_window": "05:00 - 08:30",
                        "breakdown": {
                            "temperature": {"score": 35, "max": 40, "detail": "-3.8°C"},
                            "moisture": {"score": 5, "max": 30, "detail": "能见度35km"},
                            "wind": {"score": 20, "max": 20, "detail": "2.8km/h"},
                            "cloud": {"score": 7, "max": 10, "detail": "低云75%"},
                        },
                    },
                    {
                        "event_type": "snow_tree",
                        "display_name": "树挂积雪",
                        "total_score": 72,
                        "status": "Possible",
                        "time_window": "06:00 - 14:00",
                        "breakdown": {
                            "snow_signal": {"score": 40, "max": 60, "detail": "近期降雪15cm"},
                            "clear_weather": {"score": 18, "max": 20, "detail": "晴天稳定"},
                            "stability": {"score": 14, "max": 20, "detail": "风递4.2km/h"},
                        },
                    },
                    {
                        "event_type": "ice_icicle",
                        "display_name": "冰挂",
                        "total_score": 60,
                        "status": "Possible",
                        "time_window": "06:00 - 10:00",
                        "breakdown": {
                            "water_input": {"score": 28, "max": 50, "detail": "降水转化尚可"},
                            "freeze_strength": {"score": 20, "max": 30, "detail": "-3.8°C 动力充足"},
                            "view_quality": {"score": 12, "max": 20, "detail": "能见度良好"},
                        },
                    },
                ],
            },
        ],
        "meta": {"api_calls": 14, "cache_hits": 2},
    }


def _make_rainy_day_result() -> dict:
    """构造雨天 Scheduler 输出 (无事件)"""
    return {
        "viewpoint": "牛背山",
        "forecast_days": [
            {
                "date": "2026-02-12",
                "confidence": "High",
                "events": [],
            },
        ],
        "meta": {"api_calls": 1, "cache_hits": 0},
    }


# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────

class TestForecastReporter:
    """ForecastReporter 测试集"""

    def setup_method(self) -> None:
        self.reporter = ForecastReporter()

    def test_clear_day_output(self) -> None:
        """晴天输出包含 6 个事件"""
        result = self.reporter.generate(_make_clear_day_result())

        assert "forecast_days" in result
        assert len(result["forecast_days"]) == 1

        day = result["forecast_days"][0]
        assert day["date"] == "2026-02-11"
        assert day["confidence"] == "High"
        assert len(day["events"]) == 6

        # 验证事件类型
        event_types = [e["type"] for e in day["events"]]
        assert "sunrise_golden_mountain" in event_types
        assert "stargazing" in event_types
        assert "cloud_sea" in event_types
        assert "frost" in event_types
        assert "snow_tree" in event_types
        assert "ice_icicle" in event_types

    def test_rainy_day_output(self) -> None:
        """雨天 events=[]"""
        result = self.reporter.generate(_make_rainy_day_result())

        day = result["forecast_days"][0]
        assert day["events"] == []
        assert "不推荐" in day["summary"]

    def test_score_breakdown_format(self) -> None:
        """score_breakdown 含 score+max"""
        result = self.reporter.generate(_make_clear_day_result())

        day = result["forecast_days"][0]
        golden = day["events"][0]

        assert "score_breakdown" in golden
        for dim, val in golden["score_breakdown"].items():
            assert "score" in val, f"维度 {dim} 缺少 score 字段"
            assert "max" in val, f"维度 {dim} 缺少 max 字段"

    def test_meta_fields(self) -> None:
        """meta.generated_at 为 ISO 8601 格式"""
        result = self.reporter.generate(_make_clear_day_result())

        assert "meta" in result
        meta = result["meta"]
        assert "generated_at" in meta
        # ISO 8601 格式含 'T' 分隔符
        assert "T" in meta["generated_at"]

        assert "cache_stats" in meta
        assert meta["cache_stats"]["api_calls"] == 14

    def test_report_date_present(self) -> None:
        """报告日期存在"""
        result = self.reporter.generate(_make_clear_day_result())
        assert "report_date" in result
        assert len(result["report_date"]) == 10  # "YYYY-MM-DD"

    def test_viewpoint_name(self) -> None:
        """viewpoint 名称正确传递"""
        result = self.reporter.generate(_make_clear_day_result())
        assert result["viewpoint"] == "牛背山"

    def test_summary_generation(self) -> None:
        """摘要生成 — 晴天应包含事件列表"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]
        assert day["summary_mode"] == "rule"
        # 有 Perfect 事件，摘要前缀应为 "极佳观景日"
        assert "极佳观景日" in day["summary"]

    def test_secondary_window_passthrough(self) -> None:
        """观星事件的 secondary_window 正确传递"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]

        stargazing = [e for e in day["events"] if e["type"] == "stargazing"][0]
        assert "secondary_window" in stargazing
        assert stargazing["secondary_window"] == "03:15 - 05:55"

    def test_multi_day_output(self) -> None:
        """多日输出 — 混合晴天和雨天"""
        data = _make_clear_day_result()
        data["forecast_days"].append({
            "date": "2026-02-12",
            "confidence": "High",
            "events": [],
        })

        result = self.reporter.generate(data)
        assert len(result["forecast_days"]) == 2
        assert result["forecast_days"][1]["events"] == []
        assert "不推荐" in result["forecast_days"][1]["summary"]

    def test_conditions_structured_golden_mountain(self) -> None:
        """C1 修复 — 日照金山 conditions 含 local/targets/light_path"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]
        golden = [e for e in day["events"] if e["type"] == "sunrise_golden_mountain"][0]

        conditions = golden["conditions"]
        assert "local" in conditions
        assert "targets" in conditions
        assert "light_path" in conditions

    def test_conditions_structured_stargazing(self) -> None:
        """C1 修复 — 观星 conditions 含 sky/moon/wind"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]
        star = [e for e in day["events"] if e["type"] == "stargazing"][0]

        conditions = star["conditions"]
        assert "sky" in conditions
        assert "moon" in conditions
        assert "wind" in conditions

    def test_conditions_structured_cloud_sea(self) -> None:
        """C1 修复 — 云海 conditions 含 gap/low_cloud/wind"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]
        cs = [e for e in day["events"] if e["type"] == "cloud_sea"][0]

        conditions = cs["conditions"]
        assert "gap" in conditions
        assert "low_cloud" in conditions
        assert "wind" in conditions

    def test_conditions_structured_frost(self) -> None:
        """C1 修复 — 雾凇 conditions 含 temperature/visibility/wind/low_cloud"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]
        frost = [e for e in day["events"] if e["type"] == "frost"][0]

        conditions = frost["conditions"]
        assert "temperature" in conditions
        assert "visibility" in conditions
        assert "wind" in conditions
        assert "low_cloud" in conditions

    def test_conditions_structured_snow_tree(self) -> None:
        """T1 修复 — 树挂积雪 conditions 含 snow/temperature/wind"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]
        st = [e for e in day["events"] if e["type"] == "snow_tree"][0]

        conditions = st["conditions"]
        assert "snow" in conditions
        assert "temperature" in conditions
        assert "wind" in conditions

    def test_conditions_structured_ice_icicle(self) -> None:
        """T1 修复 — 冰挂 conditions 含 water/freeze/view"""
        result = self.reporter.generate(_make_clear_day_result())
        day = result["forecast_days"][0]
        ic = [e for e in day["events"] if e["type"] == "ice_icicle"][0]

        conditions = ic["conditions"]
        assert "water" in conditions
        assert "freeze" in conditions
        assert "view" in conditions
