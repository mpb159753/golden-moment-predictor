# 4. 各阶段数据流示例

以 **牛背山 → 贡嘎金山 (2026-02-11 日出)** 场景完整演示各模块的输入输出。

---

## Stage 0: 输入参数

```python
# 用户请求
request = {
    "viewpoint_id": "niubei_gongga",
    "days": 7,
    "events": None  # None = 返回 capabilities 中所有景观评分
}

# 加载配置后的 Viewpoint 对象
viewpoint = Viewpoint(
    id="niubei_gongga",
    name="牛背山",
    location=Location(lat=29.75, lon=102.35, altitude=3660),
    capabilities=["sunrise", "sunset", "stargazing", "cloud_sea", "frost", "snow_tree", "ice_icicle"],
    targets=[
        Target(
            name="贡嘎主峰", lat=29.58, lon=101.88, altitude=7556,
            weight="primary",
            applicable_events=None,  # None = 自动计算
        ),
        Target(
            name="雅拉神山", lat=30.15, lon=101.75, altitude=5820,
            weight="secondary",
            applicable_events=["sunset"],  # 手动指定: 仅看日落金山
        ),
    ]
)
```

---

## Stage 1: Plugin 收集 + 需求聚合

```python
# 活跃 Plugin 列表 (capabilities 过滤后)
active_plugins = [
    GoldenMountainPlugin("sunrise_golden_mountain"),  # sunrise_golden_mountain
    GoldenMountainPlugin("sunset_golden_mountain"),   # sunset_golden_mountain
    StargazingPlugin,      # stargazing
    CloudSeaPlugin,        # cloud_sea
    FrostPlugin,           # frost
    SnowTreePlugin,        # snow_tree
    IceIciclePlugin,       # ice_icicle
]

# 聚合 DataRequirement
aggregated = DataRequirement(
    needs_l2_target=True,       # GoldenMountainPlugin 需要
    needs_l2_light_path=True,   # GoldenMountainPlugin 需要
    needs_astro=True,           # GoldenMountainPlugin + StargazingPlugin 需要
)
# → 需要获取: 本地天气 + 天文数据 + 目标天气 + 光路天气
```

---

## Stage 2: AstroUtils 天文计算输出

```python
sun_events = SunEvents(
    sunrise=datetime(2026, 2, 11, 7, 28),
    sunset=datetime(2026, 2, 11, 18, 35),
    sunrise_azimuth=108.5,
    sunset_azimuth=251.5,
    astronomical_dawn=datetime(2026, 2, 11, 5, 55),
    astronomical_dusk=datetime(2026, 2, 11, 19, 55),
)

moon_status = MoonStatus(
    phase=35,
    elevation=-22.5,
    moonrise=datetime(2026, 2, 11, 3, 15),
    moonset=datetime(2026, 2, 11, 13, 40)
)

# 方位角自动判定
bearing_to_gongga = GeoUtils.calculate_bearing(
    viewpoint.location, targets[0]
)
# → 245° (贡嘎在西南方)
# 日出方位角 108.5° 的对面是 288.5°
# |245 - 288.5| = 43.5° < 90° → 贡嘎适配 sunrise ✅

# 光路检查点: 沿方位角 108.5°，每 10km 一个，共 10 个点
light_path_points = GeoUtils.calculate_light_path_points(
    lat=29.75, lon=102.35, azimuth=108.5, count=10, interval_km=10
)

# 观星时间窗口
stargazing_window = StargazingWindow(
    optimal_start=datetime(2026, 2, 11, 19, 55),
    optimal_end=datetime(2026, 2, 12, 3, 15),
    good_start=datetime(2026, 2, 12, 3, 15),
    good_end=datetime(2026, 2, 12, 5, 55),
    quality="optimal",
)
```

---

## Stage 3: MeteoFetcher 气象数据输出

```python
# 3a. 本地天气 (牛背山 29.75, 102.35) — Phase 1 获取
local_weather = pd.DataFrame({
    "timestamp":       ["06:00", "07:00", "08:00", ...],
    "temperature_2m":  [-5.2,    -3.8,    -2.1,   ...],
    "cloud_cover_total":[25,      22,      30,     ...],
    "cloud_cover_low": [70,       75,      65,     ...],
    "cloud_cover_medium":[5,      3,       8,      ...],
    "cloud_cover_high":[0,        0,       2,      ...],
    "cloud_base_altitude":[2800,  2600,    2900,   ...],
    "precipitation_probability":[0, 0,     5,      ...],
    "visibility":      [30000,   35000,   28000,   ...],
    "wind_speed_10m":  [3.1,     2.8,     4.5,     ...],
    "snowfall":        [0.0,     0.0,     0.0,     ...],  # cm/h
    "rain":            [0.0,     0.0,     0.0,     ...],  # mm/h
    "showers":         [0.0,     0.0,     0.0,     ...],  # mm/h
    "weather_code":    [1,       0,       2,       ...],  # WMO code
})

# 3b. 目标山峰天气 (贡嘎 29.58, 101.88) — Phase 2 按需获取
target_weather_gongga = pd.DataFrame({
    "timestamp":       ["06:00", "07:00", "08:00", ...],
    "cloud_cover_total":[10,      15,      20,     ...],
    "cloud_cover_high":[2,        5,       5,      ...],
    "cloud_cover_medium":[5,      8,       10,     ...],
    # → 高云+中云 = 7%, 13%, 15% → 日出时(07:00) 13%
})

# 3c. 光路天气 (10个检查点) — Phase 2 按需获取
# 仅展示日出时刻 07:00 的各点数据
light_path_weather = {
    "LP-01 (10km)":  {"low_cloud": 5,  "mid_cloud": 3,  "combined": 8},
    "LP-02 (20km)":  {"low_cloud": 3,  "mid_cloud": 2,  "combined": 5},
    "LP-03 (30km)":  {"low_cloud": 8,  "mid_cloud": 5,  "combined": 13},
    "LP-04 (40km)":  {"low_cloud": 5,  "mid_cloud": 3,  "combined": 8},
    "LP-05 (50km)":  {"low_cloud": 10, "mid_cloud": 5,  "combined": 15},
    "LP-06 (60km)":  {"low_cloud": 8,  "mid_cloud": 2,  "combined": 10},
    "LP-07 (70km)":  {"low_cloud": 3,  "mid_cloud": 2,  "combined": 5},
    "LP-08 (80km)":  {"low_cloud": 5,  "mid_cloud": 3,  "combined": 8},
    "LP-09 (90km)":  {"low_cloud": 3,  "mid_cloud": 2,  "combined": 5},
    "LP-10 (100km)": {"low_cloud": 2,  "mid_cloud": 1,  "combined": 3},
}
# 10点均值 = (8+5+13+8+15+10+5+8+5+3) / 10 = 8.0% → ≤10% ✅
```

---

## Stage 4: DataContext 构建 + L1/L2 滤网

```python
# 构建共享数据上下文 (所有 Plugin 复用)
ctx = DataContext(
    date=date(2026, 2, 11),
    viewpoint=viewpoint,
    local_weather=local_weather,
    sun_events=sun_events,
    moon_status=moon_status,
    stargazing_window=stargazing_window,
    target_weather={"贡嘎主峰": target_weather_gongga},
    light_path_weather=light_path_weather,
    data_freshness="fresh",
)

# Plugin 触发结果 (各 Plugin 内部自行判断安全条件和触发条件)
# GoldenMountainPlugin.score(ctx)  # 内部判定 → True (总云22%<80%, 有Target, 关注时段降水低)
# StargazingPlugin.score(ctx)      # 内部判定      → True (夜间云量低, 无降水)
# CloudSeaPlugin.score(ctx)        # 内部判定        → True (云底2600<站点3660, 早晨无降水)
# FrostPlugin.score(ctx)           # 内部判定           → True (温度-3.8<2°C, 早晨无降水)
# SnowTreePlugin.score(ctx)        # 内部判定           → None (近期无降雪, 未触发)
# IceIciclePlugin.score(ctx)       # 内部判定           → None (近期无有效水源, 未触发)
```

---

## Stage 5: Plugin 评分输出

```python
# ═══════════ 日照金山 (GoldenMountainPlugin) ═══════════
golden_score = {
    "event_type": "sunrise_golden_mountain",
    "time_window": "07:15 - 07:45",
    "score_breakdown": {
        "light_path":     {"score": 35, "max": 35, "detail": "10点均值云量8%, ≤10%满分"},
        "target_visible": {"score": 32, "max": 40, "detail": "贡嘎高+中云13%, 10-20%区间"},
        "local_clear":    {"score": 20, "max": 25, "detail": "本地总云22%, 15-30%区间"},
    },
    "total_score": 87,   # 35+32+20 = 87
    "status": "Recommended",
    "confidence": "High",
}

# ═══════════ 观星 (StargazingPlugin) ═══════════
stargazing_score = {
    "event_type": "stargazing",
    "time_window": "19:55 - 03:15",
    "secondary_window": "03:15 - 05:55",
    "score_breakdown": {
        "base":  {"score": 100, "max": 100, "detail": "optimal: 完美暗夜"},
        "cloud": {"score":  -2, "max": 0,   "detail": "夜间平均云量3%"},
        "wind":  {"score":   0, "max": 0,   "detail": "2.8km/h ≤20"},
    },
    "total_score": 98,
    "status": "Perfect",
    "confidence": "High",
}

# ═══════════ 云海 (CloudSeaPlugin) ═══════════
cloud_sea_score = {
    "event_type": "cloud_sea",
    "time_window": "06:00 - 09:00",
    "score_breakdown": {
        "gap":     {"score": 50, "max": 50, "detail": "高差1060m > 800m"},
        "density": {"score": 20, "max": 30, "detail": "低云75%, >50%档位"},
        "mid_structure": {"factor": 1.0, "detail": "中云5%, 上层通透"},
        "wind":    {"score": 20, "max": 20, "detail": "风速2.8km/h < 10km/h"},
    },
    "total_score": 90,   # (50+20)×1.0+20 = 90
    "status": "Recommended",
    "confidence": "High",
}

# ═══════════ 雾凇 (FrostPlugin) ═══════════
frost_score = {
    "event_type": "frost",
    "time_window": "05:00 - 08:30",
    "score_breakdown": {
        "temperature": {"score": 40, "max": 40, "detail": "-3.8°C, 在[-5,0)区间满分"},
        "moisture":    {"score":  5, "max": 30, "detail": "能见度35km, 空气干燥"},
        "wind":        {"score": 20, "max": 20, "detail": "2.8km/h, 理想"},
        "cloud":       {"score":  7, "max": 10, "detail": "低云75%, >60%略重"},
    },
    "total_score": 72,   # 40+5+20+7 = 72
    "status": "Possible",
    "confidence": "High",
    "note": "温度理想但空气干燥，雾凇形成概率较低",
}

# ═══════════ 树挂积雪 (SnowTreePlugin) ═══════════
# 本日未触发 (近期无降雪), score() 触发判定=False, 不进入评分

# ═══════════ 冰挂 (IceIciclePlugin) ═══════════
# 本日未触发 (近期无有效水源+冻结), score() 触发判定=False, 不进入评分
```

---

## Stage 6a: ForecastReporter 输出 (forecast.json)

```json
{
  "report_date": "2026-02-10",
  "viewpoint": "牛背山",
  "forecast_days": [
    {
      "date": "2026-02-11",
      "confidence": "High",
      "summary": "极佳观景日 — 日照金山+壮观云海+完美暗夜+雾凇可能",
      "summary_mode": "rule",
      "events": [
        {
          "type": "sunrise_golden_mountain",
          "time_window": "07:15 - 07:45",
          "score": 87,
          "status": "Recommended",
          "conditions": {
            "local": {
              "cloud_cover": "22%",
              "temperature": -3.8
            },
            "targets": [
              {"name": "贡嘎主峰", "visible": true, "cloud_cover": "13%", "matched_event": "sunrise"},
              {"name": "雅拉神山", "visible": false, "cloud_cover": "85%", "matched_event": "sunset"}
            ],
            "light_path": {
              "status": "通畅",
              "azimuth": "108.5° (东偏南)",
              "check_points": 10,
              "avg_cloud_cover": "8%"
            }
          },
          "score_breakdown": {
            "light_path":     {"score": 35, "max": 35},
            "target_visible": {"score": 32, "max": 40},
            "local_clear":    {"score": 20, "max": 25}
          }
        },
        {
          "type": "stargazing",
          "time_window": "19:55 - 03:15",
          "secondary_window": "03:15 - 05:55",
          "score": 98,
          "status": "Perfect",
          "conditions": {
            "sky": "夜间云量3%, 能见度35km",
            "moon": "月相35%, 月落13:40 (完美暗夜至次日月出03:15)",
            "wind": "2.8 km/h"
          },
          "score_breakdown": {
            "base":  {"score": 100, "max": 100},
            "cloud": {"score":  -2, "max": 0},
            "wind":  {"score":   0, "max": 0}
          }
        },
        {
          "type": "cloud_sea",
          "time_window": "06:00 - 09:00",
          "score": 90,
          "status": "Recommended",
          "conditions": {
            "gap": "1060m (站点3660m - 云底2600m)",
            "low_cloud": "75%",
            "wind": "2.8 km/h"
          },
          "score_breakdown": {
            "gap":     {"score": 50, "max": 50},
            "density": {"score": 20, "max": 30},
            "wind":    {"score": 20, "max": 20}
          }
        },
        {
          "type": "frost",
          "time_window": "05:00 - 08:30",
          "score": 72,
          "status": "Possible",
          "conditions": {
            "temperature": "-3.8°C",
            "visibility": "35km (空气干燥)",
            "wind": "2.8 km/h",
            "low_cloud": "75%"
          },
          "score_breakdown": {
            "temperature": {"score": 40, "max": 40},
            "moisture":    {"score":  5, "max": 30},
            "wind":        {"score": 20, "max": 20},
            "cloud":       {"score":  7, "max": 10}
          }
        }
      ]
    },
    {
      "date": "2026-02-12",
      "confidence": "High",
      "summary": "不推荐 — 全天降水",
      "events": []
    }
  ],
  "meta": {
    "generated_at": "2026-02-10T08:00:00+08:00",
    "cache_stats": { "api_calls": 14, "cache_hits": 2, "saved_calls": 8 }
  }
}
```

## Stage 6b: TimelineReporter 输出 (timeline.json)

```json
{
  "viewpoint": "牛背山",
  "timeline_days": [
    {
      "date": "2026-02-11",
      "confidence": "High",
      "hours": [
        {"hour":  0, "l1_passed": true,  "cloud_cover": 5,  "precip_prob": 0, "temperature": -7.2, "tags": ["stargazing_window"]},
        {"hour":  1, "l1_passed": true,  "cloud_cover": 3,  "precip_prob": 0, "temperature": -7.8, "tags": ["stargazing_window"]},
        {"hour":  2, "l1_passed": true,  "cloud_cover": 4,  "precip_prob": 0, "temperature": -8.1, "tags": ["stargazing_window"]},
        {"hour":  3, "l1_passed": true,  "cloud_cover": 5,  "precip_prob": 0, "temperature": -8.5, "tags": ["stargazing_window", "moonrise"]},
        {"hour":  4, "l1_passed": true,  "cloud_cover": 8,  "precip_prob": 0, "temperature": -8.0, "tags": ["stargazing_secondary"]},
        {"hour":  5, "l1_passed": true,  "cloud_cover": 12, "precip_prob": 0, "temperature": -6.5, "tags": ["frost_window", "pre_dawn"]},
        {"hour":  6, "l1_passed": true,  "cloud_cover": 22, "precip_prob": 0, "temperature": -5.2, "tags": ["pre_sunrise", "cloud_sea", "frost_window"]},
        {"hour":  7, "l1_passed": true,  "cloud_cover": 22, "precip_prob": 0, "temperature": -3.8, "tags": ["sunrise_golden", "cloud_sea", "frost_window"]},
        {"hour":  8, "l1_passed": true,  "cloud_cover": 30, "precip_prob": 5, "temperature": -2.1, "tags": ["cloud_sea"]},
        {"hour":  9, "l1_passed": true,  "cloud_cover": 40, "precip_prob": 10, "temperature": 0.5, "tags": []},
        {"hour": 10, "l1_passed": false, "cloud_cover": 65, "precip_prob": 30, "temperature": 2.8, "tags": ["overcast"]},
        {"hour": 11, "l1_passed": false, "cloud_cover": 75, "precip_prob": 55, "temperature": 4.2, "tags": ["rain"]},
        {"hour": 12, "l1_passed": false, "cloud_cover": 80, "precip_prob": 60, "temperature": 5.1, "tags": ["rain"]},
        {"hour": 17, "l1_passed": true,  "cloud_cover": 20, "precip_prob": 5,  "temperature": 1.2, "tags": ["clearing"]},
        {"hour": 18, "l1_passed": true,  "cloud_cover": 15, "precip_prob": 0,  "temperature": -0.5, "tags": ["sunset_window"]},
        {"hour": 22, "l1_passed": true,  "cloud_cover": 8,  "precip_prob": 0,  "temperature": -5.8, "tags": ["stargazing_window"]},
        {"hour": 23, "l1_passed": true,  "cloud_cover": 5,  "precip_prob": 0,  "temperature": -6.3, "tags": ["stargazing_window"]}
      ]
    }
  ]
}
```

> [!NOTE]
> - **`/forecast`** 返回精选推荐事件，适合卡片列表和简洁展示
> - **`/timeline`** 返回逐24小时数据（含温度），适合时间轴图表
> - 两个端点共享同一套后端计算逻辑（同一个 `DataContext`），仅输出层不同
