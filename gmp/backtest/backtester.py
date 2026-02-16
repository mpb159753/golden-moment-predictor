"""gmp/backtest/backtester.py — 历史回测模块

使用过去的气象数据验证评分模型的准确性。
核心策略: 缓存优先、API 兜底。
"""

from __future__ import annotations


from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import pandas as pd
import structlog

from gmp.core.exceptions import InvalidDateError

if TYPE_CHECKING:
    from gmp.cache.repository import CacheRepository
    from gmp.core.config_loader import ConfigManager, ViewpointConfig
    from gmp.core.scheduler import GMPScheduler
    from gmp.data.meteo_fetcher import MeteoFetcher

logger = structlog.get_logger()

_CST = timezone(timedelta(hours=8))


class Backtester:
    """历史回测器 — 用历史天气数据验证评分模型"""

    def __init__(
        self,
        scheduler: GMPScheduler,
        fetcher: MeteoFetcher,
        config: ConfigManager,
        cache_repo: CacheRepository,
        viewpoint_config: ViewpointConfig,
    ) -> None:
        self._scheduler = scheduler
        self._fetcher = fetcher
        self._config = config
        self._cache_repo = cache_repo
        self._viewpoint_config = viewpoint_config

    def run(
        self,
        viewpoint_id: str,
        target_date: date,
        events: list[str] | None = None,
        save: bool = False,
    ) -> dict:
        """执行单次回测

        Steps:
        1. 验证日期合法性
        2. 获取天气数据 (缓存优先策略)
        3. 调用 scheduler.run_with_data() 进行评分
        4. 构建回测报告
        5. 如果 save=True → 保存到 prediction_history
        6. 返回报告
        """
        # 1. 日期验证
        self._validate_date(target_date)

        # 2. 获取 Viewpoint 配置以确定所有需要的坐标
        viewpoint = self._viewpoint_config.get(viewpoint_id)

        # 收集所有需要的坐标 (本地 + 目标)
        required_coords: list[tuple[float, float]] = [
            (round(viewpoint.location.lat, 2), round(viewpoint.location.lon, 2))
        ]
        if viewpoint.targets:
            for target in viewpoint.targets:
                required_coords.append(
                    (round(target.lat, 2), round(target.lon, 2))
                )

        # 3. 解析天气数据 (缓存优先)
        weather_data, data_source, data_fetched_at = self._resolve_weather_data(
            viewpoint_id=viewpoint_id,
            target_date=target_date,
            required_coords=required_coords,
        )

        # 4. 调用 scheduler 评分
        pipeline_result = self._scheduler.run_with_data(
            viewpoint_id=viewpoint_id,
            weather_data=weather_data,
            target_date=target_date,
            events=events,
        )

        # 5. 构建回测报告
        report = self._build_report(
            viewpoint_id=viewpoint_id,
            target_date=target_date,
            pipeline_result=pipeline_result,
            data_source=data_source,
            data_fetched_at=data_fetched_at,
        )

        # 6. 保存 (可选)
        if save:
            self._save_results(report, pipeline_result)

        return report

    def _validate_date(self, target_date: date) -> None:
        """日期合法性检查"""
        today = datetime.now(_CST).date()

        if target_date >= today:
            raise InvalidDateError(target_date, "FutureDate")

        max_days = self._config.config.backtest_max_history_days
        oldest_allowed = today - timedelta(days=max_days)
        if target_date < oldest_allowed:
            raise InvalidDateError(target_date, "DateTooOld")

    def _resolve_weather_data(
        self,
        viewpoint_id: str,
        target_date: date,
        required_coords: list[tuple[float, float]],
    ) -> tuple[dict[tuple[float, float], pd.DataFrame], str, str | None]:
        """解析回测所需天气数据 — 缓存优先策略

        Returns:
            (weather_data_dict, data_source, data_fetched_at)
        """
        weather_data: dict[tuple[float, float], pd.DataFrame] = {}
        all_from_cache = True
        latest_fetched_at: str | None = None

        for coord in required_coords:
            lat, lon = coord
            cached_rows = self._cache_repo.query_weather(lat, lon, target_date)

            if cached_rows is not None:
                # 有缓存 → 取 fetched_at 最新的一批
                best_fetched_at = max(
                    row["fetched_at"] for row in cached_rows
                )
                filtered_rows = [
                    row for row in cached_rows
                    if row["fetched_at"] == best_fetched_at
                ]
                df = pd.DataFrame(filtered_rows)
                weather_data[coord] = df

                # 跟踪全局最新 fetched_at
                if latest_fetched_at is None or best_fetched_at > latest_fetched_at:
                    latest_fetched_at = best_fetched_at
            else:
                # 无缓存 → 调用 API
                all_from_cache = False
                df = self._fetcher.fetch_historical(lat, lon, target_date)
                weather_data[coord] = df

        data_source = "cache" if all_from_cache else "archive"
        data_fetched_at = latest_fetched_at if all_from_cache else None

        return weather_data, data_source, data_fetched_at

    def _build_report(
        self,
        *,
        viewpoint_id: str,
        target_date: date,
        pipeline_result: Any,
        data_source: str,
        data_fetched_at: str | None,
    ) -> dict:
        """构建回测报告"""
        # 从 PipelineResult 中提取 events
        events_data: list[dict] = []
        if pipeline_result.forecast_days:
            day = pipeline_result.forecast_days[0]
            for event in day.events:
                events_data.append(
                    {
                        "event_type": event.event_type,
                        "total_score": event.total_score,
                        "status": event.status,
                        "breakdown": event.breakdown,
                        "confidence": event.confidence,
                    }
                )

        report: dict[str, Any] = {
            "viewpoint_id": viewpoint_id,
            "target_date": target_date.isoformat(),
            "is_backtest": True,
            "data_source": data_source,
            "events": events_data,
            "meta": {
                "backtest_run_at": datetime.now(_CST).isoformat(),
            },
        }

        if data_fetched_at is not None:
            report["data_fetched_at"] = data_fetched_at

        return report

    def _save_results(self, report: dict, pipeline_result: Any) -> None:
        """保存回测结果到 prediction_history"""
        for event_data in report["events"]:
            record = {
                "viewpoint_id": report["viewpoint_id"],
                "prediction_date": report["meta"]["backtest_run_at"],
                "target_date": report["target_date"],
                "event_type": event_data["event_type"],
                "predicted_score": event_data["total_score"],
                "predicted_status": event_data["status"],
                "confidence": event_data["confidence"],
                "conditions_json": None,
                "is_backtest": True,
                "data_source": report["data_source"],
            }
            self._cache_repo.save_prediction(record)
