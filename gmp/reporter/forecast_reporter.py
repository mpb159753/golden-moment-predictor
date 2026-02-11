"""ForecastReporter — 生成 /api/v1/forecast/{id} 格式的 JSON 输出

将 Scheduler 原始结果转换为 Forecast JSON,
包含推荐事件列表、评分明细、conditions 和每日摘要。

设计依据:
- design/04-data-flow-example.md §Stage 6a
- design/05-api.md §5.2
- design/06-class-sequence.md §6.4
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

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

        return {
            "report_date": str(date.today()),
            "viewpoint": viewpoint_name,
            "forecast_days": forecast_days,
            "meta": {
                "generated_at": datetime.now(_CST).isoformat(),
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
    # 条件详情格式化
    # ------------------------------------------------------------------

    def _format_conditions(self, event_type: str, context: dict) -> dict:
        """根据事件类型生成条件详情

        不同事件类型的 conditions 结构不同:
        - sunrise_golden_mountain/sunset_golden_mountain: local + targets + light_path
        - stargazing: sky + moon + wind
        - cloud_sea: gap + low_cloud + wind
        - frost: temperature + visibility + wind + low_cloud
        - snow_tree: snow + temperature + wind
        - ice_icicle: rain + snow + temperature + wind
        """
        breakdown = context.get("breakdown", {})

        # 从 breakdown 中提取可用信息构建条件
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
