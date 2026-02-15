# M12: 调度器 GMPScheduler

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现主调度器 `GMPScheduler`，串联 Plugin 收集→数据获取→评分→输出 的完整管线。

**依赖模块:** M04 (AstroUtils), M06 (MeteoFetcher), M07 (ConfigManager), M08 (ScoreEngine), M11 (Reporters)

---

## 背景

`GMPScheduler` 是 GMP 系统的核心编排器，职责：
1. 根据 Viewpoint 的 capabilities 从 ScoreEngine 筛选活跃 Plugin
2. 聚合所有活跃 Plugin 的 `DataRequirement`
3. 按需获取数据 (L1→L2→Astro)
4. 构建 `DataContext`
5. 逐 Plugin 评分
6. 聚合为 `PipelineResult`

### 关键参考

- 时序图: [06-class-sequence.md §6.2.1](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/06-class-sequence.md)
- 数据流示例: [04-data-flow-example.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/04-data-flow-example.md)
- 降级策略: [08-operations.md §8.2](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/08-operations.md)

---

## Task 1: GMPScheduler 核心 — `run()` 单站预测

**Files:**
- Create: `gmp/core/scheduler.py`
- Test: `tests/unit/test_scheduler.py`

### 要实现的类

```python
class GMPScheduler:
    def __init__(
        self,
        config: ConfigManager,
        viewpoint_config: ViewpointConfig,
        route_config: RouteConfig,
        fetcher: MeteoFetcher,
        score_engine: ScoreEngine,
        astro: AstroUtils,
        geo: GeoUtils,
        forecast_reporter: ForecastReporter,
        timeline_reporter: TimelineReporter,
        json_writer: JSONFileWriter,
    ):
        """接收所有依赖组件"""

    def run(
        self,
        viewpoint_id: str,
        days: int = 7,
        events: list[str] | None = None,
    ) -> PipelineResult:
        """单站点多日预测 — 核心主流程

        Steps:
        1. 获取 Viewpoint 配置 (ViewpointConfig.get)
        2. 筛选活跃 Plugin (ScoreEngine.filter_active_plugins)
        3. 聚合数据需求 (ScoreEngine.collect_requirements)
        4. for day in days:
           a. L1: 获取本地天气 (fetcher.fetch_hourly)
           b. L2 (按需): 获取目标天气 + 光路天气
           c. Astro (按需): 获取天文数据
           d. 构建 DataContext
           e. 遍历活跃 Plugin → score(context)
           f. 收集 ScoreResult 列表
           g. 生成 summary
        5. 构建 meta (cache_stats, timestamp)
        6. 返回 PipelineResult
        """
```

### 数据获取详细逻辑 (步骤 4a-4c)

**L1 本地天气:**
```python
# 一次请求获取 days 天, 按需回看 past_hours
local_weather = fetcher.fetch_hourly(
    lat=viewpoint.location.lat,
    lon=viewpoint.location.lon,
    days=days,
    past_days=1 if aggregated_req.past_hours > 0 else 0
)
```

**L2 目标天气 (仅当 `needs_l2_target=True`):**
```python
# 获取所有 Target 坐标的天气
target_coords = [(t.lat, t.lon) for t in viewpoint.targets]
target_weather = fetcher.fetch_multi_points(target_coords, days=days)
```

**L2 光路天气 (仅当 `needs_l2_light_path=True`):**
```python
# 计算光路点 (按 sunrise/sunset 方位角)
for sun_event_azimuth in [sunrise_azimuth, sunset_azimuth]:
    path_points = geo.calculate_light_path_points(
        viewpoint.location.lat, viewpoint.location.lon,
        sun_event_azimuth,
        count=config.light_path_count,
        interval_km=config.light_path_interval_km
    )
    path_weather_data = fetcher.fetch_multi_points(path_points, days=days)
```

**Astro 数据 (仅当 `needs_astro=True`):**
```python
sun_events = astro.get_sun_events(lat, lon, target_date)
moon_status = astro.get_moon_status(lat, lon, sunset_dt)
stargazing_window = astro.determine_stargazing_window(sun_events, moon_status)
```

### 降级处理

参照 [08-operations.md §8.2](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/08-operations.md):
- API 超时 → 尝试使用 stale 缓存，标记 `data_freshness="degraded"`
- 单个 Target 获取失败 → 跳过该 Target，其他正常
- 所有 API 失败且无缓存 → 抛 `ServiceUnavailableError`

### 应测试的内容

**Happy Path:**
- 使用 MockFetcher (clear) 运行 1 天 → PipelineResult 含 events
- 运行 7 天 → forecast_days 长度 7
- 各 Plugin 正常评分

**events 过滤:**
- events=["cloud_sea", "frost"] → 不触发 L2 远程调用
- events=["sunrise_golden_mountain"] → 触发 L2

**降级测试:**
- MockFetcher 超时但有 stale 缓存 → 标记 degraded
- MockFetcher 超时且无缓存 → ServiceUnavailableError

**数据按需获取:**
- 仅 L1 Plugin 活跃 → `fetch_multi_points` 调用次数=0
- 有 GoldenMountain → `fetch_multi_points` 被调用

---

## Task 2: `run_route()` 线路预测

### 要实现的方法

```python
def run_route(
    self,
    route_id: str,
    days: int = 7,
    events: list[str] | None = None,
) -> dict:
    """线路多站预测
    1. 获取 Route 配置
    2. 逐站调用 self.run(stop.viewpoint_id, days, events)
    3. 聚合为线路级别的 forecast
    """
```

### 应测试的内容

- 线路有 2 个站 → 调用 run() 2 次
- 单站失败 → 跳过, 继续其余站, 记录 warning
- 线路不存在 → RouteNotFoundError

---

## Task 3: `generate_all()` 批量生成

### 要实现的方法

```python
def generate_all(
    self,
    days: int = 7,
    events: list[str] | None = None,
    fail_fast: bool = False,
) -> dict:
    """批量生成所有观景台+线路的预测
    1. 遍历所有 viewpoints → run()
    2. 遍历所有 routes → run_route()
    3. 生成 forecast.json/timeline.json + index.json + meta.json
    4. 归档到 archive/
    """
```

### 应测试的内容

- 2 个 viewpoint, 1 个 route → 输出完整文件集
- fail_fast=False: 单站失败跳过, meta.json 记录 failed_viewpoints
- fail_fast=True: 单站失败立即中止

---

## 验证命令

```bash
python -m pytest tests/unit/test_scheduler.py -v
python -m pytest tests/integration/test_pipeline.py -v
```
