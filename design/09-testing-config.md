# 9. 测试策略与配置数据

## 9.1 测试金字塔

```
                 ┌──────────┐
                 │  E2E (2) │  完整7天预报生成
                 ├──────────┤
              ┌──────────────────┐
              │ Integration (8)  │  管线集成 + API + 缓存
              ├──────────────────┤
        ┌────────────────────────────┐
        │     Unit Tests (30+)       │  Plugin + 分析器 + 工具类
        └────────────────────────────┘
```

---

## 9.2 单元测试用例

### Plugin 测试 (每个 Plugin 至少4个用例)

| 测试 | 输入 | 预期输出 |
|------|------|---------|
| `test_golden_recommended` | 光路8%, 目标13%, 本地22% | score=87, Recommended |
| `test_golden_perfect` | 光路0%, 目标5%, 本地10% | score=100, Perfect |
| `test_golden_veto_light` | 光路60%, 目标5%, 本地10% | score=0 (光路一票否决) |
| `test_golden_veto_target` | 光路5%, 目标50%, 本地10% | score=0 (目标一票否决) |
| `test_golden_safety_veto` | 降水概率70% | score=0 (安全一票否决) |
| `test_stargazing_perfect` | optimal暗夜, 云量2%, 微风 | score≥95, Perfect |
| `test_stargazing_poor` | 满月整夜, 云量50% | score≤30, Not Recommended |
| `test_frost_excellent` | -3°C, 能见度3km, 1km/h, 低云45% | score≥90 |
| `test_frost_dry` | -3°C, 能见度35km, 2km/h, 低云75% | score=67 (干燥) |
| `test_cloud_sea_thick` | Gap1060m, 低云75%, 风2.8km/h | score=95 |
| `test_cloud_sea_none` | 云底>站点海拔 | check_trigger=false |

### 工具类测试

| 测试 | 场景 | 验证 |
|------|------|------|
| `test_light_path_10pts` | 方位角108.5°, 起点(29.75, 102.35) | 返回10个坐标, 间隔约10km |
| `test_bearing_gongga` | 牛背山→贡嘎 | 方位角 ≈ 245° |
| `test_opposite_direction` | bearing=245°, sunrise_azimuth=108.5° | True (适配sunrise) |
| `test_stargazing_window_optimal` | 月落白天, 残月35% | quality="optimal" |
| `test_stargazing_window_poor` | 满月整夜 | quality="poor" |
| `test_coord_rounding` | (29.755, 102.349) | (29.76, 102.35) |

### Plugin 扩展性测试

| 测试 | 场景 | 验证 |
|------|------|------|
| `test_register_new_plugin` | 注册自定义 Plugin | ScoreEngine 可调用 |
| `test_plugin_data_isolation` | 两个 Plugin 共享 DataContext | 互不影响评分结果 |
| `test_events_filter` | 请求仅 cloud_sea | 只返回云海评分，不触发 L2 |
| `test_season_filter` | 1月请求含 season=[10,11] 的 Plugin | Plugin 被跳过 |
| `test_requirement_aggregation` | 4个 Plugin 聚合 | 正确合并 needs_l2/needs_astro |

---

## 9.3 集成测试

```python
class TestPipelineIntegration:
    
    def test_full_pipeline_clear_day(self, mock_fetcher_clear):
        """晴天完整管线: L1→L2→Plugin评分"""
        scheduler = GMPScheduler(
            config=test_config,
            fetcher=mock_fetcher_clear
        )
        result = scheduler.run("niubei_gongga", days=1)
        
        assert len(result.forecast_days) == 1
        day = result.forecast_days[0]
        assert len(day.events) >= 2
        golden = next(e for e in day.events if e.type == "sunrise_golden_mountain")
        assert golden.score == 87
        assert golden.status == "Recommended"
    
    def test_full_pipeline_rainy_day(self, mock_fetcher_rain):
        """雨天管线: L1 拦截, 无远程调用"""
        scheduler = GMPScheduler(
            config=test_config,
            fetcher=mock_fetcher_rain
        )
        result = scheduler.run("niubei_gongga", days=1)
        
        day = result.forecast_days[0]
        assert day.events == []
        assert "不推荐" in day.summary
        assert mock_fetcher_rain.remote_call_count == 0
    
    def test_events_filter_skips_l2(self, mock_fetcher_clear):
        """events过滤: 仅请求L1景观时不触发L2"""
        scheduler = GMPScheduler(config=test_config, fetcher=mock_fetcher_clear)
        result = scheduler.run("niubei_gongga", days=1, events=["cloud_sea", "frost"])
        
        # 只有 L1 景观，不应有远程 API 调用
        assert mock_fetcher_clear.remote_call_count == 0
        event_types = [e.type for e in result.forecast_days[0].events]
        assert "sunrise_golden_mountain" not in event_types
```

---

## 9.4 Mock 数据策略

```python
class MockMeteoFetcher(BaseFetcher):
    def __init__(self, scenario: str = "clear"):
        self.scenario = scenario
        self.call_log = []
        self.remote_call_count = 0
    
    def fetch_hourly(self, lat, lon, days=7):
        self.call_log.append((lat, lon, days))
        
        if self.scenario == "clear":
            return self._generate_clear_weather(days)
        elif self.scenario == "rain":
            return self._generate_rainy_weather(days)
        elif self.scenario == "timeout":
            raise APITimeoutError("open-meteo", 15)
        elif self.scenario == "frost":
            return self._generate_frost_weather(days)
```

---

## 9.5 引擎配置 (`engine_config.yaml`)

```yaml
# 缓存配置
cache:
  memory_ttl_seconds: 300
  db_ttl_seconds: 3600
  db_path: "db/gmp_cache.db"

# 坐标精度
coord_precision: 2

# 安全阈值
thresholds:
  precip_probability: 50
  visibility_min: 1000
  local_cloud_max: 30
  target_cloud_max: 30
  light_path_cloud_max: 50
  wind_speed_max: 20
  frost_temperature: 2.0

# 光路计算
light_path:
  count: 10
  interval_km: 10

# 评分权重 (各 Plugin 独立配置)
scoring:
  golden_mountain:
    light_path: 35
    target_visible: 40
    local_clear: 25
    veto_threshold: 0        # 任一维度 ≤ 此值则一票否决
  
  cloud_sea:
    gap: 50
    density: 30
    wind: 20
  
  frost:
    temperature: 40
    moisture: 30
    wind: 20
    cloud: 10
  
  stargazing:
    base_optimal: 100
    base_good: 90
    base_partial: 70
    cloud_penalty_factor: 0.8

# 置信度映射
confidence:
  high: [1, 2]
  medium: [3, 4]
  low: [5, 6, 7]

# 摘要生成
summary:
  mode: "rule"

# 分页
pagination:
  default_page_size: 20
  max_page_size: 100

# 并发限制
concurrency:
  api_max_concurrent: 5
  batch_max_concurrent: 3
  api_daily_limit: 10000
```

---

## 9.6 观景台配置示例 (`viewpoints/niubei_gongga.yaml`)

```yaml
id: niubei_gongga
name: 牛背山
location:
  lat: 29.75
  lon: 102.35
  altitude: 3660

# 该观景台支持的景观类型 (对应注册的 Plugin event_type)
# 新增景观只需在此添加，无需改动代码
capabilities:
  - sunrise
  - sunset
  - stargazing
  - cloud_sea
  - frost

targets:
  - name: 贡嘎主峰
    lat: 29.58
    lon: 101.88
    altitude: 7556
    weight: primary
    applicable_events: null      # null = 自动根据方位角匹配

  - name: 雅拉神山
    lat: 30.15
    lon: 101.75
    altitude: 5820
    weight: secondary
    applicable_events:
      - sunset                   # 手动指定: 仅看日落金山
```

---

## 附录

### A. 外部依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| `FastAPI` | Web 框架 | ≥0.104 |
| `uvicorn` | ASGI 服务器 | ≥0.24 |
| `pandas` | 数据处理 | ≥2.0 |
| `ephem` / `skyfield` | 天文计算 | 最新 |
| `httpx` | 异步 HTTP 客户端 | ≥0.25 |
| `structlog` | 结构化日志 | ≥23.0 |
| `pydantic` | 数据校验 | ≥2.0 |

### B. 参考链接

- [Open-Meteo API 文档](https://open-meteo.com/en/docs)
- [Ephem 天文计算库](https://rhodesmill.org/pyephem/)
- [Skyfield 天文库](https://rhodesmill.org/skyfield/)
