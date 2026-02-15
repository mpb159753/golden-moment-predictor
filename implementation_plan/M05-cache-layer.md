# M05: SQLite 缓存层

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 SQLite 持久化缓存层，包括底层 DB 操作 (`CacheRepository`) 和缓存管理 (`WeatherCache`)。

**依赖模块:** M02 (数据模型: `ScoreResult` 等异常类)

---

## 背景

GMP 使用 SQLite 作为唯一缓存层，目的：
1. **跨观景台复用**: 多个观景台观测同一山峰 → 坐标 ROUND(2) 后共享缓存
2. **跨运行复用**: CLI 每次运行独立进程，SQLite 持久化数据跨运行有效
3. **历史追溯**: 保存每次预测记录，用于准确性校验

### 数据新鲜度策略 (非 TTL)
- `forecast` 数据: `fetched_at` 为当日 → 有效
- `archive` 数据: 永不过期（历史天气不变）

### 数据库表结构 (设计文档 §2.2)

两张表：
1. **`weather_cache`**: 天气数据缓存 — 按 `(lat_rounded, lon_rounded, forecast_date, forecast_hour)` 唯一索引
2. **`prediction_history`**: 预测历史记录 — 用于回测和准确性对比

### Weather Cache 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `lat_rounded` | REAL | ROUND(lat, 2) |
| `lon_rounded` | REAL | ROUND(lon, 2) |
| `forecast_date` | DATE | 预报目标日期 |
| `forecast_hour` | INTEGER | 0-23 |
| `fetched_at` | DATETIME | API 获取时间 |
| `temperature_2m` | REAL | 气温 (°C) |
| `cloud_cover_total` | INTEGER | 总云量 0-100 |
| `cloud_cover_low/medium/high` | INTEGER | 分层云量 |
| `cloud_base_altitude` | REAL | 云底高度 (m) |
| `precipitation_probability` | INTEGER | 降水概率 0-100 |
| `visibility` | REAL | 能见度 (m) |
| `wind_speed_10m` | REAL | 风速 (km/h) |
| `snowfall` | REAL | 降雪 (cm/h) |
| `rain` | REAL | 降雨 (mm/h) |
| `showers` | REAL | 阵雨 (mm/h) |
| `weather_code` | INTEGER | WMO 代码 |

完整 DDL 见设计文档 [02-data-model.md §2.2](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/02-data-model.md)。

---

## Task 1: CacheRepository — 数据库操作层

**Files:**
- Create: `gmp/cache/repository.py`
- Test: `tests/unit/test_cache_repository.py`

### 要实现的类

```python
class CacheRepository:
    def __init__(self, db_path: str):
        """连接 SQLite，自动创建表"""

    def _create_tables(self) -> None:
        """创建 weather_cache 和 prediction_history 表 (IF NOT EXISTS)"""

    def query_weather(
        self, lat: float, lon: float, target_date: date, hours: list[int] | None = None
    ) -> list[dict] | None:
        """查询天气缓存
        坐标会自动 ROUND(2)
        hours=None 查全天 (0-23)
        返回 None 表示无数据
        """

    def upsert_weather(
        self, lat: float, lon: float, target_date: date, hour: int, data: dict
    ) -> None:
        """INSERT OR REPLACE 天气数据"""

    def upsert_weather_batch(
        self, lat: float, lon: float, target_date: date, rows: list[dict]
    ) -> None:
        """批量写入 (一天24条)"""

    def save_prediction(self, record: dict) -> None:
        """保存预测历史记录到 prediction_history"""

    def get_predictions(
        self, viewpoint_id: str, target_date: date | None = None
    ) -> list[dict]:
        """查询预测历史"""

    def close(self) -> None:
        """关闭连接"""
```

### 应测试的内容

- 创建数据库时自动建表 (使用 `:memory:` 或临时文件)
- `upsert_weather` + `query_weather` 完整读写循环
- 坐标自动四舍五入 (29.755 → 29.76)
- `hours` 过滤: 只查 [6,7,8] 只返回这几小时的数据
- 重复插入 (同坐标同时间) 覆盖旧数据
- `upsert_weather_batch` 一次写入多条
- `save_prediction` + `get_predictions` 读写验证
- 空查询返回 None 或空列表
- 数据类型正确性 (int/float/str)

---

## Task 2: WeatherCache — 缓存管理层

**Files:**
- Create: `gmp/cache/weather_cache.py`
- Test: `tests/unit/test_weather_cache.py`

### 要实现的类

```python
class WeatherCache:
    def __init__(self, repository: CacheRepository, freshness_config: dict | None = None):
        """
        freshness_config 示例: {"forecast_valid_hours": 24, "archive_never_stale": True}
        """

    def get(
        self, lat: float, lon: float, target_date: date, hours: list[int] | None = None
    ) -> pd.DataFrame | None:
        """获取缓存数据，返回 DataFrame 或 None"""

    def set(
        self, lat: float, lon: float, target_date: date, data: pd.DataFrame
    ) -> None:
        """将 DataFrame 写入缓存"""

    def get_or_fetch(
        self, lat: float, lon: float, target_date: date, fetch_fn
    ) -> pd.DataFrame:
        """有则用缓存，无则调用 fetch_fn 获取并缓存"""

    def is_fresh(self, fetched_at: datetime, data_source: str = "forecast") -> bool:
        """判断数据是否新鲜
        - forecast: fetched_at 为今日 → True
        - archive: 永远 True
        """
```

### 应测试的内容

- `set` + `get` 完整循环: DataFrame 写入后能读出相同数据
- `is_fresh`: forecast 数据今日获取 → True, 昨日获取 → False
- `is_fresh`: archive 数据无论何时获取 → True
- `get` 无数据返回 None
- `get_or_fetch`: 缓存命中时不调用 fetch_fn
- `get_or_fetch`: 缓存未命中时调用 fetch_fn 并写入缓存
- DataFrame 列名与 weather_cache 表字段对应

---

## 验证命令

```bash
python -m pytest tests/unit/test_cache_repository.py tests/unit/test_weather_cache.py -v
```
