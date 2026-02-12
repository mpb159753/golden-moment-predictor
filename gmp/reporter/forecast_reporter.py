"""ForecastReporter — 生成 /api/v1/forecast/{id} 格式的 JSON 输出

将 Scheduler 原始结果转换为 Forecast JSON,
包含推荐事件列表、评分明细、conditions 和每日摘要。

设计依据:
- design/04-data-flow-example.md §Stage 6a
- design/05-api.md §5.2
- design/06-class-sequence.md §6.4
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from gmp.reporter.base import BaseReporter
from gmp.reporter.summary_generator import SummaryGenerator

# UTC+8 北京时间
_CST = timezone(timedelta(hours=8))


class ForecastReporter(BaseReporter):
    """生成 /api/v1/forecast/{id} 格式的 JSON 输出"""

    def __init__(self, summary_generator: SummaryGenerator | None = None) -> None:
        self._summary_gen = summary_generator or SummaryGenerator(mode="rule")

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def generate(self, scheduler_result: dict) -> dict:
        """将 Scheduler 原始结果转换为 Forecast JSON

        输出结构 (参见设计文档 Stage 6a):
        {
            "report_date": "2026-02-10",
            "viewpoint": "牛背山",
            "forecast_days": [
                {
                    "date": "2026-02-11",
                    "confidence": "High",
                    "summary": "极佳观景日 — ...",
                    "summary_mode": "rule",
                    "events": [ ... ]
                }, ...
            ],
            "meta": { ... }
        }
        """
        viewpoint_name = scheduler_result.get("viewpoint", "")
        raw_days = scheduler_result.get("forecast_days", [])
        meta = scheduler_result.get("meta", {})

        forecast_days: list[dict] = []
        for day in raw_days:
            raw_events = day.get("events", [])
            events = self._build_events(raw_events)

            # 生成摘要
            summary, summary_mode = self._summary_gen.generate(raw_events)

            forecast_days.append({
                "date": day.get("date", ""),
                "confidence": day.get("confidence", ""),
                "summary": summary,
                "summary_mode": summary_mode,
                "events": events,
            })

        now_cst = datetime.now(_CST)
        return {
            "report_date": str(now_cst.date()),
            "viewpoint": viewpoint_name,
            "forecast_days": forecast_days,
            "meta": {
                "generated_at": now_cst.isoformat(),
                "cache_stats": {
                    "api_calls": meta.get("api_calls", 0),
                    "cache_hits": meta.get("cache_hits", 0),
                    "saved_calls": meta.get("saved_calls", 0),
                },
            },
        }

    # ------------------------------------------------------------------
    # 事件构建
    # ------------------------------------------------------------------

    def _build_events(self, score_results: list[dict]) -> list[dict]:
        """构建事件列表

        将 Scheduler 输出的原始 event dict 转换为 Forecast API 响应格式。
        """
        events: list[dict] = []
        for raw in score_results:
            event_type = raw.get("event_type", "")
            breakdown = raw.get("breakdown", {})

            event: dict = {
                "type": event_type,
                "time_window": raw.get("time_window", ""),
                "score": raw.get("total_score", 0),
                "status": raw.get("status", ""),
                "conditions": self._format_conditions(event_type, raw),
                "score_breakdown": self._format_breakdown(breakdown),
            }

            # 可选字段
            if raw.get("secondary_window"):
                event["secondary_window"] = raw["secondary_window"]

            events.append(event)

        return events

    # ------------------------------------------------------------------
    # 条件详情格式化 (按事件类型结构化, 与 Stage 6a 对齐)
    # ------------------------------------------------------------------

    def _format_conditions(self, event_type: str, context: dict) -> dict:
        """根据事件类型生成结构化条件详情

        不同事件类型的 conditions 结构不同 (参见 Stage 6a):
        - sunrise_golden_mountain/sunset_golden_mountain: local + targets + light_path
        - stargazing: sky + moon + wind
        - cloud_sea: gap + low_cloud + wind
        - frost: temperature + visibility + wind + low_cloud
        - snow_tree: snow + temperature + wind
        - ice_icicle: rain + snow + temperature + wind
        """
        breakdown = context.get("breakdown", {})

        formatter = _CONDITIONS_FORMATTERS.get(event_type)
        if formatter is not None:
            return formatter(breakdown)

        # 回退: 从 breakdown 提取 detail 字段生成通用结构
        return self._generic_conditions(breakdown)

    @staticmethod
    def _generic_conditions(breakdown: dict) -> dict:
        """从 breakdown 的 detail 字段生成通用条件"""
        conditions: dict = {}
        for dim, detail in breakdown.items():
            if isinstance(detail, dict) and "detail" in detail:
                conditions[dim] = detail["detail"]
        return conditions

    # ------------------------------------------------------------------
    # 评分明细格式化
    # ------------------------------------------------------------------

    @staticmethod
    def _format_breakdown(breakdown: dict) -> dict:
        """格式化 score_breakdown

        确保每个维度都包含 score 和 max 两个字段。
        """
        formatted: dict = {}
        for key, val in breakdown.items():
            if isinstance(val, dict):
                formatted[key] = {
                    "score": val.get("score", 0),
                    "max": val.get("max", 0),
                }
            else:
                formatted[key] = {"score": val, "max": 0}
        return formatted


# ======================================================================
# 按事件类型的 conditions 格式化函数 (模块级, 保持类体简洁)
# ======================================================================

def _golden_mountain_conditions(breakdown: dict) -> dict:
    """日照金山 / 日落金山 — conditions: local + targets + light_path"""
    local_detail = _extract_detail(breakdown, "local_clear")
    lp_detail = _extract_detail(breakdown, "light_path")
    target_detail = _extract_detail(breakdown, "target_visible")
    return {
        "local": local_detail,
        "light_path": lp_detail,
        "targets": target_detail,
    }


def _stargazing_conditions(breakdown: dict) -> dict:
    """观星 — conditions: sky + moon + wind"""
    return {
        "sky": _extract_detail(breakdown, "base"),
        "moon": _extract_detail(breakdown, "cloud"),
        "wind": _extract_detail(breakdown, "wind"),
    }


def _cloud_sea_conditions(breakdown: dict) -> dict:
    """云海 — conditions: gap + low_cloud + wind"""
    return {
        "gap": _extract_detail(breakdown, "gap"),
        "low_cloud": _extract_detail(breakdown, "density"),
        "wind": _extract_detail(breakdown, "wind"),
    }


def _frost_conditions(breakdown: dict) -> dict:
    """雾凇 — conditions: temperature + visibility + wind + low_cloud"""
    return {
        "temperature": _extract_detail(breakdown, "temperature"),
        "visibility": _extract_detail(breakdown, "moisture"),
        "wind": _extract_detail(breakdown, "wind"),
        "low_cloud": _extract_detail(breakdown, "cloud"),
    }


def _snow_tree_conditions(breakdown: dict) -> dict:
    """树挂积雪 — conditions: snow + temperature + wind"""
    return {
        "snow": _extract_detail(breakdown, "snow_signal"),
        "temperature": _extract_detail(breakdown, "clear_weather"),
        "wind": _extract_detail(breakdown, "stability"),
    }


def _ice_icicle_conditions(breakdown: dict) -> dict:
    """冰挂 — conditions: water + freeze + view"""
    return {
        "water": _extract_detail(breakdown, "water_input"),
        "freeze": _extract_detail(breakdown, "freeze_strength"),
        "view": _extract_detail(breakdown, "view_quality"),
    }


def _extract_detail(breakdown: dict, key: str) -> str:
    """从 breakdown 维度中提取 detail 文本"""
    dim = breakdown.get(key, {})
    if isinstance(dim, dict):
        return dim.get("detail", "")
    return ""


# 事件类型 → conditions 格式化函数映射
_CONDITIONS_FORMATTERS: dict = {
    "sunrise_golden_mountain": _golden_mountain_conditions,
    "sunset_golden_mountain": _golden_mountain_conditions,
    "stargazing": _stargazing_conditions,
    "cloud_sea": _cloud_sea_conditions,
    "frost": _frost_conditions,
    "snow_tree": _snow_tree_conditions,
    "ice_icicle": _ice_icicle_conditions,
}
