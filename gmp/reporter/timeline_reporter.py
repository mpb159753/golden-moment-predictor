"""TimelineReporter — 生成 /api/v1/timeline/{id} 格式的 JSON 输出

将 Scheduler 原始结果转换为逐小时时间轴 JSON，
输出 24 小时数据 (0-23)，动态分配标签 (tags)。

设计依据:
- design/04-data-flow-example.md §Stage 6b
- design/05-api.md §5.3
- design/06-class-sequence.md §6.4
"""

from __future__ import annotations

from gmp.reporter.base import BaseReporter

# 标签映射阈值
_L1_PRECIP_THRESHOLD = 30    # 降水概率超过此值 → L1 不通过
_OVERCAST_THRESHOLD = 60     # 云量超过此值 → 阴天
_RAIN_THRESHOLD = 50         # 降水概率超过此值 → rain tag


class TimelineReporter(BaseReporter):
    """生成 /api/v1/timeline/{id} 格式的 JSON 输出"""

    def generate(self, scheduler_result: dict) -> dict:
        """将 Scheduler 原始结果转换为 Timeline JSON

        输出结构 (参见设计文档 Stage 6b):
        {
            "viewpoint": "牛背山",
            "timeline_days": [
                {
                    "date": "2026-02-11",
                    "confidence": "High",
                    "hours": [
                        {
                            "hour": int,
                            "l1_passed": bool,
                            "cloud_cover": int,
                            "precip_prob": int,
                            "temperature": float,
                            "tags": [str, ...],
                        }, ...
                    ]
                }, ...
            ]
        }
        """
        viewpoint_name = scheduler_result.get("viewpoint", "")
        raw_days = scheduler_result.get("forecast_days", [])

        timeline_days: list[dict] = []
        for day in raw_days:
            hours_data = day.get("hourly_weather", [])
            confidence = day.get("confidence", "")
            events = day.get("events", [])

            hours: list[dict] = []
            for h in range(24):
                # 查找该小时的天气数据
                hour_data = self._find_hour_data(hours_data, h)

                cloud_cover = int(hour_data.get("cloud_cover_total",
                                  hour_data.get("cloud_cover", 0)))
                precip_prob = int(hour_data.get("precipitation_probability",
                                  hour_data.get("precip_prob", 0)))
                temperature = float(hour_data.get("temperature_2m",
                                    hour_data.get("temperature", 0.0)))

                # L1 通过判定: 降水概率 < 30% 且不是极端天气
                l1_passed = precip_prob < _L1_PRECIP_THRESHOLD

                tags = self._assign_tags(h, hour_data, {
                    "events": events,
                    "cloud_cover": cloud_cover,
                    "precip_prob": precip_prob,
                    "temperature": temperature,
                    "l1_passed": l1_passed,
                })

                hours.append({
                    "hour": h,
                    "l1_passed": l1_passed,
                    "cloud_cover": cloud_cover,
                    "precip_prob": precip_prob,
                    "temperature": temperature,
                    "tags": tags,
                })

            timeline_days.append({
                "date": day.get("date", ""),
                "confidence": confidence,
                "hours": hours,
            })

        return {
            "viewpoint": viewpoint_name,
            "timeline_days": timeline_days,
        }

    # ------------------------------------------------------------------
    # 标签分配
    # ------------------------------------------------------------------

    def _assign_tags(
        self,
        hour: int,
        hour_data: dict,
        day_context: dict,
    ) -> list[str]:
        """为每个小时分配标签

        标签映射 (参见设计文档 §5.5 枚举):
        - stargazing_window: 最佳观星时段
        - pre_sunrise: 日出前30min
        - sunrise_golden: 日照金山时段
        - cloud_sea: 云海可见时段
        - frost_window: 雾凇观赏时段
        - snow_tree_window: 树挂积雪观赏时段
        - ice_icicle_window: 冰挂观赏时段
        - rain: 降水时段
        - overcast: 阴天 (云量>60%)
        - clearing: 天气转晴
        """
        tags: list[str] = []
        events = day_context.get("events", [])
        cloud_cover = day_context.get("cloud_cover", 0)
        precip_prob = day_context.get("precip_prob", 0)

        # 分析事件时间窗口
        for ev in events:
            event_type = ev.get("event_type", "")
            time_window = ev.get("time_window", "")
            status = ev.get("status", "")

            # 只标记有价值的事件 (非 Not Recommended)
            if status == "Not Recommended":
                continue

            if self._hour_in_window(hour, time_window):
                tag = self._event_type_to_tag(event_type)
                if tag and tag not in tags:
                    tags.append(tag)

            # 观星次佳窗口
            secondary = ev.get("secondary_window", "")
            if event_type == "stargazing" and secondary:
                if self._hour_in_window(hour, secondary):
                    if "stargazing_secondary" not in tags:
                        tags.append("stargazing_secondary")

        # 天气标签
        if precip_prob > _RAIN_THRESHOLD:
            if "rain" not in tags:
                tags.append("rain")
        elif cloud_cover > _OVERCAST_THRESHOLD:
            if "overcast" not in tags:
                tags.append("overcast")

        return tags

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _find_hour_data(hours_data: list, hour: int) -> dict:
        """从天气数据列表中查找指定小时的数据"""
        for hd in hours_data:
            h = hd.get("hour", hd.get("h", -1))
            if h == hour:
                return hd
        return {}

    @staticmethod
    def _event_type_to_tag(event_type: str) -> str:
        """事件类型 → 时段标签映射"""
        mapping = {
            "sunrise_golden_mountain": "sunrise_golden",
            "sunset_golden_mountain": "sunset_window",
            "stargazing": "stargazing_window",
            "cloud_sea": "cloud_sea",
            "frost": "frost_window",
            "snow_tree": "snow_tree_window",
            "ice_icicle": "ice_icicle_window",
        }
        return mapping.get(event_type, "")

    @staticmethod
    def _hour_in_window(hour: int, time_window: str) -> bool:
        """判断某小时是否在时间窗口内

        时间窗口格式: "HH:MM - HH:MM" 或 "HH:MM-HH:MM"
        支持跨日窗口 (如 "19:55 - 03:15")
        """
        if not time_window:
            return False

        try:
            parts = time_window.replace(" ", "").split("-")
            if len(parts) != 2:
                return False

            start_h = int(parts[0].split(":")[0])
            end_h = int(parts[1].split(":")[0])

            if start_h <= end_h:
                # 同日窗口
                return start_h <= hour <= end_h
            else:
                # 跨日窗口 (如 19:55 - 03:15)
                return hour >= start_h or hour <= end_h
        except (ValueError, IndexError):
            return False
