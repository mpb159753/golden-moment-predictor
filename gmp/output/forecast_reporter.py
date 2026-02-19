"""gmp/output/forecast_reporter.py — 预测报告生成器

将 PipelineResult 转换为 forecast.json 格式的 dict。
"""

from __future__ import annotations

from datetime import datetime, timezone

from gmp.core.models import (
    ForecastDay,
    PipelineResult,
    Route,
    ScoreResult,
)
from gmp.output.summary_generator import SummaryGenerator


class ForecastReporter:
    """预测报告生成器"""

    def __init__(
        self,
        summary_gen: SummaryGenerator | None = None,
        display_names: dict[str, str] | None = None,
    ) -> None:
        self._display_names = display_names or {}
        self._summary_gen = summary_gen or SummaryGenerator(
            display_names=self._display_names,
        )

    def generate(self, result: PipelineResult) -> dict:
        """将 PipelineResult → forecast.json 格式的 dict"""
        daily = []
        for day in result.forecast_days:
            # 按 score 降序排列事件
            sorted_events = sorted(
                day.events, key=lambda e: e.total_score, reverse=True
            )

            # 生成摘要
            summary = self._summary_gen.generate(sorted_events)

            # 确定 best_event
            best_event = (
                self._format_event_brief(sorted_events[0])
                if sorted_events
                else None
            )

            daily.append(
                {
                    "date": day.date,
                    "summary": summary,
                    "best_event": best_event,
                    "events": [
                        self._format_event(e) for e in sorted_events
                    ],
                }
            )

        return {
            "viewpoint_id": result.viewpoint.id,
            "viewpoint_name": result.viewpoint.name,
            "generated_at": result.meta.get(
                "generated_at",
                datetime.now(timezone.utc).isoformat(),
            ),
            "forecast_days": len(result.forecast_days),
            "daily": daily,
        }

    def generate_route(
        self, stops_results: list[PipelineResult], route: Route
    ) -> dict:
        """将多站 PipelineResult → 线路 forecast.json 格式的 dict"""
        # 建立 viewpoint_id → order/stay_note 的映射
        stop_info = {s.viewpoint_id: s for s in route.stops}

        stops = []
        for pr in stops_results:
            vid = pr.viewpoint.id
            rs = stop_info.get(vid)
            order = rs.order if rs else 0
            stay_note = rs.stay_note if rs else ""

            forecast = self.generate(pr)
            stops.append(
                {
                    "viewpoint_id": vid,
                    "viewpoint_name": pr.viewpoint.name,
                    "order": order,
                    "stay_note": stay_note,
                    "forecast": forecast,
                }
            )

        # 按 order 排序
        stops.sort(key=lambda s: s["order"])

        # 取第一个 PipelineResult 的 generated_at 和 forecast_days
        generated_at = ""
        forecast_days = 0
        if stops_results:
            generated_at = stops_results[0].meta.get(
                "generated_at",
                datetime.now(timezone.utc).isoformat(),
            )
            forecast_days = len(stops_results[0].forecast_days)

        return {
            "route_id": route.id,
            "route_name": route.name,
            "generated_at": generated_at,
            "forecast_days": forecast_days,
            "stops": stops,
        }

    def _format_event(self, event: ScoreResult) -> dict:
        """格式化单个事件为完整输出格式"""
        return {
            "event_type": event.event_type,
            "display_name": self._display_names.get(
                event.event_type, event.event_type
            ),
            "time_window": event.time_window,
            "score": event.total_score,
            "status": event.status,
            "confidence": event.confidence,
            "reject_reason": ForecastReporter._generate_reject_reason(event),
            "tags": ForecastReporter._generate_tags(event),
            "conditions": event.highlights,
            "score_breakdown": event.breakdown,
        }

    @staticmethod
    def _generate_reject_reason(event: ScoreResult) -> str | None:
        """为 0 分事件生成精简拒绝原因

        逻辑: 从 breakdown 中找到得分比例最低的维度，用其 detail 生成一句话。
        Returns: None (score > 0) 或 str (score == 0)
        """
        if event.total_score > 0:
            return None

        if not event.breakdown:
            return None

        worst_dim = None
        worst_ratio = float("inf")
        for dim, info in event.breakdown.items():
            max_score = info.get("max", 0)
            if max_score <= 0:
                continue
            ratio = info.get("score", 0) / max_score
            if ratio < worst_ratio:
                worst_ratio = ratio
                worst_dim = info

        if worst_dim and worst_dim.get("detail"):
            return worst_dim["detail"]

        return None

    @staticmethod
    def _generate_tags(event: ScoreResult) -> list[str]:
        """基于 ScoreResult 自动生成 tags

        规则 (见 05-api.md §5.3):
        - event_type 含 sunrise → "sunrise"
        - event_type 含 sunset → "sunset"
        - event_type 含 golden_mountain → "golden_mountain"
        - event_type == cloud_sea → "cloud_sea"
        - event_type == stargazing → "stargazing"
        - total_score >= 85 → "magnificent"
        - warnings 非空 → "partial_data"
        """
        tags: list[str] = []
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
        if event.warnings:
            tags.append("partial_data")

        return tags

    @staticmethod
    def _format_event_brief(event: ScoreResult) -> dict:
        """格式化事件摘要 (best_event 用)"""
        return {
            "event_type": event.event_type,
            "score": event.total_score,
            "status": event.status,
        }
