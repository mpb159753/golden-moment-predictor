"""gmp/output/timeline_reporter.py — 时间线报告生成器

将 PipelineResult 转换为 timeline.json 格式的 dict。
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from gmp.core.models import PipelineResult, ScoreResult


class TimelineReporter:
    """时间线报告生成器"""

    def generate(self, result: PipelineResult, target_date: date) -> dict:
        """将 PipelineResult → timeline.json 格式的 dict

        输出格式 (见 05-api.md):
        {
            "viewpoint_id": "...",
            "generated_at": "...",
            "date": "...",
            "hourly": [{...}, ...]
        }
        """
        raw_weather = result.meta.get("hourly_weather", {})
        date_str = target_date.isoformat()
        # 新格式: {date_str: {hour: dict}}
        hourly_weather = raw_weather.get(date_str, {})
        safety_hours = result.meta.get("safety_hours", {})

        # 找到对应日期的 ForecastDay
        date_str = target_date.isoformat()
        events: list[ScoreResult] = []
        for day in result.forecast_days:
            if day.date == date_str:
                events = day.events
                break

        # 解析事件时间窗口 → hour 集合
        event_hours: list[tuple[ScoreResult, set[int]]] = []
        for event in events:
            hours = self._parse_time_window(event.time_window)
            event_hours.append((event, hours))

        # 构建 24 小时逐时数据
        hourly = []
        for h in range(24):
            weather = hourly_weather.get(h, {})
            safe = safety_hours.get(h, True)

            # 当前小时活跃的事件
            active: list[dict] = []
            for event, hours_set in event_hours:
                if h in hours_set:
                    active.append(
                        {
                            "event_type": event.event_type,
                            "status": "Active",
                            "score": event.total_score,
                        }
                    )

            # 生成 tags
            tags = self._assign_tags(h, event_hours, weather)

            hourly.append(
                {
                    "hour": h,
                    "time": f"{h:02d}:00",
                    "safety_passed": safe,
                    "weather": weather,
                    "events_active": active,
                    "tags": tags,
                }
            )

        return {
            "viewpoint_id": result.viewpoint.id,
            "generated_at": result.meta.get(
                "generated_at",
                datetime.now(timezone.utc).isoformat(),
            ),
            "date": date_str,
            "hourly": hourly,
        }

    def _assign_tags(
        self,
        hour: int,
        event_hours: list[tuple[ScoreResult, set[int]]],
        weather: dict,
    ) -> list[str]:
        """根据时刻和事件生成 tags (sunrise, cloud_sea, etc.)"""
        tags: list[str] = []

        for event, hours_set in event_hours:
            if hour not in hours_set:
                continue
            et = event.event_type
            if "sunrise" in et:
                tags.append("sunrise")
            if "sunset" in et:
                tags.append("sunset")
            if "golden_mountain" in et:
                tags.append("golden_mountain")
            if et == "cloud_sea":
                tags.append("cloud_sea")
            if et == "stargazing":
                tags.append("stargazing")
            if event.total_score >= 85:
                tags.append("magnificent")

        # 天气相关 tags
        if not weather:
            tags.append("partial_data")
        elif weather.get("cloud_cover", weather.get("cloud_cover_total", 100)) < 30:
            tags.append("clear_sky")

        return tags

    @staticmethod
    def _parse_time_window(time_window: str) -> set[int]:
        """解析 "HH:MM - HH:MM" → 包含的整点小时集合

        例: "06:00 - 09:00" → {6, 7, 8}
        跨午夜: "21:00 - 03:00" → {21, 22, 23, 0, 1, 2}
        """
        if not time_window or " - " not in time_window:
            return set()

        parts = time_window.split(" - ")
        start_hour = int(parts[0].split(":")[0])
        end_hour = int(parts[1].split(":")[0])

        if start_hour <= end_hour:
            # 正常: end hour 不包含 (06:00-09:00 = 6,7,8)
            return set(range(start_hour, end_hour))
        else:
            # 跨午夜: 21:00-03:00 = {21,22,23} ∪ {0,1,2}
            return set(range(start_hour, 24)) | set(range(0, end_hour))
