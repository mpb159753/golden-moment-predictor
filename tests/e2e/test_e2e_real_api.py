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

import pytest
from click.testing import CliRunner

from gmp.main import cli


# ==================== Helpers ====================


def _invoke(runner, args):
    """统一 invoke，自动添加 --log-level WARNING 避免过多日志"""
    return runner.invoke(cli, ["--log-level", "WARNING"] + args)


def _extract_json(output: str) -> dict:
    """从可能包含日志的混合输出中提取 JSON 对象。

    CliRunner 会混合 stdout 和 stderr，导致 structlog 日志混入输出。
    此函数查找第一个 '{' 到最后一个 '}' 的范围作为 JSON。
    """
    # 去除 ANSI 转义码
    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in output: {output[:200]!r}")
    return json.loads(clean[start:end + 1])


# ==================== Task 1: 单站预测全链路验证 ====================


@pytest.mark.e2e
def test_predict_single_day_real_api():
    """使用真实 API 预测牛背山 1 天"""
    runner = CliRunner()
    result = _invoke(runner, ["predict", "niubei_gongga", "--days", "1", "--output", "json"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json(result.output)

    # 验证 JSON 结构完整性
    assert data["viewpoint_id"] == "niubei_gongga"
    assert "daily" in data
    assert len(data["daily"]) == 1

    # 验证事件评分合理性
    day = data["daily"][0]
    assert "date" in day
    assert "summary" in day
    assert "events" in day

    # 每个事件的 score 在 [0, 100] 范围内
    for event in day["events"]:
        assert 0 <= event["score"] <= 100
        assert event["status"] in ["Perfect", "Recommended", "Possible", "Not Recommended"]
        assert event["confidence"] in ["High", "Medium", "Low"]


@pytest.mark.e2e
def test_predict_seven_days_real_api():
    """使用真实 API 预测牛背山 7 天"""
    runner = CliRunner()
    result = _invoke(runner, ["predict", "niubei_gongga", "--days", "7", "--output", "json"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json(result.output)
    assert len(data["daily"]) == 7

    # 每天都有日期、摘要和事件列表
    for day in data["daily"]:
        assert "date" in day
        assert "summary" in day
        assert isinstance(day["events"], list)


@pytest.mark.e2e
def test_predict_events_filter_real_api():
    """事件过滤仅返回指定事件"""
    runner = CliRunner()
    result = _invoke(runner, [
        "predict", "niubei_gongga", "--days", "1",
        "--events", "cloud_sea,frost", "--output", "json"
    ])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json(result.output)

    # 仅包含 cloud_sea 和 frost 事件 (可能为空列表, 取决于天气触发)
    allowed_events = {"cloud_sea", "frost"}
    for day in data["daily"]:
        for event in day["events"]:
            assert event["event_type"] in allowed_events


# ==================== Task 2: 缓存验证 ====================


@pytest.mark.e2e
def test_cache_hit_on_second_call(tmp_path):
    """第二次调用应命中缓存，不重复调用 API"""
    import yaml

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

    # 缓存命中后应显著更快
    assert t2_duration < t1_duration * 0.5, (
        f"Cache not effective: first={t1_duration:.2f}s, second={t2_duration:.2f}s"
    )

    # 两次输出的评分应一致 (相同数据 → 相同评分)
    data1 = _extract_json(result1.output)
    data2 = _extract_json(result2.output)
    # 移除 generated_at (时间戳不同)
    data1.pop("generated_at", None)
    data2.pop("generated_at", None)
    assert data1 == data2


# ==================== Task 3: 线路预测验证 ====================


@pytest.mark.e2e
def test_predict_route_real_api():
    """线路预测: 至少需要 2 个观景台配置"""
    runner = CliRunner()
    result = _invoke(runner, ["predict-route", "lixiao", "--days", "1", "--output", "json"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = _extract_json(result.output)

    assert "route_id" in data
    assert "stops" in data
    assert len(data["stops"]) >= 1

    # 每站格式正确
    for stop in data["stops"]:
        assert "viewpoint_id" in stop
        assert "order" in stop
        assert "forecast" in stop


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

    # 验证文件系统输出
    assert (output_dir / "index.json").exists()
    assert (output_dir / "meta.json").exists()

    # 至少一个 viewpoint 有 forecast.json
    viewpoint_dirs = list((output_dir / "viewpoints").iterdir())
    assert len(viewpoint_dirs) >= 1

    for vp_dir in viewpoint_dirs:
        assert (vp_dir / "forecast.json").exists()
        # timeline 按日期保存: timeline_YYYY-MM-DD.json
        timeline_files = list(vp_dir.glob("timeline_*.json"))
        assert len(timeline_files) >= 1

        # 验证 JSON 可解析
        forecast = json.loads((vp_dir / "forecast.json").read_text())
        assert "viewpoint_id" in forecast

    # 验证归档
    archive_dirs = list(archive_dir.iterdir())
    assert len(archive_dirs) == 1


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
    data = _extract_json(result.output)

    assert data["is_backtest"] is True
    assert data["target_date"] == past_date
    assert data["data_source"] in ["cache", "archive"]
    assert "events" in data


# ==================== Task 6: 错误处理验证 ====================


@pytest.mark.e2e
def test_invalid_viewpoint_error():
    """不存在的观景台 → 错误退出"""
    runner = CliRunner()
    result = _invoke(runner, ["predict", "不存在的id"])
    assert result.exit_code == 1


@pytest.mark.e2e
def test_invalid_route_error():
    """不存在的线路 → 错误退出"""
    runner = CliRunner()
    result = _invoke(runner, ["predict-route", "不存在的id"])
    assert result.exit_code != 0


@pytest.mark.e2e
def test_backtest_future_date_error():
    """回测未来日期 → 错误退出"""
    future_date = (date.today() + timedelta(days=7)).isoformat()

    runner = CliRunner()
    result = _invoke(runner, ["backtest", "niubei_gongga", "--date", future_date])
    assert result.exit_code != 0
