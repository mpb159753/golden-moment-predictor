"""TimelineReporter — 生成 /api/v1/timeline/{id} 格式的 JSON 输出

将 Scheduler 原始结果转换为逐小时时间轴 JSON，
输出 24 小时数据 (0-23)，动态分配标签 (tags)。

设计依据:
- design/04-data-flow-example.md §Stage 6b
- design/05-api.md §5.3
- design/06-class-sequence.md §6.4
"""

from __future__ import annotations

from gmp.core.config_loader import EngineConfig
from gmp.reporter.base import BaseReporter


class TimelineReporter(BaseReporter):
    """生成 /api/v1/timeline/{id} 格式的 JSON 输出"""

    def __init__(self, config: EngineConfig | None = None) -> None:
        cfg = config or EngineConfig()
        self._l1_precip_threshold = cfg.reporter_l1_precip_threshold
        self._overcast_threshold = cfg.reporter_overcast_threshold
        self._rain_threshold = cfg.reporter_rain_threshold

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
            # 天文数据 (可选, 由 Scheduler 传入)
            sun_events = day.get("sun_events")

            hours: list[dict] = []
            prev_cloud_cover: int | None = None
            for h in range(24):
                # 查找该小时的天气数据
                hour_data = self._find_hour_data(hours_data, h)

                cloud_cover = int(hour_data.get("cloud_cover_total",
                                  hour_data.get("cloud_cover", 0)))
                precip_prob = int(hour_data.get("precipitation_probability",
                                  hour_data.get("precip_prob", 0)))
                temperature = float(hour_data.get("temperature_2m",
                                    hour_data.get("temperature", 0.0)))

                # L1 通过判定 (简化版):
                # 仅使用降水概率阈值，实际 LocalAnalyzer.analyze() 还综合检查
                # visibility, weather_code 等多维指标。此处用于 Timeline 展示。
                # 边界语义: precip_prob >= threshold 时 L1 不通过
                l1_passed = precip_prob < self._l1_precip_threshold

                tags = self._assign_tags(h, hour_data, {
                    "events": events,
                    "cloud_cover": cloud_cover,
                    "precip_prob": precip_prob,
                    "temperature": temperature,
                    "l1_passed": l1_passed,
                    "prev_cloud_cover": prev_cloud_cover,
                    "sun_events": sun_events,
                })

                hours.append({
                    "hour": h,
                    "l1_passed": l1_passed,
                    "cloud_cover": cloud_cover,
                    "precip_prob": precip_prob,
                    "temperature": temperature,
                    "tags": tags,
                })

                prev_cloud_cover = cloud_cover

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
        prev_cloud = day_context.get("prev_cloud_cover")
        sun_events = day_context.get("sun_events")

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

        # pre_sunrise 标签: 日出前 1 小时
        if sun_events is not None:
            sunrise_hour = _extract_hour(sun_events, "sunrise")
            if sunrise_hour is not None and hour == sunrise_hour - 1:
                if "pre_sunrise" not in tags:
                    tags.append("pre_sunrise")

        # 天气标签
        if precip_prob > self._rain_threshold:
            if "rain" not in tags:
                tags.append("rain")
        elif cloud_cover > self._overcast_threshold:
            if "overcast" not in tags:
                tags.append("overcast")

        # clearing 标签: 前一小时云量超过阈值，本小时降至阈值以下
        if (prev_cloud is not None
                and prev_cloud > self._overcast_threshold
                and cloud_cover <= self._overcast_threshold):
            if "clearing" not in tags:
                tags.append("clearing")

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


# ======================================================================
# 模块级辅助函数
# ======================================================================

def _extract_hour(sun_events: dict | object, key: str) -> int | None:
    """从 sun_events 中提取小时数 (兼容 dict 和对象)"""
    if isinstance(sun_events, dict):
        val = sun_events.get(key)
    else:
        val = getattr(sun_events, key, None)

    if val is None:
        return None

    # datetime-like 对象
    if hasattr(val, "hour"):
        return val.hour

    # 字符串 "07:28" 格式
    if isinstance(val, str) and ":" in val:
        try:
            return int(val.split(":")[0])
        except ValueError:
            return None

    # 整数
    if isinstance(val, int):
        return val

    return None
