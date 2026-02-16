# M13: Backtester 历史校准

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现历史回测模块，使用过去的气象数据验证评分模型的准确性。

**依赖模块:** M05 (CacheRepository), M06 (MeteoFetcher: `fetch_historical`), M12 (GMPScheduler: `run_with_data`)

---

## 背景

Backtester 的核心价值：
1. **复盘推测**: 用历史天气数据模拟当时的评分，验证模型是否合理
2. **参数调优**: 比较不同配置下的评分结果，优化阈值和权重
3. **一致性保证**: 回测分数和预测分数在相同天气数据下应完全一致

### 数据获取策略（核心）

> [!IMPORTANT]
> 回测数据获取遵循 **"缓存优先、API 兜底"** 策略：
>
> 1. **优先查本地 DB 缓存**: 检查 `weather_cache` 表中是否有该坐标+日期的数据
>    - 如果**有多次获取**（如分别在 D-1 和 D-5 获取过 2025-01-01 的预测），**加载最近一次获取的数据**（按 `fetched_at` DESC 取最新）
>    - 这样可以使用当时离目标日最近时获取的预测数据进行复盘
> 2. **DB 无缓存时**: 调用 Open-Meteo **Archive API** 获取真实历史天气数据
> 3. 回测结果可保存到 `prediction_history` 表 (标记 `is_backtest=1`)

### 架构要点

- 通过 `GMPScheduler.run_with_data()` 注入预获取的天气数据进行评分，确保管线一致性
- 限制最远回测天数 (`config.backtest_max_history_days`)

### 参考

- 设计文档 [06-class-sequence.md §6.2.6](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/06-class-sequence.md)
- 回测测试用例 [09-testing-config.md §9.7](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/09-testing-config.md)

---

## Task 0: GMPScheduler.run_with_data() — 数据注入接口 (M12 补充)

> 此 Task 在 `gmp/core/scheduler.py` 中实现，属于 M12 的补充。

**Files:**
- Modify: `gmp/core/scheduler.py`
- Test: `tests/unit/test_scheduler.py` (补充测试)

### 要新增的方法

```python
class GMPScheduler:
    # ... 已有 run() 和 run_route() ...

    def run_with_data(
        self,
        viewpoint_id: str,
        weather_data: dict[tuple[float, float], pd.DataFrame],
        target_date: date,
        events: list[str] | None = None,
    ) -> PipelineResult:
        """使用预提供的天气数据进行单日评分 — 供 Backtester 调用

        与 run() 的区别：
        - 不调用 fetcher 获取数据，而是从 weather_data 字典中读取
        - weather_data key 为 ROUND(2) 坐标, value 为该坐标的天气 DataFrame
        - 天文数据仍由 AstroUtils 实时计算 (天文数据与天气缓存无关)
        - 仅评分单日 (由 Backtester 控制日期)

        Steps:
        1. 获取 Viewpoint 配置
        2. 筛选活跃 Plugin
        3. 从 weather_data 中提取本地天气 / 目标天气 / 光路天气
        4. 计算天文数据 (如需)
        5. 构建 DataContext
        6. 遍历 Plugin 评分
        7. 返回 PipelineResult
        """
```

### 应测试的内容

- 传入 MockWeatherData + 牛背山坐标 → 正常评分
- weather_data 中缺少某坐标 → 跳过该数据或合理报错
- 与 `run()` 使用相同天气数据时产生相同评分

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
        cache_repo: CacheRepository,
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
        2. 获取天气数据 (缓存优先策略):
           a. 查询 DB 中该坐标+日期的缓存
           b. 如有多次获取，取最新 (fetched_at DESC)
           c. DB 无数据 → 调用 fetcher.fetch_historical() 从 Archive API 获取
        3. 调用 scheduler.run_with_data() 进行评分
        4. 构建回测报告
        5. 如果 save=True → 保存到 prediction_history (is_backtest=1)
        6. 返回报告
        """

    def _resolve_weather_data(
        self,
        viewpoint_id: str,
        target_date: date,
        required_coords: list[tuple[float, float]],
    ) -> tuple[dict[tuple[float, float], pd.DataFrame], str]:
        """解析回测所需天气数据 — 缓存优先策略

        Args:
            required_coords: 所有需要的坐标列表 (本地 + 目标 + 光路)

        Returns:
            (weather_data_dict, data_source)
            data_source: "cache" (来自 DB 缓存) 或 "archive" (来自 API)

        Logic:
        1. 对每个坐标查询 cache_repo.query_weather(lat, lon, target_date)
        2. 如有数据 → 取 fetched_at 最大的一批 (同一次获取)
        3. 如全部坐标都有缓存 → data_source="cache"
        4. 如任一坐标无缓存 → 对缺失坐标调用 fetcher.fetch_historical()
           → data_source="archive" (混合来源也标记为 archive)
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
    "data_source": "cache" | "archive",  # 标识数据来源
    "data_fetched_at": "2025-11-30T10:00:00",  # 如来自缓存，记录原始获取时间
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

**缓存优先策略:**
- DB 中有目标日的缓存 → 使用缓存数据, data_source="cache"
- DB 中有多次获取 (D-1 和 D-5) → 使用 D-1 (最近一次) 的数据
- DB 中无缓存 → 调用 `fetch_historical`, data_source="archive"
- 部分坐标有缓存,部分无 → 缺失部分调 API, data_source="archive"

**评分一致性:**
- 用 MockWeatherData 注入相同天气数据
- `scheduler.run_with_data()` 和正常流程 `scheduler.run()` 产生相同评分

**保存:**
- save=True → `cache_repo.save_prediction` 被调用
- 保存记录中 `is_backtest=True`, `data_source` 正确
- save=False → `save_prediction` 未被调用

**报告格式:**
- `data_source` 字段正确反映实际来源
- `data_fetched_at` 在缓存来源时有值
- events 格式与 forecast 一致

---

## 验证命令

```bash
python -m pytest tests/backtest/test_backtester.py -v
```

