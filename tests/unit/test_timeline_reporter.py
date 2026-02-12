"""TimelineReporter 单元测试

测试用例:
- test_24_hours_coverage: 输出包含 0-23 小时
- test_tag_assignment: 日出时段包含 sunrise_golden tag
- test_rain_tag: 降水概率>50 标记 rain tag
"""

from __future__ import annotations

import pytest

from gmp.reporter.timeline_reporter import TimelineReporter


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

def _make_scheduler_result_with_hourly() -> dict:
    """构造带逐小时天气数据的 Scheduler 输出"""
    hourly = []
    for h in range(24):
        # 模拟天气数据
        if h < 6:
            cloud = 5
            precip = 0
            temp = -7.0 + h * 0.3
        elif h < 10:
            cloud = 20 + (h - 6) * 5
            precip = 0
            temp = -5.0 + (h - 6) * 1.5
        elif h < 14:
            cloud = 65 + (h - 10) * 5
            precip = 30 + (h - 10) * 10
            temp = 3.0 + (h - 10) * 0.5
        elif h < 18:
            cloud = 40 - (h - 14) * 5
            precip = 10 - (h - 14) * 2
            temp = 3.0 - (h - 14) * 0.5
        else:
            cloud = 10
            precip = 0
            temp = -3.0 - (h - 18) * 0.5

        hourly.append({
            "hour": h,
            "cloud_cover_total": cloud,
            "precipitation_probability": precip,
            "temperature_2m": temp,
        })

    return {
        "viewpoint": "牛背山",
        "forecast_days": [
            {
                "date": "2026-02-11",
                "confidence": "High",
                "hourly_weather": hourly,
                "events": [
                    {
                        "event_type": "sunrise_golden_mountain",
                        "display_name": "日照金山",
                        "total_score": 87,
                        "status": "Recommended",
                        "time_window": "07:15 - 07:45",
                        "breakdown": {},
                    },
                    {
                        "event_type": "stargazing",
                        "display_name": "观星",
                        "total_score": 98,
                        "status": "Perfect",
                        "time_window": "19:55 - 03:15",
                        "secondary_window": "03:15 - 05:55",
                        "breakdown": {},
                    },
                    {
                        "event_type": "cloud_sea",
                        "display_name": "云海",
                        "total_score": 95,
                        "status": "Perfect",
                        "time_window": "06:00 - 09:00",
                        "breakdown": {},
                    },
                    {
                        "event_type": "frost",
                        "display_name": "雾凇",
                        "total_score": 67,
                        "status": "Possible",
                        "time_window": "05:00 - 08:30",
                        "breakdown": {},
                    },
                ],
            },
        ],
        "meta": {"api_calls": 14, "cache_hits": 2},
    }


def _make_empty_day_result() -> dict:
    """构造无天气数据的空结果"""
    return {
        "viewpoint": "牛背山",
        "forecast_days": [
            {
                "date": "2026-02-12",
                "confidence": "Low",
                "hourly_weather": [],
                "events": [],
            },
        ],
        "meta": {},
    }


# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────

class TestTimelineReporter:
    """TimelineReporter 测试集"""

    def setup_method(self) -> None:
        self.reporter = TimelineReporter()

    def test_24_hours_coverage(self) -> None:
        """输出包含 0-23 小时"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())

        assert "timeline_days" in result
        day = result["timeline_days"][0]
        assert len(day["hours"]) == 24

        hours = [h["hour"] for h in day["hours"]]
        assert hours == list(range(24))

    def test_tag_assignment(self) -> None:
        """日出时段包含 sunrise_golden tag"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # hour=7 在 "07:15 - 07:45" 窗口内
        hour_7 = day["hours"][7]
        assert "sunrise_golden" in hour_7["tags"]

    def test_rain_tag(self) -> None:
        """降水概率>50 标记 rain tag"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # hour=12 的 precip_prob = 30 + (12-10)*10 = 50，不超过50
        # hour=13 的 precip_prob = 30 + (13-10)*10 = 60，> 50 → rain
        hour_13 = day["hours"][13]
        assert "rain" in hour_13["tags"]

    def test_stargazing_window_tag(self) -> None:
        """观星时间窗口标签 (跨日)"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # 观星窗口 "19:55 - 03:15" → hour=0,1,2,3,19,20,21,22,23 应有 stargazing_window
        for h in [0, 1, 2, 3, 20, 21, 22, 23]:
            tags = day["hours"][h]["tags"]
            assert "stargazing_window" in tags, f"hour {h} 应有 stargazing_window"

    def test_stargazing_secondary_tag(self) -> None:
        """观星次佳窗口标签"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # secondary_window "03:15 - 05:55" → hour 4, 5
        hour_4 = day["hours"][4]
        assert "stargazing_secondary" in hour_4["tags"]

    def test_cloud_sea_tag(self) -> None:
        """云海标签在正确时段"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # cloud_sea "06:00 - 09:00" → hour 6,7,8,9
        for h in [6, 7, 8, 9]:
            assert "cloud_sea" in day["hours"][h]["tags"], f"hour {h} 应有 cloud_sea"

    def test_overcast_tag(self) -> None:
        """阴天标签 — 云量>60%"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # hour 10: cloud=65, precip=30 → precip < 50 但 cloud > 60 → overcast
        hour_10 = day["hours"][10]
        assert "overcast" in hour_10["tags"]

    def test_empty_day(self) -> None:
        """空天气数据日仍输出 24 小时"""
        result = self.reporter.generate(_make_empty_day_result())
        day = result["timeline_days"][0]
        assert len(day["hours"]) == 24

    def test_viewpoint_name(self) -> None:
        """viewpoint 名称正确"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        assert result["viewpoint"] == "牛背山"

    def test_l1_passed_determination(self) -> None:
        """L1 通过判定 — precip < 30%"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # hour=6: precip=0 → l1_passed=True
        assert day["hours"][6]["l1_passed"] is True

        # hour=12: precip=50 → l1_passed=False (>= 30)
        assert day["hours"][12]["l1_passed"] is False

    def test_frost_window_tag(self) -> None:
        """雾凇窗口标签"""
        result = self.reporter.generate(_make_scheduler_result_with_hourly())
        day = result["timeline_days"][0]

        # frost "05:00 - 08:30" → hour 5,6,7,8
        for h in [5, 6, 7, 8]:
            assert "frost_window" in day["hours"][h]["tags"], f"hour {h} 应有 frost_window"

    def test_clearing_tag(self) -> None:
        """T2 — 天气转晴标签 (前一小时阴天 → 本小时晴)"""
        # hour=14: cloud=40, hour=13: cloud=80 → 不满足 (13→14 降低但14仍>40)
        # 需要构造 明确的 cloud 变化
        data = {
            "viewpoint": "牛背山",
            "forecast_days": [{
                "date": "2026-02-11",
                "confidence": "High",
                "hourly_weather": [
                    {"hour": 0, "cloud_cover_total": 70, "precipitation_probability": 0, "temperature_2m": 0},
                    {"hour": 1, "cloud_cover_total": 40, "precipitation_probability": 0, "temperature_2m": 0},
                ],
                "events": [],
            }],
        }
        result = self.reporter.generate(data)
        day = result["timeline_days"][0]

        # hour=0: cloud=70 > 60, hour=1: cloud=40 ≤ 60 → clearing
        assert "clearing" in day["hours"][1]["tags"]
        # hour=0 没有前一小时数据, 不应有 clearing
        assert "clearing" not in day["hours"][0]["tags"]

    def test_pre_sunrise_tag(self) -> None:
        """T2 — 日出前标签 (sun_events.sunrise 所在小时的前1小时)"""
        from datetime import datetime
        data = {
            "viewpoint": "牛背山",
            "forecast_days": [{
                "date": "2026-02-11",
                "confidence": "High",
                "hourly_weather": [
                    {"hour": h, "cloud_cover_total": 10, "precipitation_probability": 0, "temperature_2m": 0}
                    for h in range(24)
                ],
                "events": [],
                "sun_events": {"sunrise": datetime(2026, 2, 11, 7, 28)},
            }],
        }
        result = self.reporter.generate(data)
        day = result["timeline_days"][0]

        # sunrise hour=7, pre_sunrise → hour=6
        assert "pre_sunrise" in day["hours"][6]["tags"]
        # hour=5 不应有 pre_sunrise
        assert "pre_sunrise" not in day["hours"][5]["tags"]

    def test_sunset_window_tag(self) -> None:
        """T2 — 日落金山标签映射 (sunset_golden_mountain → sunset_window)"""
        data = {
            "viewpoint": "牛背山",
            "forecast_days": [{
                "date": "2026-02-11",
                "confidence": "High",
                "hourly_weather": [
                    {"hour": h, "cloud_cover_total": 10, "precipitation_probability": 0, "temperature_2m": 0}
                    for h in range(24)
                ],
                "events": [{
                    "event_type": "sunset_golden_mountain",
                    "display_name": "日落金山",
                    "total_score": 80,
                    "status": "Recommended",
                    "time_window": "17:30 - 18:30",
                    "breakdown": {},
                }],
            }],
        }
        result = self.reporter.generate(data)
        day = result["timeline_days"][0]

        # hour 17, 18 在 "17:30 - 18:30" 窗口内
        assert "sunset_window" in day["hours"][17]["tags"]
        assert "sunset_window" in day["hours"][18]["tags"]
        # hour 16 不在窗口内
        assert "sunset_window" not in day["hours"][16]["tags"]

