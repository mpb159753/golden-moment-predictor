# M15: E2E 验收测试 (真实 API)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 使用真实 Open-Meteo API 进行端到端验收测试，验证从 CLI 命令到 JSON 文件输出的完整管线。

**依赖模块:** M14 (CLI 入口) — 所有前置模块均需完成

---

## 背景

这是整个 GMP 项目的最终验收模块。与 M12 集成测试和 M14 CLI 测试不同，本模块：
- **不使用任何 Mock** — 调用真实的 Open-Meteo API
- 验证真实网络环境下的完整管线行为
- 测试真实 SQLite 缓存写入/读取
- 测试真实文件系统输出
- 验证各 Plugin 在真实天气数据下的评分合理性

> [!IMPORTANT]
> 此模块的测试需要网络连接，执行时间较长（涉及真实 API 调用）。建议通过 `pytest -m e2e` 标记区分，避免在 CI 快速测试中执行。

---

## Task 1: 单站预测全链路验证

**Files:**
- Create: `tests/e2e/test_e2e_real_api.py`

### 测试场景

#### 1a. `gmp predict` 单站 1 天预测

```python
@pytest.mark.e2e
def test_predict_single_day_real_api():
    """使用真实 API 预测牛背山 1 天"""
    runner = CliRunner()
    result = runner.invoke(cli, ["predict", "niubei_gongga", "--days", "1", "--output", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)

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
        assert 0 <= event["total_score"] <= 100
        assert event["status"] in ["Perfect", "Recommended", "Possible", "Not Recommended"]
        assert event["confidence"] in ["High", "Medium", "Low"]
```

#### 1b. `gmp predict` 7 天预测

```python
@pytest.mark.e2e
def test_predict_seven_days_real_api():
    """使用真实 API 预测牛背山 7 天"""
    runner = CliRunner()
    result = runner.invoke(cli, ["predict", "niubei_gongga", "--days", "7", "--output", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["daily"]) == 7

    # 每天都有日期、摘要和事件列表
    for day in data["daily"]:
        assert "date" in day
        assert "summary" in day
        assert isinstance(day["events"], list)
```

#### 1c. 事件过滤

```python
@pytest.mark.e2e
def test_predict_events_filter_real_api():
    """事件过滤仅返回指定事件"""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "predict", "niubei_gongga", "--days", "1",
        "--events", "cloud_sea,frost", "--output", "json"
    ])

    assert result.exit_code == 0
    data = json.loads(result.output)

    # 仅包含 cloud_sea 和 frost 事件 (可能为空列表, 取决于天气触发)
    allowed_events = {"cloud_sea", "frost"}
    for day in data["daily"]:
        for event in day["events"]:
            assert event["event_type"] in allowed_events
```

---

## Task 2: 缓存验证

#### 2a. 二次调用命中缓存

```python
@pytest.mark.e2e
def test_cache_hit_on_second_call(tmp_path):
    """第二次调用应命中缓存，不重复调用 API"""
    import time

    config_path = setup_test_config(tmp_path)  # 使用临时 DB

    # 第一次调用 (真实 API)
    t1_start = time.time()
    result1 = invoke_predict(config_path, days=1)
    t1_duration = time.time() - t1_start

    # 第二次调用 (应命中缓存)
    t2_start = time.time()
    result2 = invoke_predict(config_path, days=1)
    t2_duration = time.time() - t2_start

    # 缓存命中后应显著更快
    assert t2_duration < t1_duration * 0.5

    # 两次输出的评分应一致 (相同数据 → 相同评分)
    assert result1 == result2
```

---

## Task 3: 线路预测验证

```python
@pytest.mark.e2e
def test_predict_route_real_api():
    """线路预测: 至少需要 2 个观景台配置"""
    runner = CliRunner()
    result = runner.invoke(cli, ["predict-route", "lixiao", "--days", "1", "--output", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert "route_id" in data
    assert "stops" in data
    assert len(data["stops"]) >= 1

    # 每站格式正确
    for stop in data["stops"]:
        assert "viewpoint_id" in stop
        assert "order" in stop
        assert "forecast" in stop
```

---

## Task 4: 批量生成验证

```python
@pytest.mark.e2e
def test_generate_all_real_api(tmp_path):
    """批量生成并验证文件系统输出"""
    output_dir = tmp_path / "public" / "data"
    archive_dir = tmp_path / "archive"

    runner = CliRunner()
    result = runner.invoke(cli, [
        "generate-all", "--days", "1",
        "--output", str(output_dir),
        "--archive", str(archive_dir),
    ])

    assert result.exit_code == 0

    # 验证文件系统输出
    assert (output_dir / "index.json").exists()
    assert (output_dir / "meta.json").exists()

    # 至少一个 viewpoint 有 forecast.json
    viewpoint_dirs = list((output_dir / "viewpoints").iterdir())
    assert len(viewpoint_dirs) >= 1

    for vp_dir in viewpoint_dirs:
        assert (vp_dir / "forecast.json").exists()
        assert (vp_dir / "timeline.json").exists()

        # 验证 JSON 可解析
        forecast = json.loads((vp_dir / "forecast.json").read_text())
        assert "viewpoint_id" in forecast

    # 验证归档
    archive_dirs = list(archive_dir.iterdir())
    assert len(archive_dirs) == 1
```

---

## Task 5: 回测验证

```python
@pytest.mark.e2e
def test_backtest_real_api():
    """回测: 使用 Archive API 获取历史天气"""
    # 选一个 30 天内的过去日期
    from datetime import date, timedelta
    past_date = (date.today() - timedelta(days=7)).isoformat()

    runner = CliRunner()
    result = runner.invoke(cli, [
        "backtest", "niubei_gongga", "--date", past_date, "--output", "json"
    ])

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["is_backtest"] == True
    assert data["target_date"] == past_date
    assert data["data_source"] in ["cache", "archive"]
    assert "events" in data
```

---

## Task 6: 错误处理验证

```python
@pytest.mark.e2e
def test_invalid_viewpoint_error():
    """不存在的观景台 → 错误退出"""
    runner = CliRunner()
    result = runner.invoke(cli, ["predict", "不存在的id"])
    assert result.exit_code == 1

@pytest.mark.e2e
def test_invalid_route_error():
    """不存在的线路 → 错误退出"""
    runner = CliRunner()
    result = runner.invoke(cli, ["predict-route", "不存在的id"])
    assert result.exit_code == 1

@pytest.mark.e2e
def test_backtest_future_date_error():
    """回测未来日期 → 错误退出"""
    from datetime import date, timedelta
    future_date = (date.today() + timedelta(days=7)).isoformat()

    runner = CliRunner()
    result = runner.invoke(cli, ["backtest", "niubei_gongga", "--date", future_date])
    assert result.exit_code != 0
```

---

## pytest 配置

在 `pyproject.toml` 中添加 E2E 标记:

```toml
[tool.pytest.ini_options]
markers = [
    "e2e: End-to-end tests with real API calls (deselect with '-m not e2e')",
]
```

---

## 验证命令

```bash
# 运行 E2E 测试 (需要网络连接)
python -m pytest tests/e2e/test_e2e_real_api.py -v -m e2e

# 排除 E2E 测试的快速运行
python -m pytest -m "not e2e" -v
```
