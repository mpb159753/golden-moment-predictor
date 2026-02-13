# M12: 调度器 GMPScheduler

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现主调度器 `GMPScheduler`，串联 Plugin 收集→数据获取→评分 的核心管线。Scheduler 聚焦于单站/线路评分，批量生成由 [M12B BatchGenerator](./M12B-batch-generator.md) 负责。

**依赖模块:** M04 (AstroUtils), M06 (MeteoFetcher), M07 (ConfigManager), M08 (ScoreEngine)

---

## 背景

`GMPScheduler` 是 GMP 系统的核心评分编排器，职责：
1. 根据 Viewpoint 的 capabilities 从 ScoreEngine 筛选活跃 Plugin
2. 聚合所有活跃 Plugin 的 `DataRequirement`
3. 按需获取数据 (L1→L2→Astro)
4. 构建 `DataContext`
5. 逐 Plugin 评分
6. 聚合为 `PipelineResult`

> **注意**: 批量生成 (generate_all) 和文件输出职责已抽离至 [M12B BatchGenerator](./M12B-batch-generator.md)，Scheduler 不直接依赖输出层组件。

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
    ):
        """接收核心评分管线依赖组件（不含输出层）"""

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
           b. Astro (按需): 获取天文数据 — ⚠️ 必须在 L2 之前，因光路方向依赖方位角
           c. L2 (按需): 获取目标天气 + 光路天气
           d. 构建 DataContext
           e. 遍历活跃 Plugin → score(context)
           f. 收集 ScoreResult 列表
           g. 生成 summary
        5. 构建 meta (cache_stats, timestamp)
        6. 返回 PipelineResult
        """
```

### 数据获取详细逻辑 (步骤 4a-4c)

**4a. L1 本地天气:**
```python
# 一次请求获取 days 天, 按需回看 past_hours
local_weather = fetcher.fetch_hourly(
    lat=viewpoint.location.lat,
    lon=viewpoint.location.lon,
    days=days,
    past_days=1 if aggregated_req.past_hours > 0 else 0
)
```

**4b. Astro 数据 (仅当 `needs_astro=True`) — ⚠️ 必须在 L2 之前执行:**
```python
# 先计算天文数据，因为 L2 光路方向依赖日出/日落方位角
sun_events = astro.get_sun_events(lat, lon, target_date)
moon_status = astro.get_moon_status(lat, lon, sunset_dt)
stargazing_window = astro.determine_stargazing_window(sun_events, moon_status)
```

**4c-1. L2 目标天气 (仅当 `needs_l2_target=True`):**
```python
# 获取所有 Target 坐标的天气
target_coords = [(t.lat, t.lon) for t in viewpoint.targets]
target_weather = fetcher.fetch_multi_points(target_coords, days=days)
```

**4c-2. L2 光路天气 (仅当 `needs_l2_light_path=True`):**
```python
# 根据活跃 Plugin 判断需要哪个方向的光路 — 此处依赖 4b 的 sun_events
azimuths_to_fetch = []
if any(p.event_type == "sunrise_golden_mountain" for p in active_plugins):
    azimuths_to_fetch.append(sun_events.sunrise_azimuth)
if any(p.event_type == "sunset_golden_mountain" for p in active_plugins):
    azimuths_to_fetch.append(sun_events.sunset_azimuth)

for azimuth in azimuths_to_fetch:
    path_points = geo.calculate_light_path_points(
        viewpoint.location.lat, viewpoint.location.lon,
        azimuth,
        count=config.light_path_count,
        interval_km=config.light_path_interval_km
    )
    path_weather_data = fetcher.fetch_multi_points(path_points, days=days)
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
- 仅 sunrise Plugin 活跃 → 只获取 sunrise 方向光路，不获取 sunset 方向
- 仅 sunset Plugin 活跃 → 只获取 sunset 方向光路
- 两者都活跃 → 获取两个方向

**多天循环容错:**
- 7 天预测中第 3 天数据获取失败 → 其他 6 天正常, 第 3 天标记 degraded 或跳过
- 单天 Plugin 评分异常 → 记录 warning, 该 Plugin 在该天返回 None, 其他 Plugin 不受影响

---

## Task 2: `run_route()` 线路预测

### 要实现的方法

```python
def run_route(
    self,
    route_id: str,
    days: int = 7,
    events: list[str] | None = None,
) -> list[PipelineResult]:
    """线路多站预测
    1. 获取 Route 配置
    2. 逐站调用 self.run(stop.viewpoint_id, days, events)
    3. 返回每站的 PipelineResult 列表
    注意: 线路级别 JSON 聚合由 ForecastReporter.generate_route() 负责
    """
```

### 应测试的内容

- 线路有 2 个站 → 调用 run() 2 次
- 单站失败 → 跳过, 继续其余站, 记录 warning
- 线路不存在 → RouteNotFoundError

---

## Task 3: `run_with_data()` 数据注入接口

> 详细定义见 [M13 Task 0](file:///Users/mpb/WorkSpace/golden-moment-predictor/implementation_plan/M13-backtester.md)，在本模块的 `scheduler.py` 中实现。

此方法接受预获取的天气数据字典，不调用 Fetcher，供 Backtester 调用。确保评分管线与 `run()` 复用相同逻辑。

---

## Task 4: 集成测试 (`tests/integration/test_pipeline.py`)

**Files:**
- Create: `tests/integration/test_pipeline.py`

### 测试策略

> **重要**: 集成测试中只允许 Mock **外部 API 返回结果** (Open-Meteo HTTP 响应)，其他所有组件 (包括 SQLite 缓存、配置加载、评分引擎等) 均使用真实实现。

### 要测试的场景

**端到端管线测试 (晋天 fixture):**
- Mock Open-Meteo HTTP 响应为晴天数据
- 真实初始化 ConfigManager、ScoreEngine、所有 Plugin
- 调用 `scheduler.run("niubei_gongga", days=1)` → 验证 PipelineResult 包含预期事件

**多 Plugin 协同评分:**
- 晴天低温场景: 应同时触发 golden_mountain 和 frost 等多个 Plugin
- 验证各 Plugin 独立评分、互不干扰

**缓存集成:**
- 第一次调用: Mock API 被调用、数据写入 SQLite
- 第二次调用: Mock API **不**被调用、从 SQLite 读取缓存

**降级场景:**
- Mock API 返回超时、SQLite 中有 stale 缓存 → 标记 degraded、仍返回结果
- Mock API 返回超时、无缓存 → 抛 `ServiceUnavailableError`

**线路测试:**
- 真实初始化 2 个观景台配置 + 1 条线路
- 调用 `scheduler.run_route("lixiao", days=1)` → 验证各站点结果

---

## 验证命令

```bash
python -m pytest tests/unit/test_scheduler.py -v
python -m pytest tests/integration/test_pipeline.py -v
```
