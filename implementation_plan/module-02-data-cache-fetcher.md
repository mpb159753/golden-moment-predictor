# M02 - 数据层（SQLite + 多级缓存 + 气象拉取）

## 1. 模块目标

实现“数据获取与复用”的核心能力：同坐标同时间只拉取一次，优先命中缓存，失败可降级。

---

## 2. 背景上下文

- 参考：`design/02-data-model.md`、`design/06-class-sequence.md`、`design/08-operations.md`
- 关键约束：
  - 坐标缓存键使用 `ROUND(lat, 2)` + `ROUND(lon, 2)`
  - 缓存链路：Memory(5min) → SQLite(1h) → Open-Meteo
  - 表唯一键：`(lat_rounded, lon_rounded, forecast_date, forecast_hour)`

---

## 3. 交付范围

### 本模块要做

1. SQLite 初始化脚本与两张表（`weather_cache`、`prediction_history`）。
2. `CacheRepository`（查询、upsert、历史保存）。
3. `MemoryCache`（TTL 内存缓存）。
4. `WeatherCache`（多级缓存门面 + `get_or_fetch`）。
5. `MeteoFetcher`（Open-Meteo 适配、重试、超时）。

### 本模块不做

- 不做天文/地理计算（M03）。
- 不做调度与 Plugin 评分（M06/M05）。

---

## 4. 输入与输出契约

### 输入

- `EngineConfig`（缓存 TTL、DB 路径、坐标精度、超时配置）。
- 坐标与日期（按天拉取逐小时数据）。

### 输出

- 标准化天气 DataFrame（至少含：温度、总云量、分层云、云底、降水概率、能见度、风速）。
- 缓存命中统计信息（供上层聚合到 `meta.cache_stats`）。

---

## 5. 实施任务清单

1. 新建 `gmp/db/init_db.py`：
   - 创建表与索引，对齐设计 SQL。
2. 实现 `gmp/cache/repository.py`：
   - `query(...)`：按坐标+日期+小时查记录
   - `upsert(...)`：`INSERT OR REPLACE`
   - `save_prediction(...)`、`get_history(...)`
3. 实现 `gmp/cache/memory_cache.py`：
   - `get/set/invalidate` + TTL 判定
4. 实现 `gmp/cache/weather_cache.py`：
   - 先内存、后 DB、最后 fetcher
   - 支持 `ignore_ttl=True`（降级取 stale）
5. 实现 `gmp/fetcher/meteo_fetcher.py`：
   - HTTP 请求、字段映射、DataFrame 解析
   - **请求优化**：默认启用 `forecast_days=7` (一次获取一周) 与 `past_days=1` (含昨日历史)，确保 SnowTree/IceIcicle 等插件无需额外请求。
   - 失败抛 `APITimeoutError` 或可识别异常
6. 实现 **Batch Fetching**：
   - 实现 `fetch_batch(locations, days)`：使用 Open-Meteo 逗号分隔坐标方式 (e.g. `lat=52.52,48.85`)，单次请求聚合 ~50 个坐标，显著降低 HTTP 请求量。
   - 响应自动拆分：将返回的大 JSON 拆解为 `Map<Location, DataFrame>`。

---

## 6. 验收标准

1. 同一坐标/日期重复查询优先命中缓存；
2. 过期数据默认不返回，但 `ignore_ttl=True` 可返回；
3. API 正常时写入 DB 与内存缓存；
4. SQLite 唯一键防止重复记录；
5. 数据字段满足下游分析器/Plugin 使用。

---

## 7. 测试清单

- `tests/unit/test_cache_repository.py`
  - upsert 去重、query 命中、TTL 逻辑
- `tests/unit/test_memory_cache.py`
  - 命中/过期/失效
- `tests/unit/test_weather_cache.py`
  - memory hit、db hit、api fallback、stale fallback
- `tests/integration/test_cache_sqlite.py`
  - 全链路缓存读写

---

## 8. 新会话启动提示词

```text
请按 gmp_implementation_plan/module-02-data-cache-fetcher.md 实现 M02：
完成 SQLite 表结构、CacheRepository、MemoryCache、WeatherCache、MeteoFetcher。
要求：坐标 ROUND(2) 去重、支持 stale 降级读取、补齐对应单测与集成测试。
完成后给出缓存链路验证结果（memory/db/api 各场景）。
```
