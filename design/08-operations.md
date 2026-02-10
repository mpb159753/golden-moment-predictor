# 8. 错误处理、日志与并发

## 8.1 错误分级与处理

| 级别 | 场景 | 处理策略 | 用户影响 |
|------|------|---------|---------|
| 🟢 L0 透明恢复 | 内存缓存过期 | 自动重新获取，用户无感知 | 无 |
| 🟡 L1 降级响应 | API 超时但有旧缓存 | 使用 stale 缓存，标记 `Degraded` | 响应头 `X-Data-Freshness: stale` |
| 🟠 L2 部分失败 | 目标天气获取失败 | 跳过该目标评分，其他正常 | 事件标记 `partial_data` |
| 🔴 L3 服务不可用 | 所有 API 失败且无缓存 | 返回 503 错误 | 服务暂时不可用 |

---

## 8.2 降级策略

```python
class DegradationPolicy:
    """降级策略"""
    
    @staticmethod
    def handle_fetch_error(error: Exception, cache: WeatherCache,
                           coords: tuple, target_date: date) -> tuple[pd.DataFrame, str]:
        """
        返回: (数据, 置信度标记)
        """
        if isinstance(error, APITimeoutError):
            stale = cache.get(coords[0], coords[1], target_date, 
                            hours=list(range(24)), ignore_ttl=True)
            if stale is not None:
                logger.warning(f"API超时，使用过期缓存 ({coords})")
                return stale, "Degraded"
            else:
                raise ServiceUnavailableError(f"无可用数据: {coords}")
        
        elif isinstance(error, InvalidCoordinateError):
            raise error
        
        else:
            logger.error(f"未知获取错误: {error}", exc_info=True)
            stale = cache.get(coords[0], coords[1], target_date,
                            hours=list(range(24)), ignore_ttl=True)
            if stale is not None:
                return stale, "Degraded"
            raise
```

## 8.3 超时配置

```python
TIMEOUT_CONFIG = {
    "open_meteo_api": {
        "connect_timeout": 5,
        "read_timeout": 15,
        "retries": 2,
        "retry_delay": 1,
    },
    "ephem_calculation": {
        "max_duration": 0.5,
    },
    "total_request": {
        "max_duration": 30,
    }
}
```

---

## 8.4 日志分级

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| `DEBUG` | 开发调试 | `光路LP-05云量: low=10, mid=5, combined=15` |
| `INFO` | 正常流程 | `牛背山 2026-02-11 评分完成: golden=87, stargazing=98` |
| `WARNING` | 降级/异常但可恢复 | `Open-Meteo 超时, 使用缓存数据 (fetched 2h ago)` |
| `ERROR` | 失败/需介入 | `API连续失败3次, 无可用缓存` |

## 8.5 结构化日志

```python
import structlog
logger = structlog.get_logger()

# 请求级别
logger.info("forecast_generated",
    viewpoint="niubei_gongga",
    date="2026-02-11",
    events_count=4,
    top_event="stargazing",
    top_score=98,
    api_calls=14,
    cache_hits=2,
    duration_ms=1200
)

# Plugin 评分级别
logger.debug("plugin_scored",
    plugin="GoldenMountainPlugin",
    event_type="sunrise_golden_mountain",
    total_score=87,
    breakdown={"light_path": 35, "target_visible": 32, "local_clear": 20},
    elapsed_ms=5
)

# 降级告警
logger.warning("degraded_response",
    viewpoint="niubei_gongga",
    reason="api_timeout",
    cache_age_hours=2.5
)
```

## 8.6 关键指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `forecast_duration_ms` | Histogram | 单次预报生成耗时 |
| `api_calls_total` | Counter | 外部 API 调用总次数 |
| `cache_hit_ratio` | Gauge | 缓存命中率 |
| `degraded_responses_total` | Counter | 降级响应次数 |
| `score_distribution` | Histogram | 评分分布 (按 Plugin 类型) |

---

## 8.7 并发策略

```python
import asyncio
from asyncio import Semaphore

class ConcurrencyControl:
    def __init__(self, config: EngineConfig):
        self.api_semaphore = Semaphore(5)
        self.batch_semaphore = Semaphore(3)
    
    async def fetch_with_limit(self, fetcher, lat, lon, days):
        async with self.api_semaphore:
            return await fetcher.fetch_hourly(lat, lon, days)
    
    async def run_batch(self, viewpoint_ids: list):
        tasks = []
        for vid in viewpoint_ids:
            async with self.batch_semaphore:
                task = asyncio.create_task(self.scheduler.run(vid))
                tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=True)
```

## 8.8 API 调用限流

| API | 限制 | 策略 |
|-----|------|------|
| Open-Meteo (免费版) | 10,000 requests/day | 日级别 + 令牌桶限流 |
| 单次请求并发 | 5 并发 | 信号量 |
| 批量处理并发 | 3 观景台/批 | 信号量 |
| 光路10点请求 | 合并为 1 次多坐标请求 | `fetch_multi_points` |

## 8.9 请求合并策略

```python
class RequestCoalescer:
    """同坐标请求合并"""
    
    def coalesce_light_path(self, coords: list[tuple], days: int) -> dict:
        """
        将10个光路点的坐标去重后批量请求
        ROUND(lat, 2) + ROUND(lon, 2) 相同的坐标视为同一点
        """
        unique_coords = set()
        for lat, lon in coords:
            rounded = (round(lat, 2), round(lon, 2))
            unique_coords.add(rounded)
        
        # 批量请求去重后的坐标 (通常 10→5~7 个)
        results = {}
        for lat, lon in unique_coords:
            results[(lat, lon)] = self.fetcher.fetch_hourly(lat, lon, days)
        
        return results
```
