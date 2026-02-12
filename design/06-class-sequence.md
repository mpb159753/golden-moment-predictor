# 6. 类图与时序图

## 6.1 核心类结构

```mermaid
classDiagram
    class GMPScheduler {
        -config: ViewpointConfig
        -route_config: RouteConfig
        -fetcher: MeteoFetcher
        -astro: AstroUtils
        -analyzer: AnalyzerPipeline
        -score_engine: ScoreEngine
        +run(viewpoint_id: str, days: int, events: list) ForecastReport
        +run_route(route: Route, days: int, events: list) RouteForecastReport
        +run_batch(viewpoint_ids: list) list~ForecastReport~
        -_collect_active_plugins(viewpoint, events, date) list~ScorerPlugin~
        -_build_data_context(viewpoint, date, requirement) DataContext
    }

    class ViewpointConfig {
        -viewpoints: dict
        +load(path: str) void
        +get(id: str) Viewpoint
        +list_all(page: int, page_size: int) PaginatedResult
    }

    class RouteConfig {
        -routes: dict
        +load(path: str) void
        +get(id: str) Route
        +list_all(page: int, page_size: int) PaginatedResult
    }

    class Route {
        +id: str
        +name: str
        +description: str
        +stops: list~RouteStop~
    }

    class RouteStop {
        +viewpoint_id: str
        +order: int
        +stay_note: str
    }

    class Viewpoint {
        +id: str
        +name: str
        +location: Location
        +capabilities: list~str~
        +targets: list~Target~
    }

    class Location {
        +lat: float
        +lon: float
        +altitude: int
    }

    class Target {
        +name: str
        +lat: float
        +lon: float
        +altitude: int
        +weight: str
        +applicable_events: Optional~list~
    }

    GMPScheduler --> ViewpointConfig
    GMPScheduler --> RouteConfig
    GMPScheduler --> ScoreEngine
    ViewpointConfig --> Viewpoint
    RouteConfig --> Route
    Route --> RouteStop
    RouteStop ..> Viewpoint : viewpoint_id
    Viewpoint --> Location
    Viewpoint --> Target
```

---

## 6.2 数据获取层 (含缓存层)

```mermaid
classDiagram
    class BaseFetcher {
        <<abstract>>
        +fetch_hourly(lat, lon, days)* DataFrame
    }

    class MeteoFetcher {
        -cache: WeatherCache
        -api_url: str
        +fetch_hourly(lat, lon, days) DataFrame
        +fetch_multi_points(coords: list, days) dict
        -_parse_response(response) DataFrame
    }

    class WeatherCache {
        -memory_cache: MemoryCache
        -db: CacheRepository
        -ttl_memory: int
        -ttl_db: int
        +get(lat, lon, date, hours) Optional~DataFrame~
        +set(lat, lon, date, data: DataFrame) void
        +get_or_fetch(lat, lon, date, fetcher) DataFrame
    }

    class MemoryCache {
        -storage: dict
        -ttl: int
        +get(key: str) Optional~DataFrame~
        +set(key: str, data: DataFrame) void
        +invalidate(key: str) void
    }

    class CacheRepository {
        -db_path: str
        -conn: sqlite3.Connection
        +query(lat, lon, date, hours) Optional~list~
        +upsert(lat, lon, date, hour, data: dict) void
        +get_history(viewpoint_id, date_range) list
        +save_prediction(prediction: PredictionRecord) void
    }

    class AstroUtils {
        +get_sun_events(lat, lon, date) SunEvents
        +get_moon_status(lat, lon, dt) MoonStatus
        +determine_stargazing_window(sun_events, moon_status) StargazingWindow
    }

    class GeoUtils {
        +calculate_destination(lat, lon, distance, bearing) tuple
        +calculate_bearing(p1, p2) float
        +calculate_distance(p1, p2) float
        +round_coords(lat, lon, precision) tuple
        +is_opposite_direction(bearing_to_target, sun_azimuth) bool
        +calculate_light_path_points(lat, lon, azimuth, count, interval_km) list~tuple~
    }

    class SunEvents {
        +sunrise: datetime
        +sunset: datetime
        +sunrise_azimuth: float
        +sunset_azimuth: float
        +astronomical_dawn: datetime
        +astronomical_dusk: datetime
    }

    class MoonStatus {
        +phase: int
        +elevation: float
        +moonrise: Optional~datetime~
        +moonset: Optional~datetime~
    }

    BaseFetcher <|-- MeteoFetcher
    MeteoFetcher --> WeatherCache
    WeatherCache --> MemoryCache
    WeatherCache --> CacheRepository
    AstroUtils --> GeoUtils
    AstroUtils --> SunEvents
    AstroUtils --> MoonStatus
```

---

## 6.3 分析层 (Plugin 架构)

```mermaid
classDiagram
    class DataRequirement {
        +needs_l2_target: bool
        +needs_l2_light_path: bool
        +needs_astro: bool
        +season_months: Optional~list~int~~
    }

    class DataContext {
        +date: date
        +viewpoint: Viewpoint
        +local_weather: DataFrame
        +sun_events: Optional~SunEvents~
        +moon_status: Optional~MoonStatus~
        +stargazing_window: Optional~StargazingWindow~
        +target_weather: Optional~dict~
        +light_path_weather: Optional~list~
        +l2_result: Optional~AnalysisResult~
    }

    class ScorerPlugin {
        <<interface>>
        +event_type: str
        +display_name: str
        +data_requirement: DataRequirement
        +check_trigger(l1_data: dict) bool
        +score(context: DataContext) ScoreResult
        +dimensions() list~str~
    }

    class ScoreEngine {
        -plugins: dict~str, ScorerPlugin~
        +register(plugin: ScorerPlugin) void
        +all_plugins() list~ScorerPlugin~
        +get(event_type: str) ScorerPlugin
        +collect_requirements(plugins: list) DataRequirement
    }

    class GoldenMountainPlugin {
        +event_type = "sunrise_golden_mountain"
        +data_requirement: needs_l2 + needs_astro
        +check_trigger(l1_data) bool
        +score(context) ScoreResult
    }

    class StargazingPlugin {
        +event_type = "stargazing"
        +data_requirement: needs_astro
        +check_trigger(l1_data) bool
        +score(context) ScoreResult
    }

    class CloudSeaPlugin {
        +event_type = "cloud_sea"
        +data_requirement: L1 only
        +check_trigger(l1_data) bool
        +score(context) ScoreResult
    }

    class FrostPlugin {
        +event_type = "frost"
        +data_requirement: L1 only
        +check_trigger(l1_data) bool
        +score(context) ScoreResult
    }

    class SnowTreePlugin {
        +event_type = "snow_tree"
        +data_requirement: L1 only
        +check_trigger(l1_data) bool
        +score(context) ScoreResult
    }

    class IceIciclePlugin {
        +event_type = "ice_icicle"
        +data_requirement: L1 only
        +check_trigger(l1_data) bool
        +score(context) ScoreResult
    }

    class BaseAnalyzer {
        <<abstract>>
        +analyze(data: DataFrame, context)* AnalysisResult
    }

    class LocalAnalyzer {
        +analyze(data, context) AnalysisResult
        -_check_safety(row) bool
        -_check_cloud_sea(row, altitude) CloudSeaStatus
        -_check_frost(row, altitude) FrostStatus
        -_check_snow_tree(row) SnowTreeStatus
        -_check_ice_icicle(row) IceIcicleStatus
    }

    class RemoteAnalyzer {
        +analyze(data, context) AnalysisResult
        -_check_target_visibility(target_data) bool
        -_check_light_path(light_points_data) LightPathResult
    }

    class AnalysisResult {
        +passed: bool
        +reason: str
        +score: int
        +details: dict
    }

    class ScoreResult {
        +total_score: int
        +status: str
        +breakdown: dict
    }

    ScorerPlugin --> DataRequirement
    ScorerPlugin --> DataContext
    ScoreEngine --> ScorerPlugin
    ScorerPlugin <|.. GoldenMountainPlugin
    ScorerPlugin <|.. StargazingPlugin
    ScorerPlugin <|.. CloudSeaPlugin
    ScorerPlugin <|.. FrostPlugin
    ScorerPlugin <|.. SnowTreePlugin
    ScorerPlugin <|.. IceIciclePlugin
    BaseAnalyzer <|-- LocalAnalyzer
    BaseAnalyzer <|-- RemoteAnalyzer
    LocalAnalyzer --> AnalysisResult
    RemoteAnalyzer --> AnalysisResult
    ScorerPlugin --> ScoreResult
```

> [!NOTE]
> **扩展新景观**: 只需实现 `ScorerPlugin` 接口并调用 `engine.register(NewPlugin())`，Scheduler 和 API 无需任何改动。

---

## 6.4 输出层

```mermaid
classDiagram
    class BaseReporter {
        <<abstract>>
        +generate(result: PipelineResult)* str
    }

    class ForecastReporter {
        -indent: int
        -summary_gen: SummaryGenerator
        +generate(result) str
        -_build_events(events) list
        -_format_conditions(conditions) dict
    }

    class TimelineReporter {
        +generate(result) str
        -_build_hourly(hours: list) list
        -_assign_tags(hour_data) list
    }

    class SummaryGenerator {
        -mode: str
        +generate(events: list) str
        -_rule_based(events) str
        -_llm_enhanced(events) str
    }

    class CLIFormatter {
        -color_enabled: bool
        +generate(result) str
        -_format_score(score) str
        -_colorize(text, level) str
    }

    BaseReporter <|-- ForecastReporter
    BaseReporter <|-- TimelineReporter
    BaseReporter <|-- CLIFormatter
    ForecastReporter --> SummaryGenerator
```

---

## 6.5 主流程时序图 — 7天预报生成 (Plugin 驱动)


```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant S as GMPScheduler
    participant VC as ViewpointConfig
    participant SE as ScoreEngine
    participant MF as MeteoFetcher
    participant AU as AstroUtils
    participant LA as LocalAnalyzer
    participant RA as RemoteAnalyzer
    participant P as ScorerPlugin

    C->>S: run("niubei_gongga", days=7, events=None)
    S->>VC: get("niubei_gongga")
    VC-->>S: Viewpoint(牛背山, capabilities=[...])

    Note over S,SE: 🔵 收集活跃 Plugin + 聚合需求
    S->>SE: all_plugins() → 按 capabilities/season/events 过滤
    SE-->>S: active_plugins = [Golden, Star, CloudSea, Frost, SnowTree, IceIcicle]
    S->>SE: collect_requirements(active_plugins)
    SE-->>S: DataRequirement(l2_target=T, l2_light=T, astro=T)

    Note over S,MF: 🟢 Phase 1: 获取本地天气 (一次性7天)
    S->>MF: fetch_hourly(local_coords, days=7)
    MF-->>S: local_weather_7days

    loop 对于每一天 (Day 1-7)
        Note over S,AU: 📐 天文计算 (因 needs_astro=True)
        S->>AU: get_sun_events + get_moon_status
        AU-->>S: SunEvents, MoonStatus

        Note over S,LA: 🟡 L1 本地滤网
        S->>LA: analyze(local_weather[day], context)
        LA-->>S: L1Result(passed, details)

        alt L1 通过 ✅
            Note over S,P: 🔍 Plugin 触发检查
            loop 对每个 active_plugin
                S->>P: check_trigger(l1_details)
                P-->>S: true/false
            end

            Note over S,MF: 🟢 Phase 2: 按需获取远程天气
            opt 有触发的 Plugin 需要 L2
                S->>MF: fetch_multi_points(targets + light_path)
                MF-->>S: target_weather, light_path_weather
                S->>RA: analyze(target_weather, light_path_weather)
                RA-->>S: L2Result
            end

            Note over S,P: 🟠 构建 DataContext + Plugin 循环评分
            S->>S: build DataContext(共享数据池)
            loop 对每个触发的 Plugin
                S->>P: score(DataContext)
                P-->>S: ScoreResult
            end
        else L1 未通过 ❌
            Note over S: 跳过，标记不推荐
        end
    end

    S-->>C: ForecastReport
```

---

## 6.6 缓存与降级流程

```mermaid
sequenceDiagram
    autonumber
    participant S as Scheduler
    participant MF as MeteoFetcher
    participant C as DataCache
    participant API as Open-Meteo API

    S->>MF: fetch_hourly(lat, lon, days)
    
    MF->>C: get(cache_key)
    
    alt 缓存命中且有效
        C-->>MF: cached_data
        MF-->>S: DataFrame (from cache)
    else 缓存未命中或过期
        MF->>API: GET /forecast?lat=...&lon=...
        
        alt API 正常响应
            API-->>MF: weather_data
            MF->>C: set(cache_key, weather_data)
            MF-->>S: DataFrame (fresh)
        else API 超时或错误
            MF->>C: get(cache_key, ignore_ttl=true)
            alt 有过期缓存
                C-->>MF: stale_data
                Note over MF: 标记 confidence="Degraded"
                MF-->>S: DataFrame (stale) + Warning
            else 无任何缓存
                MF-->>S: Error(APIUnavailable)
            end
        end
    end
```

---

## 6.7 云海评分流程

```mermaid
sequenceDiagram
    autonumber
    participant S as Scheduler
    participant P as CloudSeaPlugin
    participant LA as LocalAnalyzer

    S->>LA: analyze(weather_data, context)
    LA->>LA: _check_safety(precip, visibility)
    alt 安全检查失败
        LA-->>S: Result(passed=false)
    end

    LA->>LA: _check_cloud_sea(cloud_base, site_altitude)
    alt 云底高度 < 站点海拔
        LA-->>S: Result(cloud_sea=true, gap=1060m)
    else 云底高度 >= 站点海拔
        LA-->>S: Result(cloud_sea=false)
        Note over S: 跳过云海 Plugin
    end

    S->>P: check_trigger(l1_details) → true
    S->>P: score(DataContext)
    Note over P: 评分: gap(50) + density(30) + mid_struct(中云修正) + wind(20)
    P-->>S: ScoreResult(score=95, Perfect)
```

---

## 6.8 雾凇评分流程

```mermaid
sequenceDiagram
    autonumber
    participant S as Scheduler
    participant P as FrostPlugin
    participant LA as LocalAnalyzer

    S->>LA: analyze(weather_data, context)
    LA->>LA: _check_frost(temperature, visibility, wind)
    alt 温度 < 2°C
        LA-->>S: Result(frost=true, quality="marginal")
    else 温度 >= 2°C
        LA-->>S: Result(frost=false)
        Note over S: 跳过雾凇 Plugin
    end

    S->>P: check_trigger(l1_details) → true
    S->>P: score(DataContext)
    Note over P: 评分: temp(40) + moisture(30) + wind(20) + cloud(10)
    P-->>S: ScoreResult(score=67, Possible)
```

---

## 6.9 树挂积雪评分流程 (留存场景)

```mermaid
sequenceDiagram
    autonumber
    participant S as Scheduler
    participant P as SnowTreePlugin
    participant LA as LocalAnalyzer

    S->>LA: analyze(weather_data, context)
    LA->>LA: _check_snow_tree(snowfall, past_history)
    alt 降雪(12h) > 0.2cm OR (积雪 > 1.5cm + 持续低温)
        LA-->>S: Result(snow_tree=true, snow_cm=2.5, since=18h)
    else 无近期降雪
        LA-->>S: Result(snow_tree=false)
    end

    S->>P: check_trigger(l1_details) → true
    S->>P: score(DataContext)
    
    Note right of P: 复杂评分逻辑
    P->>P: calc_snow_signal(snow=2.5cm) -> 60
    P->>P: calc_clear(sun=True) -> 20
    P->>P: check_history(max_wind=15km/h) -> 0 deduc
    P->>P: check_sun_destruction(accum_sun=8h) -> -30 deduc
    
    Note over P: 评分: 60 + 20 + 20 - 12(Age) - 12(Temp) - 30(Sun)
    P-->>S: ScoreResult(score=46, Not Recommended)
```

---

## 6.10 线路预测时序图 — Route Forecast

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant S as GMPScheduler
    participant RC as RouteConfig
    participant VC as ViewpointConfig

    C->>S: run_route(route_id="lixiao", days=3)
    S->>RC: get("lixiao")
    RC-->>S: Route(理小路, stops=[stop1, stop2, stop3])

    loop 对每个停靠点 (order=1..3)
        S->>VC: get(stop.viewpoint_id)
        VC-->>S: Viewpoint
        Note over S: 复用 self.run(viewpoint_id, days, events)
        S->>S: run(stop.viewpoint_id, days=3)
        Note over S: 内部缓存层按坐标去重，相近点位共享天气数据
    end

    Note over S: 汇总 meta: total_api_calls, total_cache_hits
    S-->>C: RouteForecastReport(route, stops[], meta)
```

> [!NOTE]
> **缓存复用**: 线路上多个点位可能共享相同的天气数据缓存（坐标 ROUND(2) 后相同），
> 无需额外优化，现有缓存机制自然处理。
