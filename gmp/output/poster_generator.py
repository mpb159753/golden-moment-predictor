"""gmp/output/poster_generator.py — 海报数据聚合器

读取已生成的 forecast+timeline JSON，按山系分组聚合为 poster.json。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gmp.core.config_loader import ViewpointConfig

_CST = timezone(timedelta(hours=8))

# 山系分组元数据 (key → 中文名 + 排序序号)
GROUP_META: dict[str, dict] = {
    "gongga": {"name": "贡嘎山系", "order": 1},
    "siguniang": {"name": "四姑娘山", "order": 2},
    "yala": {"name": "雅拉山系", "order": 3},
    "genie": {"name": "格聂山系", "order": 4},
    "yading": {"name": "亚丁景区", "order": 5},
    "318": {"name": "318 沿途", "order": 6},
    "lixiao": {"name": "理小路沿途", "order": 7},
    "other": {"name": "其它景区", "order": 8},
}

# weather_icon → 中文映射 (对应 scheduler._extract_hourly_weather 生成的值)
WEATHER_ICON_MAP: dict[str, str] = {
    "clear": "晴天",
    "partly_cloudy": "多云",
    "cloudy": "阴天",
    "rain": "雨",
    "snow": "雪",
}

# 上午/下午事件归属
AM_EVENTS = {"sunrise_golden_mountain", "frost", "snow_tree", "ice_icicle"}
PM_EVENTS = {"sunset_golden_mountain", "cloud_sea", "stargazing"}


class PosterGenerator:
    """海报数据聚合器"""

    def __init__(self, output_dir: str = "public/data") -> None:
        self._output_dir = Path(output_dir)

    def generate(
        self,
        viewpoint_config: ViewpointConfig,
        days: int = 5,
    ) -> dict:
        """聚合所有景点数据生成 poster.json 格式的 dict"""
        now = datetime.now(_CST)
        date_list = [
            (now + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days)
        ]

        # 按 groups 分组 viewpoint (一个景点可属于多个组)
        groups_map: dict[str, list] = {}
        for vp in viewpoint_config.list_all():
            vp_groups = vp.groups if vp.groups else ["other"]
            for group_key in vp_groups:
                if group_key not in groups_map:
                    groups_map[group_key] = []
                groups_map[group_key].append(vp)

        # 构建每组数据
        groups = []
        for group_key, meta in sorted(
            GROUP_META.items(), key=lambda x: x[1]["order"]
        ):
            vps = groups_map.get(group_key, [])
            if not vps:
                continue

            viewpoints_data = []
            for vp in vps:
                daily = self._build_daily(vp.id, date_list)
                viewpoints_data.append({
                    "id": vp.id,
                    "name": vp.name,
                    "daily": daily,
                })

            groups.append({
                "name": meta["name"],
                "key": group_key,
                "viewpoints": viewpoints_data,
            })

        return {
            "generated_at": now.isoformat(),
            "days": date_list,
            "groups": groups,
        }

    def _build_daily(
        self, viewpoint_id: str, dates: list[str]
    ) -> list[dict]:
        """为单个景点构建多日 AM/PM 数据"""
        forecast = self._load_forecast(viewpoint_id)
        result = []
        for date_str in dates:
            timeline = self._load_timeline(viewpoint_id, date_str)
            am = self._extract_half_day(
                forecast, timeline, date_str, "am"
            )
            pm = self._extract_half_day(
                forecast, timeline, date_str, "pm"
            )
            result.append({"date": date_str, "am": am, "pm": pm})
        return result

    def _load_forecast(self, viewpoint_id: str) -> dict:
        """加载 viewpoint 的 forecast.json"""
        path = (
            self._output_dir / "viewpoints" / viewpoint_id / "forecast.json"
        )
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_timeline(self, viewpoint_id: str, date_str: str) -> dict:
        """加载 viewpoint 的 timeline_{date}.json"""
        path = (
            self._output_dir
            / "viewpoints"
            / viewpoint_id
            / f"timeline_{date_str}.json"
        )
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _extract_half_day(
        self,
        forecast: dict,
        timeline: dict,
        date_str: str,
        half: str,  # "am" or "pm"
    ) -> dict:
        """提取上午/下午的天气+最佳事件"""
        weather = self._get_dominant_weather(timeline, half)

        event_name = ""
        score = 0
        conditions: dict = {}
        target_events = AM_EVENTS if half == "am" else PM_EVENTS

        for day_data in forecast.get("daily", []):
            if day_data.get("date") != date_str:
                continue
            best_score = 0
            for ev in day_data.get("events", []):
                ev_type = ev.get("event_type", "")
                ev_score = ev.get("score", 0)
                if ev_score >= 50 and ev_type in target_events:
                    if ev_score > best_score:
                        best_score = ev_score
                        event_name = ev.get("display_name", ev_type)
                        score = ev_score
                        conditions = ev.get("score_breakdown", {})
            # 如果无专属时段事件 >= 50, 检查 clear_sky
            if not event_name:
                for ev in day_data.get("events", []):
                    if (
                        ev.get("event_type") == "clear_sky"
                        and ev.get("score", 0) >= 50
                    ):
                        score = ev["score"]
                        conditions = ev.get("score_breakdown", {})
            break

        return {"weather": weather, "event": event_name, "score": score, "conditions": conditions}

    def _get_dominant_weather(self, timeline: dict, half: str) -> str:
        """从 timeline 中提取上午/下午的主导天气"""
        hours_range = range(6, 12) if half == "am" else range(12, 18)
        icons: list[str] = []

        for entry in timeline.get("hourly", []):
            if entry.get("hour") in hours_range:
                weather = entry.get("weather", {})
                icon = weather.get("weather_icon")
                if icon is not None:
                    icons.append(icon)

        if not icons:
            return "未知"

        most_common = Counter(icons).most_common(1)[0][0]
        return WEATHER_ICON_MAP.get(most_common, "未知")
