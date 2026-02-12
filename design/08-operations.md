# 8. 错误处理、日志与运维

## 8.1 错误分级与处理

| 级别 | 场景 | 处理策略 | 用户影响 |
|------|------|---------|---------|
| 🟢 L0 透明恢复 | SQLite 缓存自动刷新 | 缓存数据过期后自动重新获取，用户无感知 | 无 |
| 🟡 L1 降级响应 | API 超时但有旧缓存 | 使用 stale 缓存，标记 `Degraded` | confidence 标记为 `Degraded` |
| 🟠 L2 部分失败 | 目标天气获取失败 | 跳过该目标评分，其他正常 | 事件标记 `partial_data` |
| 🔴 L3 服务不可用 | 所有 API 失败且无缓存 | 返回错误信息并退出 | CLI 输出错误提示 |

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
    "open_meteo_archive_api": {
        "connect_timeout": 5,
        "read_timeout": 30,       # 历史数据查询可能更慢
        "retries": 2,
        "retry_delay": 2,
    },
    "ephem_calculation": {
        "max_duration": 0.5,
    },
    "total_request": {
        "max_duration": 30,
    },
    "backtest_request": {
        "max_duration": 60,       # 回测允许更长超时
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
    total_score=90,
    breakdown={"light_path": 35, "target_visible": 35, "local_clear": 20},
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

## 8.7 定时任务配置

GMP 采用预计算模式，通过 cron 定时运行批量生成命令：

```cron
# 每日 05:00 / 12:00 / 20:00 运行预测生成
0 5,12,20 * * * cd /path/to/gmp && venv/bin/python -m gmp generate-all 2>&1 >> /var/log/gmp/generate.log
```

## 8.8 API 调用限流

| API | 限制 | 策略 |
|-----|------|------|
| Open-Meteo (免费版) | 10,000 requests/day | MeteoFetcher 内部日级计数控制 |
| 光路10点请求 | 合并为 1 次多坐标请求 | `fetch_multi_points` |
| 坐标去重 | ROUND(lat,2) + ROUND(lon,2) | 缓存层自然去重 |

---

## 8.9 批量任务错误恢复

| 策略 | 说明 |
|------|------|
| **默认模式** | 单站失败时跳过，记录 warning，继续处理其余站点 |
| `--fail-fast` | 任一站点失败则立即中止整个批量任务 |
| `meta.json` | 批量完成后生成 `meta.json`，包含 `failed_viewpoints` 列表及失败原因 |
| **已生成文件** | 已生成的 JSON 文件保持不变，不回滚 |

---

## 8.10 数据校验规则

在 `MeteoFetcher._parse_response()` 之后，对 API 返回数据进行校验：

| 字段 | 校验规则 | 异常处理 |
|------|---------|---------|
| `cloud_base_altitude` | 非 None 且 ≥ 0 | None → 10000（极高 = 无低云） |
| `temperature_2m` | -60°C ~ 60°C | 超范围标记 `data_quality=degraded` |
| `precipitation_probability` | 0 ~ 100 | clip 到范围内 |
| `visibility` | ≥ 0 | None → 0（保守假设不可见） |
| `cloud_cover` | 0 ~ 100 | clip 到范围内 |
| `wind_speed_10m` | ≥ 0 | None → 0 |
