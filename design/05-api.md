# 5. API 接口定义

## 5.1 `GET /api/v1/viewpoints` — 获取观景台列表

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| `page` | query | int | | 1 | 页码 |
| `page_size` | query | int | | 20 | 每页数量 (max 100) |

**响应 `200 OK`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `viewpoints` | array | 观景台列表 |
| `viewpoints[].id` | string | 观景台唯一 ID |
| `viewpoints[].name` | string | 观景台名称 |
| `viewpoints[].location.lat` | float | 纬度 |
| `viewpoints[].location.lon` | float | 经度 |
| `viewpoints[].location.altitude` | int | 海拔 (m) |
| `viewpoints[].capabilities` | string[] | 支持的事件类型 |
| `viewpoints[].targets` | array | 可观测目标列表 |
| `viewpoints[].targets[].name` | string | 目标名称 |
| `viewpoints[].targets[].altitude` | int | 目标海拔 (m) |
| `viewpoints[].targets[].weight` | string | 权重: `primary` / `secondary` |
| `viewpoints[].targets[].applicable_events` | string[]∣null | 适用事件, null=自动计算 |
| `pagination.page` | int | 当前页码 |
| `pagination.page_size` | int | 每页数量 |
| `pagination.total` | int | 总数量 |
| `pagination.total_pages` | int | 总页数 |

---

## 5.2 `GET /api/v1/forecast/{viewpoint_id}` — 获取景观预测报告

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| `viewpoint_id` | path | string | ✅ | | 观景台 ID |
| `days` | query | int | | 7 | 预测天数 (1-7) |
| `events` | query | string | | (全部) | 逗号分隔的事件类型过滤，如 `cloud_sea,frost` |

> [!NOTE]
> **`events` 参数行为**：
> - **不传**: 返回该观景台 `capabilities` 中所有景观评分（聚合查询）
> - **传入**: 只返回指定类型的景观评分，如 `?events=cloud_sea,stargazing`
> - **传入不在 capabilities 中的事件**: 忽略，不报错
> - **Scheduler 按需优化**: 若过滤后无 Plugin 需要 L2 数据，则跳过远程 API 调用

**响应 `200 OK`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `report_date` | string (date) | 报告生成日期 |
| `viewpoint` | string | 观景台名称 |
| `forecast_days` | array | 每日预测列表 |
| `forecast_days[].date` | string (date) | 目标日期 |
| `forecast_days[].confidence` | string | 置信度: `High`(T+1~2) / `Medium`(T+3~4) / `Low`(T+5~7) |
| `forecast_days[].summary` | string | 当日摘要 (规则生成或LLM生成) |
| `forecast_days[].summary_mode` | string | 摘要生成方式: `rule` / `llm` |
| `forecast_days[].events` | array | 推荐事件列表 (仅通过L1的事件) |
| `.events[].type` | string | 事件类型 (见枚举表) |
| `.events[].time_window` | string | 最佳观赏时段 |
| `.events[].secondary_window` | string | 次佳时段 (观星等可选) |
| `.events[].score` | int | 综合评分 (0-100) |
| `.events[].status` | string | `Perfect`(≥95) / `Recommended`(≥80) / `Possible`(≥50) / `Not Recommended`(<50) |
| `.events[].conditions` | object | 条件详情 (结构因事件类型而异) |
| `.events[].score_breakdown` | object | 评分明细 |
| `.events[].score_breakdown.{dimension}` | object | 各维度: `{"score": int, "max": int}` |
| `meta.generated_at` | string (datetime) | 生成时间 (ISO 8601) |
| `meta.cache_stats.api_calls` | int | 本次请求的 API 调用数 |
| `meta.cache_stats.cache_hits` | int | 缓存命中数 |
| `meta.cache_stats.saved_calls` | int | 因缓存/懒加载节省的调用数 |

---

## 5.3 `GET /api/v1/timeline/{viewpoint_id}` — 获取逐小时时间轴数据

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| `viewpoint_id` | path | string | ✅ | | 观景台 ID |
| `days` | query | int | | 7 | 预测天数 (1-7) |

**响应 `200 OK`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `viewpoint` | string | 观景台名称 |
| `timeline_days` | array | 每日时间轴列表 |
| `timeline_days[].date` | string (date) | 日期 |
| `timeline_days[].confidence` | string | 置信度 |
| `timeline_days[].hours` | array | 24小时逐时数据 |
| `.hours[].hour` | int | 小时 (0-23) |
| `.hours[].l1_passed` | bool | L1 本地滤网是否通过 |
| `.hours[].cloud_cover` | int | 总云量 (0-100%) |
| `.hours[].precip_prob` | int | 降水概率 (0-100%) |
| `.hours[].temperature` | float | 2m 气温 (°C) |
| `.hours[].tags` | string[] | 时段标签 (见枚举表) |

---

## 5.4 通用错误响应

| HTTP 状态码 | 错误类型 | 说明 |
|------------|--------|------|
| `404` | `ViewpointNotFound` | 观景台 ID 不存在 |
| `408` | `APITimeout` | 外部气象 API 超时 |
| `422` | `InvalidParameter` | 请求参数不合法 (如 days > 7) |
| `503` | `ServiceDegraded` | 服务降级 (使用过期缓存, 响应头含 `X-Data-Freshness: stale`) |

```json
{
  "error": {
    "type": "ViewpointNotFound",
    "message": "未找到观景台: invalid_id",
    "code": 404
  }
}
```

---

## 5.5 枚举值定义

### `event_type` 事件类型

| 值 | 说明 | 数据需求 | Plugin |
|----|------|---------|--------|
| `sunrise_golden_mountain` | 日出金山 | L2 目标 + L2 光路 + 天文 | GoldenMountainPlugin |
| `sunset_golden_mountain` | 日落金山 | L2 目标 + L2 光路 + 天文 | GoldenMountainPlugin |
| `stargazing` | 观星/银河 | 天文 (月相+晨暮曦) | StargazingPlugin |
| `cloud_sea` | 云海 | 仅 L1 (云底高度) | CloudSeaPlugin |
| `frost` | 雾凇 | 仅 L1 (温度+湿度+风速) | FrostPlugin |
| `snow_tree` | 树挂积雪 | 仅 L1 (降雪+温度+风速) | SnowTreePlugin |
| `ice_icicle` | 冰挂 | 仅 L1 (降雨降雪+温度+风速) | IceIciclePlugin |
| `sunrise` | 普通日出 | L2 光路 + 天文 | — |
| `sunset` | 普通日落 | L2 光路 + 天文 | — |

### `tags` 时段标签

| 值 | 说明 |
|----|------|
| `stargazing_window` | 最佳观星 (无月光+低云量) |
| `stargazing_secondary` | 次佳观星 (月相<50%残月微光) |
| `pre_sunrise` | 日出前30分钟 |
| `sunrise_golden` | 日照金山最佳时段 |
| `cloud_sea` | 云海可见时段 |
| `frost_window` | 雾凇观赏时段 |
| `snow_tree_window` | 树挂积雪观赏时段 |
| `ice_icicle_window` | 冰挂观赏时段 |
| `sunset_window` | 日落窗口 |
| `pre_dawn` | 天文晨曦前 |
| `moonrise` | 月出时刻 |
| `clearing` | 天气转晴 |
| `overcast` | 阴天 |
| `rain` | 降水时段 |
