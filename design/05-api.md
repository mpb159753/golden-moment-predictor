# 5. CLI 命令与 JSON 输出定义

---

## 5.1 CLI 命令

### `gmp predict` — 单点预测

```bash
gmp predict <viewpoint_id> [options]
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `viewpoint_id` | str | ✅ | — | 观景台 ID (如 `niubei_gongga`) |
| `--days` | int | | 7 | 预测天数 (1-16) |
| `--events` | str | | 全部 | 逗号分隔事件类型过滤 |
| `--format` | str | | `table` | 输出格式: `table` / `json` / `detail` |
| `--output` | path | | — | 输出 JSON 文件路径 (仅 `--format json`) |

**示例**

```bash
# 预测牛背山 7 天全部景观
gmp predict niubei_gongga --days 7

# 只看日出金山和云海，输出 JSON
gmp predict niubei_gongga --events sunrise_golden_mountain,cloud_sea --format json

# 输出到文件
gmp predict niubei_gongga --format json --output result.json
```

---

### `gmp predict-route` — 路线预测

```bash
gmp predict-route <route_id> [options]
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `route_id` | str | ✅ | — | 线路 ID (如 `lixiao`) |
| `--days` | int | | 7 | 预测天数 |
| `--events` | str | | 全部 | 逗号分隔事件类型过滤 |
| `--format` | str | | `table` | 输出格式: `table` / `json` / `detail` |

---

### `gmp generate-all` — 批量生成 JSON

```bash
gmp generate-all [options]
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--output` | path | | `./public/data/` | JSON 输出目录 |
| `--archive` | path | | `./archive/` | 历史归档目录 |
| `--days` | int | | 7 | 预测天数 |
| `--no-archive` | flag | | — | 跳过历史归档 |

**行为**

1. 遍历所有已配置的观景台，逐站生成 `forecast.json` + `timeline.json`
2. 遍历所有已配置的线路，生成聚合 `forecast.json`
3. 生成 `index.json` (观景台/线路索引) + `meta.json` (时间戳/版本)
4. 将全部结果复制到 `archive/YYYY-MM-DDTHH-MM/` 目录
5. 所有预测结果同时写入 SQLite `prediction_history` 表

**定时任务示例**

```cron
# 每日 05:00 / 12:00 / 20:00 运行
0 5,12,20 * * * cd /path/to/gmp && venv/bin/python -m gmp generate-all
```

---

### `gmp backtest` — 历史回测

```bash
gmp backtest <viewpoint_id> [options]
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `viewpoint_id` | str | ✅ | — | 观景台 ID |
| `--date` | str | ✅ | — | 目标日期 (YYYY-MM-DD)，优先使用 DB 已有数据，无数据则从历史 API 获取 |
| `--events` | str | | 全部 | 逗号分隔事件类型过滤 |
| `--actual` | str | | — | 实际观测结果 JSON (用于准确性对比) |

---

### `gmp list-viewpoints` — 列出观景台

```bash
gmp list-viewpoints [options]
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--format` | str | | `table` | 输出格式: `table` / `json` |

**输出字段**: ID、名称、坐标、海拔、支持的景观类型

---

### `gmp list-routes` — 列出线路

```bash
gmp list-routes [options]
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--format` | str | | `table` | 输出格式: `table` / `json` |

**输出字段**: ID、名称、停靠站数量、各站观景台 ID

---

## 5.2 JSON 输出文件结构

### 目录布局

```
public/data/                              ← 最新预测 (前端读取)
├── index.json                            ← 观景台 + 线路索引
├── viewpoints/
│   ├── niubei_gongga/
│   │   ├── forecast.json                 ← 多日预测
│   │   └── timeline.json                 ← 逐时数据
│   ├── zheduo_gongga/
│   │   ├── forecast.json
│   │   └── timeline.json
│   └── ...
├── routes/
│   ├── lixiao/
│   │   └── forecast.json                 ← 线路聚合预测
│   └── ...
└── meta.json                             ← 生成时间、版本

archive/                                  ← 历史预测归档
├── 2026-02-12T05-00/
│   ├── viewpoints/ ...
│   ├── routes/ ...
│   └── meta.json
└── ...
```

---

### `index.json` — 全局索引

```json
{
  "viewpoints": [
    {
      "id": "niubei_gongga",
      "name": "牛背山",
      "location": {"lat": 29.75, "lon": 102.35, "altitude": 3660},
      "capabilities": ["sunrise", "cloud_sea", "stargazing", "frost"],
      "forecast_url": "viewpoints/niubei_gongga/forecast.json"
    }
  ],
  "routes": [
    {
      "id": "lixiao",
      "name": "理小路",
      "stops": [
        {"viewpoint_id": "zheduo_gongga", "name": "折多山"},
        {"viewpoint_id": "niubei_gongga", "name": "牛背山"}
      ],
      "forecast_url": "routes/lixiao/forecast.json"
    }
  ]
}
```

---

### `viewpoints/{id}/forecast.json` — 观景台预测

```json
{
  "viewpoint_id": "niubei_gongga",
  "viewpoint_name": "牛背山",
  "generated_at": "2026-02-12T05:00:00+08:00",
  "forecast_days": 7,
  "daily": [
    {
      "date": "2026-02-12",
      "summary": "🌄☁️ 日照金山+壮观云海 — 绝佳组合日",
      "best_event": {
        "event_type": "sunrise_golden_mountain",
        "score": 90,
        "status": "Recommended"
      },
      "events": [
        {
          "event_type": "sunrise_golden_mountain",
          "display_name": "日出金山",
          "time_window": "07:15 - 07:45",
          "score": 90,
          "status": "Recommended",
          "confidence": "High",
          "tags": ["sunrise", "golden_mountain", "clear_sky"],
          "conditions": ["东方少云 ☀️", "贡嘎可见 🏔️", "光路通畅 ✨"],
          "score_breakdown": {
            "light_path":     {"score": 35, "max": 35},
            "target_visible": {"score": 35, "max": 40},
            "local_clear":    {"score": 20, "max": 25}
          }
        },
        {
          "event_type": "cloud_sea",
          "display_name": "云海",
          "time_window": "06:00 - 09:00",
          "score": 90,
          "status": "Recommended",
          "confidence": "High",
          "tags": ["cloud_sea", "magnificent"],
          "conditions": ["云底 2600m < 站点 3660m ☁️"],
          "score_breakdown": {
            "gap":     {"score": 50, "max": 50},
            "density": {"score": 20, "max": 30},
            "wind":    {"score": 20, "max": 20}
          }
        }
      ]
    }
  ]
}
```

---

### `viewpoints/{id}/timeline.json` — 逐时数据

```json
{
  "viewpoint_id": "niubei_gongga",
  "generated_at": "2026-02-12T05:00:00+08:00",
  "date": "2026-02-12",
  "hourly": [
    {
      "hour": 6,
      "time": "06:00",
      "safety_passed": true,
      "weather": {
        "temperature_2m": -3.2,
        "cloud_cover_total": 25,
        "cloud_cover_low": 40,
        "precipitation_probability": 0,
        "weather_code": 1,
        "visibility": 35000,
        "wind_speed_10m": 8.5
      },
      "events_active": [
        {
          "event_type": "cloud_sea",
          "status": "Active",
          "score": 90
        }
      ]
    }
  ]
}
```

---

### `routes/{id}/forecast.json` — 线路聚合预测

```json
{
  "route_id": "lixiao",
  "route_name": "理小路",
  "generated_at": "2026-02-12T05:00:00+08:00",
  "forecast_days": 7,
  "daily": [
    {
      "date": "2026-02-12",
      "route_highlight": "牛背山云海+金山绝佳，建议优先前往",
      "route_score": 83,
      "stops": [
        {
          "order": 1,
          "viewpoint_id": "zheduo_gongga",
          "viewpoint_name": "折多山",
          "best_event": {
            "event_type": "sunrise_golden_mountain",
            "score": 75,
            "status": "Possible"
          },
          "events": [
            {
              "event_type": "sunrise_golden_mountain",
              "score": 75,
              "status": "Possible",
              "confidence": "High"
            }
          ]
        },
        {
          "order": 2,
          "viewpoint_id": "niubei_gongga",
          "viewpoint_name": "牛背山",
          "best_event": {
            "event_type": "cloud_sea",
            "score": 90,
            "status": "Recommended"
          },
          "events": [
            {
              "event_type": "sunrise_golden_mountain",
              "score": 87,
              "status": "Recommended",
              "confidence": "High"
            },
            {
              "event_type": "cloud_sea",
              "score": 90,
              "status": "Recommended",
              "confidence": "High"
            }
          ]
        }
      ]
    }
  ]
}
```

---

### `meta.json` — 生成元数据

```json
{
  "generated_at": "2026-02-12T05:00:00+08:00",
  "engine_version": "4.0.0",
  "forecast_days": 7,
  "viewpoint_count": 12,
  "route_count": 3,
  "generation_duration_seconds": 45.2,
  "data_sources": {
    "weather": "Open-Meteo API",
    "astronomy": "ephem"
  }
}
```

---

## 5.3 枚举值定义

### `event_type`

| 值 | 显示名 | 说明 |
|----|--------|------|
| `sunrise_golden_mountain` | 日出金山 | 日出时段日照金山 |
| `sunset_golden_mountain` | 日落金山 | 日落时段日照金山 |
| `cloud_sea` | 云海 | 低云海景观 |
| `stargazing` | 观星 | 夜间观星窗口 |
| `frost` | 雾凇 | 低温高湿凝华 |
| `snow_tree` | 树挂积雪 | 降雪后树冠覆雪 |
| `ice_icicle` | 冰挂 | 水源冻结成冰帘 |

### `status`

| 值 | 分数范围 | 说明 |
|----|---------|------|
| `Perfect` | 95-100 | 完美条件 |
| `Recommended` | 80-94 | 推荐出行，条件优良 |
| `Possible` | 50-79 | 可能可见，存在风险 |
| `Not Recommended` | 0-49 | 不推荐 |

### `confidence`

| 值 | 说明 |
|----|------|
| `High` | 预报 1-2 天内 |
| `Medium` | 预报 3-4 天 |
| `Low` | 预报 5-16 天 |

### `tags` (自动生成)

| Tag | 触发条件 |
|-----|---------|
| `sunrise` | 日出相关事件 |
| `sunset` | 日落相关事件 |
| `golden_mountain` | 金山事件 |
| `cloud_sea` | 云海事件 |
| `stargazing` | 观星事件 |
| `clear_sky` | 低云量 (< 30%) |
| `magnificent` | 评分 ≥ 85 |
| `partial_data` | 部分数据缺失，评分可能不准确 |

> [!NOTE]
> **组合推荐由前端实现**: `combo_day` (同日 2+ 个 Recommended 以上事件)、`photographer_pick` (金山+云海同日) 等组合型标签**不由引擎生成**，而是由前端读取 JSON 后自行计算。引擎仅输出各事件的独立评分和基础 tags，保持后端职责单一。
>
> **SummaryGenerator**: 后端的 `SummaryGenerator` 仅生成基于规则模板的单日文字摘要 (如"日照金山+壮观云海")，复杂的组合推荐、跨日对比等高级展示逻辑预留给前端。
