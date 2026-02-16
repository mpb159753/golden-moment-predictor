# M06: MeteoFetcher 气象数据获取

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 Open-Meteo API 调用与数据解析，支持预报和历史数据获取，集成缓存和降级策略。

**依赖模块:** M02 (异常类), M05 (WeatherCache)

---

## 背景

MeteoFetcher 是 GMP 的核心数据获取组件，负责：
1. 调用 Open-Meteo Forecast API 获取逐时天气预报
2. 调用 Open-Meteo Archive API 获取历史天气 (回测用)
3. 支持多坐标批量请求 (光路 10 点)
4. 通过 WeatherCache 实现缓存和降级

> **HTTP 方案选择**: 使用 `httpx` 直接调用 Open-Meteo REST JSON API，而非 `openmeteo-requests` SDK。原因：GMP 单次数据量小 (7×24=168 条)，FlatBuffers 性能优势可忽略；已有完整缓存层 (M05) 和重试机制；JSON 按名称访问字段比 SDK 的按索引访问更直观安全。

### API 请求参数

**Forecast API**: `https://api.open-meteo.com/v1/forecast`
```
?latitude=29.75&longitude=102.35
&hourly=temperature_2m,cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,
       cloudbase,precipitation_probability,visibility,wind_speed_10m,
       snowfall,rain,showers,weather_code
&forecast_days=7
&past_days=1        # 可选，用于获取 D+1 的 past_hours 数据
```

**Archive API**: `https://archive-api.open-meteo.com/v1/archive`
```
?latitude=29.75&longitude=102.35
&hourly=<同上字段>
&start_date=2025-12-01&end_date=2025-12-01
```

### 数据校验规则 (设计文档 §8.10)

| 字段 | 校验 | 异常处理 |
|------|------|---------|
| `cloud_base_altitude` | 非 None 且 ≥ 0 | None → 10000 |
| `temperature_2m` | -60°C ~ 60°C | 超范围标记 degraded |
| `precipitation_probability` | 0 ~ 100 | clip |
| `visibility` | ≥ 0 | None → 0 |
| `cloud_cover` | 0 ~ 100 | clip |
| `wind_speed_10m` | ≥ 0 | None → 0 |

### 超时配置 (设计文档 §8.3)

```python
# 从 engine_config.yaml 加载
TIMEOUT_CONFIG = {
    "open_meteo_api": {"connect_timeout": 5, "read_timeout": 15, "retries": 2, "retry_delay": 1},
    "open_meteo_archive_api": {"connect_timeout": 5, "read_timeout": 30, "retries": 2, "retry_delay": 2},
}
```

---

## Task 1: MeteoFetcher 核心实现

**Files:**
- Create: `gmp/data/meteo_fetcher.py`
- Test: `tests/unit/test_meteo_fetcher.py`

### 要实现的类

```python
class MeteoFetcher:
    def __init__(self, cache: WeatherCache, config: dict | None = None):
        """
        config 示例: {
            "base_url": "https://api.open-meteo.com/v1",
            "archive_base_url": "https://archive-api.open-meteo.com/v1/archive",
            "connect_timeout": 5,
            "read_timeout": 15,
            "retries": 2,
            "retry_delay": 1,
        }
        """

    def fetch_hourly(
        self, lat: float, lon: float, days: int = 7, past_days: int = 0
    ) -> pd.DataFrame:
        """获取逐小时天气预报
        1. 先查缓存
        2. 缓存未命中或不新鲜 → 调用 API
        3. 解析响应 → DataFrame
        4. 数据校验
        5. 写入缓存
        6. 返回 DataFrame
        """

    def fetch_historical(
        self, lat: float, lon: float, target_date: date
    ) -> pd.DataFrame:
        """获取历史天气 (回测用)，使用 Archive API"""

    def fetch_multi_points(
        self, coords: list[tuple[float, float]], days: int = 7
    ) -> dict[tuple[float, float], pd.DataFrame]:
        """批量获取多坐标天气（光路点 + 目标点）
        坐标会先 ROUND(2) 去重, 减少 API 调用
        """

    def _call_api(self, url: str, params: dict) -> dict:
        """HTTP 调用 + 重试 + 超时处理"""

    def _parse_response(self, response: dict) -> pd.DataFrame:
        """解析 Open-Meteo JSON → DataFrame

        字段名映射 (Open-Meteo API → GMP 内部):
        - cloud_cover → cloud_cover_total
        - cloud_cover_mid → cloud_cover_medium
        - cloudbase → cloud_base_altitude
        其余字段名与 API 一致。
        """

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据校验: clip 异常值, None 填充默认值"""
```

### DataFrame 列结构

```python
columns = [
    "forecast_date",              # date
    "forecast_hour",              # int 0-23
    "temperature_2m",             # float °C
    "cloud_cover_total",          # int 0-100
    "cloud_cover_low",            # int 0-100
    "cloud_cover_medium",         # int 0-100
    "cloud_cover_high",           # int 0-100
    "cloud_base_altitude",        # float meters
    "precipitation_probability",  # int 0-100
    "visibility",                 # float meters
    "wind_speed_10m",             # float km/h
    "snowfall",                   # float cm/h
    "rain",                       # float mm/h
    "showers",                    # float mm/h
    "weather_code",               # int WMO code
]
```

### 应测试的内容

**解析测试 (使用固定 JSON fixture):**
- `_parse_response` 正确解析 Open-Meteo 格式 → DataFrame
- 列名映射正确 (Open-Meteo 的 `cloudbase` → 我们的 `cloud_base_altitude`)
- 日期/小时解析正确

**校验测试:**
- `cloud_base_altitude=None` → 替换为 10000
- `visibility=None` → 替换为 0
- `precipitation_probability=110` → clip 到 100
- `temperature_2m=-70` → 标记 degraded

**缓存集成测试:**
- 缓存命中时不调用 API
- 缓存未命中时调用 API 并写入缓存

**错误处理测试:**
- API 超时 → 抛出 `APITimeoutError`
- API 返回格式无效 → 合理错误
- 重试行为: 第 1 次超时, 第 2 次成功 → 返回正常数据
- 重试次数耗尽 → 抛出 `APITimeoutError`

**`past_days` 参数测试:**
- `past_days=1` → API 请求包含 `past_days=1`
- `past_days=0` → API 请求不含 `past_days` 或为 0

**`fetch_historical` 测试:**
- 使用 Archive API URL (非 Forecast)
- 正确传入 `start_date` 和 `end_date`
- 返回 DataFrame 格式与 `fetch_hourly` 一致

**`fetch_multi_points` 测试:**
- 坐标去重: 输入 3 个坐标, 其中 2 个 ROUND 后相同 → 实际请求 2 个
- 返回字典 key 为 rounded 坐标
- 空坐标列表 → 返回空字典

---

## Task 2: 创建测试 fixture 文件

**Files:**
- Create: `tests/fixtures/weather_data_clear.json`
- Create: `tests/fixtures/weather_data_rainy.json`

### 要创建的 fixture

按 Open-Meteo 实际响应格式创建两个 JSON fixture:

1. **clear**: 晴天场景 (低云量, 无降水) — 用于 Plugin 测试
2. **rainy**: 雨天场景 (高降水概率, 低能见度) — 用于安全检查测试

---

## 验证命令

```bash
python -m pytest tests/unit/test_meteo_fetcher.py -v
```
