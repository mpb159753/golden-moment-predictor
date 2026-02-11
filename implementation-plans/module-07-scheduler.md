# Module 07: 主调度引擎 GMPScheduler

## 模块背景

GMPScheduler 是整个系统的"大脑"，负责协调所有子系统完成一次完整的预测流程：从接收用户请求，到收集活跃 Plugin、聚合数据需求、分阶段获取数据、构建 DataContext、调度 L1/L2 滤网、遍历 Plugin 评分，最终输出结果。

**在系统中的位置**: 核心引擎 (`gmp/core/scheduler.py`) — 系统的中枢调度器。

**前置依赖**: Module 01-06 全部完成

## 设计依据

- [01-architecture.md](../design/01-architecture.md): §1.4 整体架构, §1.5 数据流架构
- [03-scoring-plugins.md](../design/03-scoring-plugins.md): §3.2 Scheduler 调度流程伪代码
- [04-data-flow-example.md](../design/04-data-flow-example.md): Stage 0-5 完整数据流
- [06-class-sequence.md](../design/06-class-sequence.md): §6.1 核心类, §6.5 主流程时序图, §6.6 缓存与降级流程
- [08-operations.md](../design/08-operations.md): §8.2 降级策略, §8.7 并发策略, §8.9 请求合并

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/core/scheduler.py` | GMPScheduler 主调度器 |
| `gmp/core/pipeline.py` | AnalyzerPipeline (L1→L2 管线) |
| `tests/integration/test_pipeline.py` | 管线集成测试 |

## 代码接口定义

### `gmp/core/scheduler.py`

```python
from gmp.core.models import DataContext, DataRequirement, Viewpoint
from gmp.core.config_loader import ViewpointConfig, EngineConfig
from gmp.fetcher.meteo_fetcher import MeteoFetcher
from gmp.astro.astro_utils import AstroUtils
from gmp.astro.geo_utils import GeoUtils
from gmp.analyzer.local_analyzer import LocalAnalyzer
from gmp.analyzer.remote_analyzer import RemoteAnalyzer
from gmp.scorer.engine import ScoreEngine

class GMPScheduler:
    """主调度器 — Plugin 驱动的预测引擎"""
    
    def __init__(self, config: EngineConfig, 
                 viewpoint_config: ViewpointConfig,
                 fetcher: MeteoFetcher,
                 astro: AstroUtils,
                 score_engine: ScoreEngine):
        self._config = config
        self._viewpoint_config = viewpoint_config
        self._fetcher = fetcher
        self._astro = astro
        self._geo = GeoUtils()
        self._local_analyzer = LocalAnalyzer(config)
        self._remote_analyzer = RemoteAnalyzer()
        self._score_engine = score_engine
    
    def run(self, viewpoint_id: str, days: int = 7,
            events: list[str] | None = None) -> dict:
        """执行预测
        
        流程:
        1. 加载观景台配置
        2. 收集活跃 Plugin (capabilities ∩ season ∩ events)
        3. 聚合 DataRequirement
        4. Phase 1: 获取本地天气 (7天一次性获取)
        5. 遍历每一天:
           a. 按需获取天文数据
           b. L1 本地滤网
           c. Plugin 触发检查
           d. Phase 2: 按需获取远程天气
           e. L2 远程滤网
           f. 构建 DataContext + Plugin 循环评分
        6. 汇总结果
        
        参数:
            viewpoint_id: 观景台 ID
            days: 预测天数 (1-7)
            events: 事件类型过滤列表，None=全部
        
        返回:
            {
                "viewpoint": str,
                "forecast_days": [
                    {
                        "date": str,
                        "confidence": str,
                        "events": [ScoreResult, ...],
                    }, ...
                ],
                "meta": {"api_calls": int, "cache_hits": int}
            }
        """
    
    def _collect_active_plugins(self, viewpoint: Viewpoint,
                                 events_filter: list[str] | None,
                                 target_date: date) -> list:
        """收集活跃 Plugin
        
        过滤条件:
        1. plugin.event_type 对应的 capability 在 viewpoint.capabilities 中
        2. events_filter 为 None 或包含 plugin.event_type
        3. plugin.data_requirement.season_months 为 None 或包含当月
        
        特殊映射:
        - "sunrise" capability → 匹配 "sunrise_golden_mountain" event_type
        - "sunset" capability → 匹配 "sunset_golden_mountain" event_type
        """
    
    def _build_data_context(self, viewpoint: Viewpoint, target_date: date,
                             local_weather_day: "pd.DataFrame",
                             requirement: DataRequirement) -> DataContext:
        """构建共享数据上下文
        
        根据 requirement 按需填充:
        - needs_astro → get_sun_events + get_moon_status + determine_stargazing_window
        - needs_l2_target → fetch_multi_points(targets)
        - needs_l2_light_path → calculate_light_path_points + fetch_multi_points
        """
    
    def _determine_confidence(self, days_ahead: int) -> str:
        """置信度映射: T+1~2=High, T+3~4=Medium, T+5~7=Low"""
    
    def _match_targets_by_direction(self, viewpoint: Viewpoint,
                                     sun_events: "SunEvents") -> list[dict]:
        """根据方位角自动匹配 Target 适用事件
        
        逻辑:
        1. 计算 viewpoint → target 方位角
        2. 日出: is_opposite_direction(bearing, sunrise_azimuth) → 该 target 适配 sunrise
        3. 日落: is_opposite_direction(bearing, sunset_azimuth) → 该 target 适配 sunset
        4. 如果 target.applicable_events 不为 None，使用手动指定
        """
```

### `gmp/core/pipeline.py`

```python
class AnalyzerPipeline:
    """L1 → L2 分析管线"""
    
    def __init__(self, local_analyzer: LocalAnalyzer, 
                 remote_analyzer: RemoteAnalyzer):
        self._local = local_analyzer
        self._remote = remote_analyzer
    
    def run(self, local_weather: "pd.DataFrame", context: DataContext,
            need_l2: bool = False) -> dict:
        """运行分析管线
        
        返回:
            {
                "l1": AnalysisResult,
                "l2": AnalysisResult | None,  # 仅当 need_l2=True 且 L1 通过时
            }
        """
```

## 实现要点

### 调度流程核心伪代码

```python
def run(self, viewpoint_id, days=7, events=None):
    viewpoint = self._viewpoint_config.get(viewpoint_id)
    
    # Phase 1: 一次性获取7天本地天气
    local_weather_all = self._fetcher.fetch_hourly(
        viewpoint.location.lat, viewpoint.location.lon, days=days
    )
    
    forecast_days = []
    for day_offset in range(days):
        target_date = date.today() + timedelta(days=day_offset + 1)
        
        # 当天本地天气切片
        local_weather_day = self._slice_day(local_weather_all, target_date)
        
        # 收集活跃 Plugin + 聚合需求
        active_plugins = self._collect_active_plugins(viewpoint, events, target_date)
        requirement = self._score_engine.collect_requirements(active_plugins)
        
        # 构建 DataContext (按需填充天文+远程数据)
        ctx = self._build_data_context(viewpoint, target_date, local_weather_day, requirement)
        
        # L1 滤网
        l1_result = self._local_analyzer.analyze(local_weather_day, {
            "site_altitude": viewpoint.location.altitude,
            "viewpoint": viewpoint,
        })
        
        if not l1_result.passed:
            forecast_days.append({"date": str(target_date), "confidence": ..., "events": []})
            continue
        
        # Plugin 触发检查
        triggered = [p for p in active_plugins if p.check_trigger(l1_result.details)]
        
        # Phase 2: 按需获取远程数据
        triggered_need_l2 = any(
            p.data_requirement.needs_l2_target or p.data_requirement.needs_l2_light_path
            for p in triggered
        )
        if triggered_need_l2:
            # 获取目标天气 + 光路天气 + L2 分析
            ...
        
        # Plugin 循环评分
        results = [p.score(ctx) for p in triggered]
        
        forecast_days.append({
            "date": str(target_date),
            "confidence": self._determine_confidence(day_offset + 1),
            "events": results,
        })
    
    return {"viewpoint": viewpoint.name, "forecast_days": forecast_days, "meta": {...}}
```

### 请求合并优化

光路 10 个检查点的天气数据，在坐标 ROUND(2) 后可能有重复，应去重后批量请求。

### 错误处理

- MeteoFetcher 超时 → 使用降级策略（Module 03 的 `DegradationPolicy`）
- 某个 Plugin 评分异常 → 记录错误，跳过该 Plugin，其他 Plugin 正常评分

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
python -m pytest tests/integration/test_pipeline.py -v
```

### 具体测试用例

| 测试函数 | 验证内容 |
|---------|---------|
| `test_full_pipeline_clear_day` | 晴天完整管线: L1→L2→Plugin评分，golden=87 |
| `test_full_pipeline_rainy_day` | 雨天: L1 拦截, events=[], remote_call_count=0 |
| `test_events_filter_skips_l2` | 仅请求 cloud_sea+frost 时不触发 L2 远程调用 |
| `test_confidence_mapping` | T+1=High, T+3=Medium, T+5=Low |
| `test_target_direction_matching` | 贡嘎245°+日出108.5° → sunrise 匹配 |
| `test_7day_forecast_structure` | 7天预测结构完整 |
| `test_season_filter` | 非当季 Plugin 被正确跳过 |
| `test_plugin_error_isolation` | 单个 Plugin 异常不影响其他 |
| `test_requirement_aggregation` | 多 Plugin 需求聚合正确 |

## 验收标准

- [ ] 完整 7 天预测流程可执行
- [ ] Plugin 收集逻辑正确（capabilities + season + events 三重过滤）
- [ ] DataContext 按需填充正确
- [ ] L1 一票否决后不触发远程调用
- [ ] events 过滤正确（仅 L1 Plugin 时不请求 L2 数据）
- [ ] 方位角方向匹配逻辑正确
- [ ] 置信度映射正确
- [ ] 所有测试通过
