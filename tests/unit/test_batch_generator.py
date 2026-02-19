"""tests/unit/test_batch_generator.py — BatchGenerator 单元测试"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from gmp.core.models import (
    ForecastDay,
    Location,
    PipelineResult,
    Route,
    RouteStop,
    ScoreResult,
    Viewpoint,
)
from gmp.core.config_loader import ViewpointConfig, RouteConfig
from gmp.output.forecast_reporter import ForecastReporter
from gmp.output.timeline_reporter import TimelineReporter
from gmp.output.json_file_writer import JSONFileWriter


# ══════════════════════════════════════════════════════
# Test Helpers
# ══════════════════════════════════════════════════════

_CST = timezone(timedelta(hours=8))


def _make_viewpoint(vp_id: str = "vp_a") -> Viewpoint:
    return Viewpoint(
        id=vp_id,
        name=f"观景台_{vp_id}",
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["cloud_sea"],
        targets=[],
    )


def _make_pipeline_result(vp_id: str = "vp_a", days: int = 1) -> PipelineResult:
    """创建一个基本的 PipelineResult"""
    forecast_days = []
    for d in range(days):
        target_date = datetime.now(_CST).date() + timedelta(days=d)
        forecast_days.append(
            ForecastDay(
                date=target_date.isoformat(),
                summary="晴朗天气",
                best_event=None,
                events=[
                    ScoreResult(
                        event_type="cloud_sea",
                        total_score=80,
                        status="Recommended",
                        breakdown={"test": {"score": 80, "max": 100}},
                        time_window="06:00 - 09:00",
                    )
                ],
                confidence="high",
            )
        )
    return PipelineResult(
        viewpoint=_make_viewpoint(vp_id),
        forecast_days=forecast_days,
        meta={"generated_at": datetime.now(_CST).isoformat(), "data_freshness": "fresh"},
    )


def _make_route(route_id: str = "route_a", stops: list[str] | None = None) -> Route:
    stop_ids = stops or ["vp_a", "vp_b"]
    return Route(
        id=route_id,
        name=f"线路_{route_id}",
        stops=[
            RouteStop(viewpoint_id=sid, order=i + 1) for i, sid in enumerate(stop_ids)
        ],
    )


def _build_batch_generator(
    *,
    viewpoints: list[Viewpoint] | None = None,
    routes: list[Route] | None = None,
    scheduler_run_side_effect=None,
    scheduler_run_route_side_effect=None,
):
    """构建 BatchGenerator 及其 mock 依赖"""
    from gmp.core.batch_generator import BatchGenerator

    # Scheduler mock
    scheduler = MagicMock()
    if scheduler_run_side_effect is not None:
        scheduler.run.side_effect = scheduler_run_side_effect
    else:
        # 默认: run(vp_id) → 返回对应 vp_id 的 PipelineResult
        scheduler.run.side_effect = lambda vp_id, **kwargs: _make_pipeline_result(
            vp_id, days=kwargs.get("days", 7)
        )

    if scheduler_run_route_side_effect is not None:
        scheduler.run_route.side_effect = scheduler_run_route_side_effect
    else:
        scheduler.run_route.side_effect = lambda route_id, **kwargs: [
            _make_pipeline_result(sid, days=kwargs.get("days", 7))
            for sid in ["vp_a", "vp_b"]
        ]

    # ViewpointConfig mock
    vps = viewpoints or [_make_viewpoint("vp_a"), _make_viewpoint("vp_b")]
    viewpoint_config = MagicMock(spec=ViewpointConfig)
    viewpoint_config.list_all.return_value = vps
    viewpoint_config.get.side_effect = lambda vid: next(
        (v for v in vps if v.id == vid), None
    )

    # RouteConfig mock
    rts = routes or [_make_route("route_a")]
    route_config = MagicMock(spec=RouteConfig)
    route_config.list_all.return_value = rts
    route_config.get.side_effect = lambda rid: next(
        (r for r in rts if r.id == rid), None
    )

    # Reporters mock
    forecast_reporter = MagicMock(spec=ForecastReporter)
    forecast_reporter.generate.return_value = {"viewpoint_id": "mock", "daily": []}
    forecast_reporter.generate_route.return_value = {
        "route_id": "mock",
        "stops": [],
    }

    timeline_reporter = MagicMock(spec=TimelineReporter)
    timeline_reporter.generate.return_value = {
        "viewpoint_id": "mock",
        "hourly": [],
    }

    # JSONFileWriter mock
    json_writer = MagicMock(spec=JSONFileWriter)

    bg = BatchGenerator(
        scheduler=scheduler,
        viewpoint_config=viewpoint_config,
        route_config=route_config,
        forecast_reporter=forecast_reporter,
        timeline_reporter=timeline_reporter,
        json_writer=json_writer,
    )

    return bg, scheduler, forecast_reporter, timeline_reporter, json_writer


# ══════════════════════════════════════════════════════
# Happy Path Tests
# ══════════════════════════════════════════════════════


class TestHappyPath:
    """2 viewpoints + 1 route → 完整文件集"""

    def test_generates_all_viewpoints(self):
        """2 个 viewpoint → scheduler.run() 被调用 2 次"""
        bg, scheduler, *_ = _build_batch_generator()

        result = bg.generate_all(days=7)

        assert scheduler.run.call_count == 2
        called_vp_ids = [c.args[0] for c in scheduler.run.call_args_list]
        assert "vp_a" in called_vp_ids
        assert "vp_b" in called_vp_ids

    def test_generates_all_routes(self):
        """1 个 route → scheduler.run_route() 被调用 1 次"""
        bg, scheduler, *_ = _build_batch_generator()

        result = bg.generate_all(days=7)

        scheduler.run_route.assert_called_once_with("route_a", days=7, events=None)

    def test_writes_viewpoint_files(self):
        """每个 viewpoint → JSONFileWriter.write_viewpoint() 被调用"""
        bg, _, forecast_reporter, timeline_reporter, json_writer = (
            _build_batch_generator()
        )

        bg.generate_all(days=7)

        assert json_writer.write_viewpoint.call_count == 2

    def test_writes_route_files(self):
        """route → JSONFileWriter.write_route() 被调用"""
        bg, _, forecast_reporter, timeline_reporter, json_writer = (
            _build_batch_generator()
        )

        bg.generate_all(days=7)

        assert json_writer.write_route.call_count == 1

    def test_writes_index_json(self):
        """生成 index.json — 富对象格式"""
        bg, _, _, _, json_writer = _build_batch_generator()

        bg.generate_all(days=7)

        json_writer.write_index.assert_called_once()
        index_args = json_writer.write_index.call_args
        viewpoints_list = index_args.args[0] if index_args.args else index_args.kwargs.get("viewpoints")
        routes_list = index_args.args[1] if len(index_args.args) > 1 else index_args.kwargs.get("routes")
        assert len(viewpoints_list) == 2
        assert len(routes_list) == 1
        # 验证富对象格式
        vp = viewpoints_list[0]
        assert isinstance(vp, dict)
        assert "id" in vp
        assert "name" in vp
        assert "location" in vp
        assert "capabilities" in vp
        assert "forecast_url" in vp
        assert vp["forecast_url"] == f"viewpoints/{vp['id']}/forecast.json"
        assert vp["location"]["lat"] == 29.75
        rt = routes_list[0]
        assert isinstance(rt, dict)
        assert "id" in rt
        assert "name" in rt
        assert "stops" in rt
        assert "forecast_url" in rt

    def test_index_json_capabilities_include_universal(self):
        """index.json 中每个 viewpoint 的 capabilities 合并通用能力"""
        bg, _, _, _, json_writer = _build_batch_generator()

        bg.generate_all(days=7)

        json_writer.write_index.assert_called_once()
        index_args = json_writer.write_index.call_args
        viewpoints_list = index_args.kwargs.get("viewpoints") or index_args.args[0]
        # _make_viewpoint 仅配了 ["cloud_sea"]，但 index.json 里应合并通用
        for vp in viewpoints_list:
            assert "clear_sky" in vp["capabilities"]
            assert "stargazing" in vp["capabilities"]
            assert "frost" in vp["capabilities"]
            assert "cloud_sea" in vp["capabilities"]  # 原始手动配的

    def test_writes_meta_json(self):
        """生成 meta.json 包含 generated_at, viewpoints_count, routes_count"""
        bg, _, _, _, json_writer = _build_batch_generator()

        bg.generate_all(days=7)

        json_writer.write_meta.assert_called_once()
        meta = json_writer.write_meta.call_args.args[0]
        assert "generated_at" in meta
        assert meta["viewpoints_count"] == 2
        assert meta["routes_count"] == 1

    def test_return_stats(self):
        """返回统计 dict"""
        bg, *_ = _build_batch_generator()

        result = bg.generate_all(days=7)

        assert result["viewpoints_processed"] == 2
        assert result["routes_processed"] == 1
        assert result["failed_viewpoints"] == []
        assert result["failed_routes"] == []

    def test_passes_events_to_scheduler(self):
        """events 参数传递给 scheduler"""
        bg, scheduler, *_ = _build_batch_generator()

        bg.generate_all(days=3, events=["cloud_sea"])

        for c in scheduler.run.call_args_list:
            assert c.kwargs.get("events") == ["cloud_sea"]

    def test_writes_per_day_timeline_files(self):
        """每个 viewpoint 的每个 forecast_day 生成 timeline_{date}.json"""
        bg, _, _, timeline_reporter, json_writer = _build_batch_generator()

        bg.generate_all(days=7)

        # 默认 _make_pipeline_result 生成 7 天 forecast_days
        # 2 个 viewpoints × 7 天 = 14 次 write_viewpoint_timeline
        assert json_writer.write_viewpoint_timeline.call_count == 2 * 7

    def test_timeline_reporter_called_per_day(self):
        """timeline_reporter.generate() 被每天调用"""
        bg, _, _, timeline_reporter, json_writer = _build_batch_generator()

        bg.generate_all(days=7)

        # 2 viewpoints × 7 天 = 14，加上可能的 timeline.json 回退调用
        assert timeline_reporter.generate.call_count >= 2 * 7


# ══════════════════════════════════════════════════════
# 容错 Tests
# ══════════════════════════════════════════════════════


class TestFaultTolerance:
    """容错测试"""

    def test_fail_fast_false_skips_failed_viewpoint(self):
        """fail_fast=False: 单站失败跳过，返回 failed_viewpoints"""
        call_count = 0

        def run_side_effect(vp_id, **kwargs):
            nonlocal call_count
            call_count += 1
            if vp_id == "vp_b":
                raise RuntimeError("vp_b 数据获取失败")
            return _make_pipeline_result(vp_id, days=kwargs.get("days", 7))

        bg, *_ = _build_batch_generator(scheduler_run_side_effect=run_side_effect)

        result = bg.generate_all(days=7, fail_fast=False)

        assert result["viewpoints_processed"] == 1
        assert "vp_b" in result["failed_viewpoints"]

    def test_fail_fast_true_raises_immediately(self):
        """fail_fast=True: 单站失败立即抛出异常"""

        def run_side_effect(vp_id, **kwargs):
            if vp_id == "vp_a":
                raise RuntimeError("vp_a error")
            return _make_pipeline_result(vp_id, days=kwargs.get("days", 7))

        bg, *_ = _build_batch_generator(scheduler_run_side_effect=run_side_effect)

        with pytest.raises(RuntimeError, match="vp_a error"):
            bg.generate_all(days=7, fail_fast=True)

    def test_fail_fast_false_skips_failed_route(self):
        """fail_fast=False: 线路失败跳过，返回 failed_routes"""

        def run_route_side_effect(route_id, **kwargs):
            raise RuntimeError(f"{route_id} 线路评分失败")

        bg, *_ = _build_batch_generator(
            scheduler_run_route_side_effect=run_route_side_effect
        )

        result = bg.generate_all(days=7, fail_fast=False)

        assert "route_a" in result["failed_routes"]
        assert result["routes_processed"] == 0

    def test_fail_fast_true_route_failure_raises(self):
        """fail_fast=True: 线路失败立即中止"""

        def run_route_side_effect(route_id, **kwargs):
            raise RuntimeError(f"{route_id} error")

        bg, *_ = _build_batch_generator(
            scheduler_run_route_side_effect=run_route_side_effect
        )

        with pytest.raises(RuntimeError, match="route_a error"):
            bg.generate_all(days=7, fail_fast=True)


# ══════════════════════════════════════════════════════
# 归档 Tests
# ══════════════════════════════════════════════════════


class TestArchive:
    """归档测试"""

    def test_no_archive_false_calls_archive(self):
        """no_archive=False → 调用 json_writer.archive()"""
        bg, _, _, _, json_writer = _build_batch_generator()

        bg.generate_all(days=7, no_archive=False)

        json_writer.archive.assert_called_once()

    def test_no_archive_true_skips_archive(self):
        """no_archive=True → 不调用 json_writer.archive()"""
        bg, _, _, _, json_writer = _build_batch_generator()

        bg.generate_all(days=7, no_archive=True)

        json_writer.archive.assert_not_called()

    def test_archive_timestamp_format(self):
        """归档 timestamp 格式为 YYYY-MM-DDTHH-MM"""
        bg, _, _, _, json_writer = _build_batch_generator()

        bg.generate_all(days=7, no_archive=False)

        ts = json_writer.archive.call_args.args[0]
        # 格式: 2025-01-15T10-30  (长度 16)
        assert len(ts) == 16
        assert ts[4] == "-"
        assert ts[7] == "-"
        assert ts[10] == "T"
        assert ts[13] == "-"


# ══════════════════════════════════════════════════════
# 输出统计 Tests
# ══════════════════════════════════════════════════════


class TestOutputStats:
    """输出统计"""

    def test_index_contains_successful_viewpoints_only(self):
        """index.json 只包含成功处理的 viewpoint（富对象格式）"""

        def run_side_effect(vp_id, **kwargs):
            if vp_id == "vp_b":
                raise RuntimeError("fail")
            return _make_pipeline_result(vp_id, days=kwargs.get("days", 7))

        bg, _, _, _, json_writer = _build_batch_generator(
            scheduler_run_side_effect=run_side_effect
        )

        bg.generate_all(days=7, fail_fast=False)

        json_writer.write_index.assert_called_once()
        call_kwargs = json_writer.write_index.call_args.kwargs
        call_args = json_writer.write_index.call_args.args
        viewpoints_list = call_kwargs.get("viewpoints") or call_args[0]
        assert len(viewpoints_list) == 1  # 只有 vp_a 成功
        assert viewpoints_list[0]["id"] == "vp_a"

    def test_result_output_dir(self):
        """返回结果包含 output_dir"""
        bg, *_ = _build_batch_generator()

        result = bg.generate_all(days=7)

        assert "output_dir" in result

    def test_result_archive_dir_when_archived(self):
        """归档时返回 archive_dir"""
        bg, *_ = _build_batch_generator()

        result = bg.generate_all(days=7, no_archive=False)

        assert result["archive_dir"] is not None

    def test_result_archive_dir_none_when_no_archive(self):
        """no_archive=True → archive_dir 为 None"""
        bg, *_ = _build_batch_generator()

        result = bg.generate_all(days=7, no_archive=True)

        assert result["archive_dir"] is None
