# M13: Backtester 历史校准

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现历史回测模块，使用过去的气象数据验证评分模型的准确性。

**依赖模块:** M06 (MeteoFetcher: `fetch_historical`), M12 (GMPScheduler: `run`)

---

## 背景

Backtester 的核心价值：
1. **模型验证**: 用过去已知结果的天气数据验证评分模型是否合理
2. **参数调优**: 比较不同配置下的评分结果，优化阈值和权重
3. **一致性保证**: 回测分数和预测分数在相同天气数据下应完全一致

### 架构要点

- 使用 Open-Meteo **Archive API** (而非 Forecast API) 获取历史数据
- 通过 `GMPScheduler.run()` 的相同管线进行评分，确保一致性
- 结果可保存到 `prediction_history` 表 (标记 `is_backtest=1`)
- 限制最远回测天数 (`config.backtest_max_history_days`)

### 参考

- 设计文档 [06-class-sequence.md §6.2.6](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/06-class-sequence.md)
- 回测测试用例 [09-testing-config.md §9.7](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/09-testing-config.md)
- Archive API 配置 [09-testing-config.md §9.5 → backtest](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/09-testing-config.md)

---

## Task 1: Backtester 实现

**Files:**
- Create: `gmp/backtest/backtester.py`
- Test: `tests/backtest/test_backtester.py`

### 要实现的类

```python
class Backtester:
    def __init__(
        self,
        scheduler: GMPScheduler,
        fetcher: MeteoFetcher,
        config: ConfigManager,
        cache_repo: CacheRepository | None = None,
    ):
        self._scheduler = scheduler
        self._fetcher = fetcher
        self._config = config
        self._cache_repo = cache_repo

    def run(
        self,
        viewpoint_id: str,
        target_date: date,
        events: list[str] | None = None,
        save: bool = False,
    ) -> dict:
        """执行单次回测

        Steps:
        1. 验证日期合法性:
           - 必须是过去的日期 (< today) → else InvalidDateError("FutureDate")
           - 不能超过 max_history_days → else InvalidDateError("DateTooOld")
        2. 使用 fetcher.fetch_historical() 获取历史天气
        3. 使用 scheduler 的评分管线 (相同 Plugin/配置) 评分
        4. 构建回测报告
        5. 如果 save=True → 保存到 prediction_history (is_backtest=1)
        6. 返回报告
        """

    def _validate_date(self, target_date: date) -> None:
        """日期合法性检查"""
```

### 回测报告格式

```python
{
    "viewpoint_id": "niubei_gongga",
    "target_date": "2025-12-01",
    "is_backtest": True,
    "data_source": "archive",
    "events": [...],  # 同 forecast 格式
    "meta": {
        "backtest_run_at": "...",
        "config_snapshot": {"scoring": {}}  # 可选: 记录评分配置快照
    }
}
```

### 应测试的内容

**日期验证:**
- 过去的有效日期 → 正常执行
- 未来日期 → `InvalidDateError("FutureDate")`
- 超过 max_history_days → `InvalidDateError("DateTooOld")`

**评分一致性:**
- 用 MockFetcher 返回相同天气数据
- 同一数据: `scheduler.run()` 和 `backtester.run()` 产生相同评分

**保存:**
- save=True → `cache_repo.save_prediction` 被调用
- 保存记录中 `is_backtest=True`, `data_source="archive"`
- save=False → `save_prediction` 未被调用

**数据源:**
- 回测使用 `fetch_historical` (非 `fetch_hourly`)
- 返回报告中 `data_source="archive"`

---

## 验证命令

```bash
python -m pytest tests/backtest/test_backtester.py -v
```
