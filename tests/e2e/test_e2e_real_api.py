"""tests/e2e/test_e2e_real_api.py — E2E 验收测试 (真实 API)

不使用任何 Mock，调用真实的 Open-Meteo API 验证完整管线。
通过 `pytest -m e2e` 标记区分，避免在快速测试中执行。
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, timedelta
from pathlib import Path

import yaml
import pytest
from click.testing import CliRunner

from gmp.main import cli
from gmp.scoring.engine import _CAPABILITY_EVENT_MAP


# ==================== 动态常量构建 ====================


def _load_viewpoint_expected_event_types(viewpoint_id: str) -> set[str]:
    """从配置文件 + 映射表动态构建期望的 event_types"""
    config_path = Path(f"config/viewpoints/{viewpoint_id}.yaml")
    with open(config_path) as f:
        vp_config = yaml.safe_load(f)
    event_types: set[str] = set()
    for cap in vp_config["capabilities"]:
        mapped = _CAPABILITY_EVENT_MAP.get(cap, [cap])
        event_types.update(mapped)
    return event_types


def _load_route_expected_stops(route_id: str) -> set[str]:
    """从配置文件动态构建期望的 stop viewpoint_ids"""
    config_path = Path(f"config/routes/{route_id}.yaml")
    with open(config_path) as f:
        route_config = yaml.safe_load(f)
    return {s["viewpoint_id"] for s in route_config["stops"]}


def _load_route_name(route_id: str) -> str:
    """从配置文件获取线路名称"""
    config_path = Path(f"config/routes/{route_id}.yaml")
    with open(config_path) as f:
        route_config = yaml.safe_load(f)
    return route_config["name"]


def _load_viewpoint_name(viewpoint_id: str) -> str:
    """从配置文件获取观景台名称"""
    config_path = Path(f"config/viewpoints/{viewpoint_id}.yaml")
    with open(config_path) as f:
        vp_config = yaml.safe_load(f)
    return vp_config["name"]


# 动态构建常量 (基于配置文件，不硬编码)
NIUBEI_EXPECTED_EVENT_TYPES = _load_viewpoint_expected_event_types("niubei_gongga")
NIUBEI_VIEWPOINT_NAME = _load_viewpoint_name("niubei_gongga")
LIXIAO_EXPECTED_STOPS = _load_route_expected_stops("lixiao")
LIXIAO_ROUTE_NAME = _load_route_name("lixiao")

# 全年活跃的 plugin (无 season_months 限制)
# 注意: 所有 plugin 都有天气触发条件，单日可能不产出，
# 但 7 天内至少应出现其中大部分。
YEAR_ROUND_EVENT_TYPES = {"cloud_sea", "stargazing"}

# 所有合法的 status 值
VALID_STATUSES = {"Perfect", "Recommended", "Possible", "Not Recommended"}

# 所有合法的 confidence 值
VALID_CONFIDENCES = {"High", "Medium", "Low"}


# ==================== Helpers ====================


def _invoke(runner, args):
    """统一 invoke，自动添加 --log-level WARNING 避免过多日志"""
    return runner.invoke(cli, ["--log-level", "WARNING"] + args)


def _extract_json_object(output: str) -> dict:
    """从可能包含日志的混合输出中提取 JSON 对象 ({...})。

    CliRunner 会混合 stdout 和 stderr，导致 structlog 日志混入输出。
    此函数查找第一个 '{' 到最后一个 '}' 的范围作为 JSON。
    """
    # 去除 ANSI 转义码
    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in output: {output[:200]!r}")
    return json.loads(clean[start:end + 1])


def _extract_json_array(output: str) -> list:
    """从输出中提取 JSON 数组 ([...])。

    先去除非 JSON 前缀行，再从剩余文本中定位 JSON 数组。
    """
    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
    # 按行过滤: 找到第一个以 '[' 开头的行
    lines = clean.split("\n")
    json_start_line = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            json_start_line = i
            break
    remaining = "\n".join(lines[json_start_line:])
    start = remaining.find("[")
    end = remaining.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in output: {output[:200]!r}")
    return json.loads(remaining[start:end + 1])


def _strip_generated_at(obj):
    """递归移除字典中所有 'generated_at' 字段，用于比较两次输出"""
    if isinstance(obj, dict):
        return {k: _strip_generated_at(v) for k, v in obj.items() if k != "generated_at"}
    elif isinstance(obj, list):
        return [_strip_generated_at(item) for item in obj]
    return obj


def _assert_event_fields_complete(event: dict):
    """断言 forecast 输出中单个 event 的字段完整性"""
    required_keys = {
        "event_type", "display_name", "time_window", "score",
        "status", "confidence", "tags", "conditions", "score_breakdown",
    }
    missing = required_keys - set(event.keys())
    assert not missing, f"Event {event.get('event_type')} 缺少字段: {missing}"

    assert isinstance(event["score"], int)
    assert 0 <= event["score"] <= 100, f"Score {event['score']} 超出 [0, 100]"
    assert event["status"] in VALID_STATUSES, f"非法 status: {event['status']}"
    assert event["confidence"] in VALID_CONFIDENCES, f"非法 confidence: {event['confidence']}"
    assert isinstance(event["tags"], list)
    assert isinstance(event["conditions"], list)
    assert isinstance(event["score_breakdown"], dict)
    assert event["display_name"], "display_name 不能为空"


def _assert_backtest_event_fields(event: dict, expected_event_types: set):
    """断言 backtest 输出中单个 event 的字段完整性"""
    required_keys = {"event_type", "total_score", "status", "breakdown", "confidence"}
    missing = required_keys - set(event.keys())
    assert not missing, f"Backtest event {event.get('event_type')} 缺少字段: {missing}"

    assert event["event_type"] in expected_event_types, (
        f"意外的 event_type: {event['event_type']}，预期: {expected_event_types}"
    )
    assert isinstance(event["total_score"], int)
    assert 0 <= event["total_score"] <= 100, f"total_score {event['total_score']} 超出 [0, 100]"
    assert event["status"] in VALID_STATUSES, f"非法 status: {event['status']}"
    assert event["confidence"] in VALID_CONFIDENCES, f"非法 confidence: {event['confidence']}"
    assert isinstance(event["breakdown"], dict), "breakdown 应为 dict"


def _assert_forecast_structure(
    data: dict,
    expected_event_types: set,
    *,
    min_events_per_day: int = 0,
):
    """断言 forecast 输出的通用结构

    Args:
        data: forecast JSON 数据
        expected_event_types: 允许的 event_type 集合
        min_events_per_day: 每天最少事件数 (0=不检查)
    """
    assert "viewpoint_id" in data
    assert "viewpoint_name" in data
    assert "generated_at" in data
    assert "forecast_days" in data
    assert "daily" in data
    assert isinstance(data["daily"], list)
    assert len(data["daily"]) == data["forecast_days"]

    for day in data["daily"]:
        assert re.match(r"\d{4}-\d{2}-\d{2}", day["date"]), f"日期格式错误: {day['date']}"
        assert isinstance(day["summary"], str) and day["summary"], "summary 不能为空"
        assert isinstance(day["events"], list)

        if min_events_per_day > 0:
            assert len(day["events"]) >= min_events_per_day, (
                f"日期 {day['date']} 的 events 数量 ({len(day['events'])}) "
                f"少于要求的最少 {min_events_per_day} 个"
            )

        for event in day["events"]:
            assert event["event_type"] in expected_event_types, (
                f"意外的 event_type: {event['event_type']}，"
                f"预期: {expected_event_types}"
            )
            _assert_event_fields_complete(event)

        # best_event 验证: events 非空时必须有 best_event，为空时必须为 None
        if day["events"]:
            assert day["best_event"] is not None, "有事件时 best_event 不应为 None"
            assert "event_type" in day["best_event"]
            assert "score" in day["best_event"]
            assert "status" in day["best_event"]
        else:
            assert day["best_event"] is None, "无事件时 best_event 应为 None"


# ==================== Task 1: 单站预测全链路验证 ====================


@pytest.mark.e2e
def test_predict_single_day_real_api():
    """使用真实 API 预测牛背山 1 天"""
    runner = CliRunner()
    result = _invoke(runner, ["predict", "niubei_gongga", "--days", "1", "--output", "json"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_object(result.output)

    # 结构验证
    assert data["viewpoint_id"] == "niubei_gongga"
    assert data["viewpoint_name"] == NIUBEI_VIEWPOINT_NAME
    _assert_forecast_structure(data, NIUBEI_EXPECTED_EVENT_TYPES)

    # 单日至少应有部分事件产出
    day = data["daily"][0]
    assert len(day["events"]) > 0, (
        "events 列表为空——可能存在 Plugin 静默失败。"
        f"已配置 event_types: {NIUBEI_EXPECTED_EVENT_TYPES}"
    )

    # 实际返回的 event_types 应是配置期望的子集 (不应出现意外类型)
    actual_event_types = {e["event_type"] for e in day["events"]}
    unexpected = actual_event_types - NIUBEI_EXPECTED_EVENT_TYPES
    assert not unexpected, f"出现超出配置期望的 event_type: {unexpected}"


@pytest.mark.e2e
def test_predict_seven_days_real_api():
    """使用真实 API 预测牛背山 7 天"""
    runner = CliRunner()
    result = _invoke(runner, ["predict", "niubei_gongga", "--days", "7", "--output", "json"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_object(result.output)
    assert len(data["daily"]) == 7

    # 结构验证
    _assert_forecast_structure(data, NIUBEI_EXPECTED_EVENT_TYPES)

    # 7 天中至少有 1 天有事件
    # 注意: 所有 Plugin 都有天气触发条件 (如云底高度、夜间云量等)
    # 在极端天气下大部分天可能无事件触发，但 7 天内至少应有 1 天
    non_empty_days = [d for d in data["daily"] if d["events"]]
    assert len(non_empty_days) >= 1, (
        "7 天预测中所有天的 events 都为空，可能存在 Plugin 问题"
    )

    # 7 天聚合: 收集所有出现的 event_types，验证不超出配置范围
    all_event_types: set[str] = set()
    for day in data["daily"]:
        all_event_types.update(e["event_type"] for e in day["events"])
    unexpected = all_event_types - NIUBEI_EXPECTED_EVENT_TYPES
    assert not unexpected, (
        f"7 天聚合后出现超出配置的 event_type: {unexpected}"
    )

    # 日期应连续
    dates = [d["date"] for d in data["daily"]]
    for i in range(1, len(dates)):
        d_prev = date.fromisoformat(dates[i - 1])
        d_curr = date.fromisoformat(dates[i])
        assert d_curr == d_prev + timedelta(days=1), (
            f"日期不连续: {dates[i - 1]} → {dates[i]}"
        )


@pytest.mark.e2e
def test_predict_events_filter_real_api():
    """事件过滤仅返回指定事件，且不能为空"""
    runner = CliRunner()
    filter_events = {"cloud_sea", "frost"}
    # 使用 7 天增加事件产出概率 (Plugin 有天气触发条件)
    result = _invoke(runner, [
        "predict", "niubei_gongga", "--days", "7",
        "--events", ",".join(filter_events), "--output", "json"
    ])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_object(result.output)

    # 所有天的事件汇总
    all_actual_types: set[str] = set()
    has_events = False
    for day in data["daily"]:
        actual_types = {e["event_type"] for e in day["events"]}
        all_actual_types.update(actual_types)
        if day["events"]:
            has_events = True

        # 排除验证: 每天都不应包含未指定的事件类型
        unexpected = actual_types - filter_events
        assert not unexpected, f"过滤后出现不允许的 event_type: {unexpected}"

    # 包含验证: 7 天聚合后，过滤集合中的事件至少应出现部分
    assert has_events, (
        f"7 天过滤后所有 events 为空，指定 {filter_events} 但未返回任何事件"
    )
    # 至少返回了过滤集合中的某些事件 (确认过滤生效而非全部丢弃)
    assert all_actual_types, (
        f"过滤后无任何 event_type 产出，指定: {filter_events}"
    )


# ==================== Task 2: 缓存验证 ====================


@pytest.mark.e2e
def test_cache_hit_on_second_call(tmp_path):
    """第二次调用应命中缓存，不重复调用 API"""

    tmp_config = tmp_path / "engine_config.yaml"
    # 读取原始配置并修改 db_path
    with open("config/engine_config.yaml") as f:
        config_data = yaml.safe_load(f)
    config_data["cache"]["db_path"] = str(tmp_path / "test_cache.db")
    with open(tmp_config, "w") as f:
        yaml.dump(config_data, f)

    runner = CliRunner()

    # 第一次调用 (真实 API)
    t1_start = time.time()
    result1 = _invoke(runner, [
        "predict", "niubei_gongga", "--days", "1",
        "--output", "json", "--config", str(tmp_config),
    ])
    t1_duration = time.time() - t1_start
    assert result1.exit_code == 0, f"First call failed: {result1.output}"

    # 第二次调用 (应命中缓存)
    t2_start = time.time()
    result2 = _invoke(runner, [
        "predict", "niubei_gongga", "--days", "1",
        "--output", "json", "--config", str(tmp_config),
    ])
    t2_duration = time.time() - t2_start
    assert result2.exit_code == 0, f"Second call failed: {result2.output}"

    # 缓存命中后应更快: 使用相对+绝对组合阈值避免 flaky
    assert t2_duration < max(t1_duration * 0.8, 2.0), (
        f"Cache not effective: first={t1_duration:.2f}s, second={t2_duration:.2f}s"
    )

    # 两次输出的评分应一致 (递归移除所有 generated_at 时间戳)
    data1 = _strip_generated_at(_extract_json_object(result1.output))
    data2 = _strip_generated_at(_extract_json_object(result2.output))
    assert data1 == data2, "缓存命中后评分结果不一致"


# ==================== Task 3: 线路预测验证 ====================


@pytest.mark.e2e
def test_predict_route_real_api():
    """线路预测: 至少需要 2 个观景台配置"""
    runner = CliRunner()
    result = _invoke(runner, ["predict-route", "lixiao", "--days", "1", "--output", "json"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_object(result.output)

    assert data["route_id"] == "lixiao"
    assert data["route_name"] == LIXIAO_ROUTE_NAME
    assert "stops" in data
    assert len(data["stops"]) == len(LIXIAO_EXPECTED_STOPS), (
        f"预期 {len(LIXIAO_EXPECTED_STOPS)} 个 stops，实际 {len(data['stops'])}"
    )

    # 站点 ID 匹配配置
    actual_stop_ids = {s["viewpoint_id"] for s in data["stops"]}
    assert actual_stop_ids == LIXIAO_EXPECTED_STOPS, (
        f"站点不匹配: 预期 {LIXIAO_EXPECTED_STOPS}, 实际 {actual_stop_ids}"
    )

    # 每站的 forecast 深度验证
    for stop in data["stops"]:
        assert "viewpoint_id" in stop
        assert "viewpoint_name" in stop
        assert "order" in stop
        assert isinstance(stop["order"], int) and stop["order"] > 0
        assert "stay_note" in stop, "stop 缺少 stay_note 字段"
        assert "forecast" in stop

        # 动态构建该站的期望 event_types
        stop_expected_events = _load_viewpoint_expected_event_types(stop["viewpoint_id"])

        forecast = stop["forecast"]
        _assert_forecast_structure(forecast, stop_expected_events, min_events_per_day=1)


# ==================== Task 4: 批量生成验证 ====================


@pytest.mark.e2e
def test_generate_all_real_api(tmp_path):
    """批量生成并验证文件系统输出"""
    output_dir = tmp_path / "public" / "data"
    archive_dir = tmp_path / "archive"

    runner = CliRunner()
    result = _invoke(runner, [
        "generate-all", "--days", "1",
        "--output", str(output_dir),
        "--archive", str(archive_dir),
    ])

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # 验证 index.json
    assert (output_dir / "index.json").exists()
    index_data = json.loads((output_dir / "index.json").read_text())
    assert "viewpoints" in index_data
    assert "routes" in index_data
    assert isinstance(index_data["viewpoints"], list)
    assert len(index_data["viewpoints"]) >= 1
    assert isinstance(index_data["routes"], list)
    assert len(index_data["routes"]) >= 1

    # 验证 meta.json 内容
    assert (output_dir / "meta.json").exists()
    meta_data = json.loads((output_dir / "meta.json").read_text())
    assert "generated_at" in meta_data, "meta.json 缺少 generated_at"
    assert "viewpoints_count" in meta_data, "meta.json 缺少 viewpoints_count"
    assert meta_data["viewpoints_count"] >= 1

    # 至少一个 viewpoint 有 forecast.json
    viewpoint_dirs = list((output_dir / "viewpoints").iterdir())
    assert len(viewpoint_dirs) >= 1

    for vp_dir in viewpoint_dirs:
        # forecast.json 存在且可解析
        assert (vp_dir / "forecast.json").exists()
        forecast = json.loads((vp_dir / "forecast.json").read_text())
        assert "viewpoint_id" in forecast
        assert "daily" in forecast
        assert isinstance(forecast["daily"], list)

        # 事件字段完整性
        for day in forecast["daily"]:
            for event in day.get("events", []):
                _assert_event_fields_complete(event)

        # timeline 按日期保存: timeline_YYYY-MM-DD.json
        timeline_files = list(vp_dir.glob("timeline_*.json"))
        assert len(timeline_files) >= 1

    # 验证 routes 目录
    routes_dir = output_dir / "routes"
    if routes_dir.exists():
        route_dirs = list(routes_dir.iterdir())
        for rt_dir in route_dirs:
            assert (rt_dir / "forecast.json").exists(), (
                f"线路 {rt_dir.name} 缺少 forecast.json"
            )
            route_forecast = json.loads((rt_dir / "forecast.json").read_text())
            assert "route_id" in route_forecast
            assert "stops" in route_forecast

    # 验证归档
    archive_dirs = list(archive_dir.iterdir())
    assert len(archive_dirs) == 1
    # 归档目录内应有文件
    archive_contents = list(archive_dirs[0].rglob("*"))
    assert len(archive_contents) >= 1, "归档目录为空，归档未生效"


# ==================== Task 5: 回测验证 ====================


@pytest.mark.e2e
def test_backtest_real_api():
    """回测: 使用 Archive API 获取历史天气"""
    # 选一个 30 天内的过去日期
    past_date = (date.today() - timedelta(days=7)).isoformat()

    runner = CliRunner()
    result = _invoke(runner, [
        "backtest", "niubei_gongga", "--date", past_date
    ])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_object(result.output)

    assert data["is_backtest"] is True
    assert data["target_date"] == past_date
    assert data["viewpoint_id"] == "niubei_gongga"
    assert data["data_source"] in ["cache", "archive"]
    assert "events" in data
    assert isinstance(data["events"], list)

    # 回测应有事件结果
    assert len(data["events"]) > 0, "回测 events 为空，可能存在 Plugin 问题"

    # meta 字段验证
    assert "meta" in data, "回测报告缺少 meta 字段"
    assert "backtest_run_at" in data["meta"], "meta 缺少 backtest_run_at"

    # 每个事件的字段完整性 (backtest 格式)
    for event in data["events"]:
        _assert_backtest_event_fields(event, NIUBEI_EXPECTED_EVENT_TYPES)


@pytest.mark.e2e
def test_backtest_seasonal_plugin_real_api():
    """通过回测验证季节性 plugin 在对应季节的产出

    选取 1 月份 (冬季) 日期，验证 frost/snow_tree/ice_icicle 等冬季 plugin 能产出结果。
    """
    # 选取去年 1 月 15 日 (确保在 backtest_max_history_days=365 范围内)
    today = date.today()
    winter_date = date(today.year - 1, 1, 15)
    # 如果距今超过 365 天，使用今年的 1 月
    if (today - winter_date).days > 360:
        winter_date = date(today.year, 1, 15)
    # 如果今年 1 月 15 日是未来日期，退回到去年
    if winter_date >= today:
        winter_date = date(today.year - 1, 1, 15)

    runner = CliRunner()
    result = _invoke(runner, [
        "backtest", "niubei_gongga", "--date", winter_date.isoformat()
    ])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_object(result.output)
    assert data["is_backtest"] is True

    # 冬季回测应有事件
    assert len(data["events"]) > 0, "冬季回测 events 为空"

    actual_types = {e["event_type"] for e in data["events"]}
    # 实际返回的类型应全部在配置范围内
    unexpected = actual_types - NIUBEI_EXPECTED_EVENT_TYPES
    assert not unexpected, f"回测出现超出配置的 event_type: {unexpected}"

    # 冬季回测应至少产出多种事件类型
    assert len(actual_types) >= 2, (
        f"冬季回测仅产出 {len(actual_types)} 种事件: {actual_types}，预期至少 2 种"
    )


# ==================== Task 6: 错误处理验证 ====================


@pytest.mark.e2e
def test_invalid_viewpoint_error():
    """不存在的观景台 → 错误退出"""
    runner = CliRunner()
    result = _invoke(runner, ["predict", "不存在的id"])
    assert result.exit_code == 1, f"预期 exit_code=1，实际={result.exit_code}"
    assert "错误" in result.output or "未找到" in result.output, (
        f"错误输出中缺少有意义的错误信息: {result.output[:200]}"
    )


@pytest.mark.e2e
def test_invalid_route_error():
    """不存在的线路 → 错误退出 (RouteNotFoundError → GMPError → exit 3)"""
    runner = CliRunner()
    result = _invoke(runner, ["predict-route", "不存在的id"])
    assert result.exit_code != 0, f"预期非零 exit_code，实际={result.exit_code}"
    assert "错误" in result.output or "未找到" in result.output, (
        f"错误输出中缺少有意义的错误信息: {result.output[:200]}"
    )


@pytest.mark.e2e
def test_backtest_future_date_error():
    """回测未来日期 → 错误退出"""
    future_date = (date.today() + timedelta(days=7)).isoformat()

    runner = CliRunner()
    result = _invoke(runner, ["backtest", "niubei_gongga", "--date", future_date])
    assert result.exit_code == 1, f"预期 exit_code=1，实际={result.exit_code}"
    assert "日期" in result.output or "错误" in result.output, (
        f"错误输出中缺少有意义的错误信息: {result.output[:200]}"
    )


# ==================== Task 7: 命令覆盖 ====================


@pytest.mark.e2e
def test_list_viewpoints_real_api():
    """list-viewpoints 命令应列出所有观景台"""
    runner = CliRunner()

    # JSON 格式
    result = _invoke(runner, ["list-viewpoints", "--output", "json"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_array(result.output)
    assert isinstance(data, list)
    assert len(data) >= 1

    vp_ids = {vp["id"] for vp in data}
    assert "niubei_gongga" in vp_ids

    for vp in data:
        assert "id" in vp
        assert "name" in vp
        assert "location" in vp
        assert "capabilities" in vp
        assert isinstance(vp["capabilities"], list)
        assert len(vp["capabilities"]) >= 1

    # Table 格式
    result_table = _invoke(runner, ["list-viewpoints", "--output", "table"])
    assert result_table.exit_code == 0, f"CLI table failed: {result_table.output}"
    assert "niubei_gongga" in result_table.output


@pytest.mark.e2e
def test_list_routes_real_api():
    """list-routes 命令应列出所有线路"""
    runner = CliRunner()

    # JSON 格式
    result = _invoke(runner, ["list-routes", "--output", "json"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json_array(result.output)
    assert isinstance(data, list)
    assert len(data) >= 1

    route_ids = {r["id"] for r in data}
    assert "lixiao" in route_ids

    for route in data:
        assert "id" in route
        assert "name" in route
        assert "stops_count" in route
        assert "stops" in route
        assert route["stops_count"] == len(route["stops"])

    # Table 格式
    result_table = _invoke(runner, ["list-routes", "--output", "table"])
    assert result_table.exit_code == 0, f"CLI table failed: {result_table.output}"
    assert "lixiao" in result_table.output


@pytest.mark.e2e
def test_predict_table_output_real_api():
    """predict 的 table 格式输出应有内容"""
    runner = CliRunner()
    result = _invoke(runner, ["predict", "niubei_gongga", "--days", "1"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    # table 格式应有非空输出 (至少包含观景台名称)
    assert len(result.output.strip()) > 0, "table 输出为空"
    assert NIUBEI_VIEWPOINT_NAME in result.output, (
        f"table 输出中缺少观景台名称 '{NIUBEI_VIEWPOINT_NAME}'"
    )


@pytest.mark.e2e
def test_predict_output_file_real_api(tmp_path):
    """--output-file 应将 JSON 输出写入指定文件"""
    out_file = tmp_path / "result.json"
    runner = CliRunner()
    result = _invoke(runner, [
        "predict", "niubei_gongga", "--days", "1",
        "--output", "json", "--output-file", str(out_file),
    ])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert out_file.exists(), f"输出文件 {out_file} 未创建"

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["viewpoint_id"] == "niubei_gongga"
    assert "daily" in data


@pytest.mark.e2e
def test_days_boundary_values():
    """--days 边界值: 0 和 17 应报错"""
    runner = CliRunner()

    # --days 0 应报错 (IntRange(1, 16))
    result_zero = _invoke(runner, ["predict", "niubei_gongga", "--days", "0", "--output", "json"])
    assert result_zero.exit_code != 0, "days=0 应报错"

    # --days 17 应报错
    result_over = _invoke(runner, ["predict", "niubei_gongga", "--days", "17", "--output", "json"])
    assert result_over.exit_code != 0, "days=17 应报错"
