# 3. 可插拔评分器架构 (ScorerPlugin)

> [!CAUTION]
> **本文档中出现的所有评分阈值、权重、分界值均为默认参考值（示例）。**
> 实际运行时，所有数值均通过 `engine_config.yaml` 配置文件加载，代码中不应存在魔法数字。
> 配置结构详见 [09-testing-config.md §9.5](./09-testing-config.md)。

## 3.1 设计概述

评分系统采用**可插拔 Plugin 架构**：每种景观类型由一个独立的 `ScorerPlugin` 实现，Plugin 通过 `DataRequirement` 声明自身所需的数据，Scheduler 据此聚合需求、统一获取后通过 `DataContext` 分发。

> [!IMPORTANT]
> **扩展新景观的完整步骤**：
> 1. 实现 `ScorerPlugin` 接口（评分逻辑 + 触发条件 + 数据需求声明）
> 2. 在观景台配置的 `capabilities` 中添加新事件类型
> 3. 在 `ScoreEngine` 中注册 Plugin
> 
> **无需改动**：Scheduler、API 路由、Reporter 等管线代码。

---

## 3.2 Plugin 核心契约

### DataRequirement — 数据需求声明

每个 Plugin 声明自己需要哪些数据，Scheduler 聚合所有活跃 Plugin 的需求后一次性获取。

```python
@dataclass
class DataRequirement:
    """评分器的数据需求声明"""
    needs_l2_target: bool = False       # 是否需要目标山峰天气（触发 L2 远程请求）
    needs_l2_light_path: bool = False   # 是否需要光路检查点天气（触发 L2 远程请求）
    needs_astro: bool = False           # 是否需要天文数据（月相/日出日落/晨暮曦）
    past_hours: int = 0                 # 需要多少小时的历史数据 (0=无需回看)
    season_months: list[int] | None = None  # 适用月份 (1-12)，None=全年适用
```

### DataContext — 共享数据上下文

所有 Plugin 共享同一份 `DataContext`，保证数据复用、不重复请求：

```python
@dataclass
class DataContext:
    """一天的共享数据上下文 — 所有 Plugin 复用"""
    date: date
    viewpoint: Viewpoint
    
    # Phase 1: 始终获取（所有 Plugin 共享）
    local_weather: pd.DataFrame           # 本地逐时天气
    
    # 按需获取（仅当有 Plugin 声明需要时才获取）
    sun_events: SunEvents | None = None
    moon_status: MoonStatus | None = None
    stargazing_window: StargazingWindow | None = None
    
    # Phase 2: 按需获取（仅当有 Plugin 声明 needs_l2 时）
    target_weather: dict[str, pd.DataFrame] | None = None  # {target_name: DataFrame}
    light_path_weather: list[dict] | None = None            # 10点光路数据
    
    # 数据质量标记
    data_freshness: str = "fresh"  # "fresh" | "stale" | "degraded"
```

> [!TIP]
> **数据获取时序**：
> 1. Scheduler 收集所有活跃 Plugin → 聚合 `DataRequirement`
> 2. `any(needs_astro)` → 获取天文数据，写入 `DataContext.sun_events/moon_status`
> 3. 若本地天气全天恶劣（降水高+能见度低）且有 L2 需求 → 跳过 Phase 2（节省 API）
> 4. `any(needs_l2_target)` → 获取目标天气，写入 `DataContext.target_weather`
> 5. `any(needs_l2_light_path)` → 获取光路天气，写入 `DataContext.light_path_weather`
> 6. 构建完成后，将同一个 `DataContext` 传入每个 Plugin

### ScorerPlugin — 评分器接口

```python
class ScorerPlugin(Protocol):
    """可插拔评分器契约"""
    
    @property
    def event_type(self) -> str:
        """事件类型标识，如 'cloud_sea'"""
        ...
    
    @property
    def display_name(self) -> str:
        """显示名称，如 '云海'"""
        ...
    
    @property
    def data_requirement(self) -> DataRequirement:
        """声明数据需求"""
        ...
    
    def score(self, context: DataContext) -> ScoreResult | None:
        """基于共享数据上下文计算评分
        
        内含触发判定逻辑：若条件不满足则返回 None (等价于原 check_trigger=False)。
        
        Args:
            context: 共享数据上下文，包含所有已获取的天气/天文数据
        Returns:
            ScoreResult 包含总分、状态、各维度明细；None 表示未触发
        """
        ...
    
    def dimensions(self) -> list[str]:
        """返回评分维度名称列表"""
        ...
```

### Scheduler 调度流程

```python
# capability → event_type 映射表
# capabilities 使用缩写 (如 "sunrise")，Plugin 使用完整名 (如 "sunrise_golden_mountain")
_CAPABILITY_EVENT_MAP: dict[str, list[str]] = {
    "sunrise": ["sunrise_golden_mountain"],
    "sunset":  ["sunset_golden_mountain"],
    "stargazing": ["stargazing"],
    "cloud_sea":  ["cloud_sea"],
    "frost":      ["frost"],
    "snow_tree":  ["snow_tree"],
    "ice_icicle": ["ice_icicle"],
}

# 伪代码：Scheduler 的 Plugin 驱动调度
def run_day(self, viewpoint: Viewpoint, date: date, 
            events_filter: list[str] | None = None) -> list[ScoreResult]:
    
    # 1. 收集活跃 Plugin (通过映射表将 capabilities 展开为 event_type 集合)
    allowed_event_types: set[str] = set()
    for cap in viewpoint.capabilities:
        mapped = _CAPABILITY_EVENT_MAP.get(cap, [cap])
        allowed_event_types.update(mapped)
    
    active_plugins = []
    for plugin in self.score_engine.all_plugins():
        if plugin.event_type not in allowed_event_types:
            continue
        if events_filter and plugin.event_type not in events_filter:
            continue
        if plugin.data_requirement.season_months:
            if date.month not in plugin.data_requirement.season_months:
                continue
        active_plugins.append(plugin)
    
    # 2. 聚合数据需求
    need_astro = any(p.data_requirement.needs_astro for p in active_plugins)
    need_l2_target = any(p.data_requirement.needs_l2_target for p in active_plugins)
    need_l2_light = any(p.data_requirement.needs_l2_light_path for p in active_plugins)
    
    # 3. Phase 1: 获取本地天气 (始终获取)
    local_weather = self.fetcher.fetch_hourly(viewpoint.location, days=days)
    
    # 4. 构建 DataContext (逐步填充)
    ctx = DataContext(date=date, viewpoint=viewpoint, local_weather=local_weather)
    
    if need_astro:
        ctx.sun_events = self.astro.get_sun_events(...)
        ctx.moon_status = self.astro.get_moon_status(...)
        ctx.stargazing_window = self.astro.determine_stargazing_window(...)
    
    # 5. Phase 2: 按需获取远程数据 (含简单天气预检)
    if need_l2_target or need_l2_light:
        # 优化：若全天天气极端恶劣，跳过远程调用节省 API 配额
        any_viable = any(
            row.precipitation_probability < 50 or row.visibility > 1000
            for _, row in local_weather.iterrows()
        )
        if any_viable:
            if need_l2_target:
                ctx.target_weather = self._fetch_target_weather(viewpoint.targets)
            if need_l2_light:
                ctx.light_path_weather = self._fetch_light_path_weather(...)
    
    # 6. 遍历评分 (Plugin 内含触发判定 + 安全检查，返回 None 表示未触发)
    results = []
    for plugin in active_plugins:
        result = plugin.score(ctx)
        if result is not None:
            results.append(result)
    
    return results
```

---

## 3.3 六个 Plugin 的 DataRequirement 总览

| Plugin | `event_type` | `needs_l2_target` | `needs_l2_light_path` | `needs_astro` | `past_hours` | `season_months` | `score()` 内触发条件 |
|--------|-------------|:-:|:-:|:-:|:-:|:-:|------|
| GoldenMountainPlugin | `sunrise_golden_mountain` / `sunset_golden_mountain` | ✅ | ✅ | ✅ | 0 | `None` (全年) | 总云量 < 80% 且有匹配 Target |
| StargazingPlugin | `stargazing` | ❌ | ❌ | ✅ | 0 | `None` (全年) | 夜间总云量 < 70% |
| CloudSeaPlugin | `cloud_sea` | ❌ | ❌ | ❌ | 0 | `None` (全年) | 云底高度 < 站点海拔 |
| FrostPlugin | `frost` | ❌ | ❌ | ❌ | 0 | `None` (全年) | 温度 < 2°C |
| SnowTreePlugin | `snow_tree` | ❌ | ❌ | ❌ | **24** | `None` (全年, 预留) | 近12小时有降雪，或近24小时大雪+持续低温留存，且当前晴朗 |
| IceIciclePlugin | `ice_icicle` | ❌ | ❌ | ❌ | **24** | `None` (全年, 预留) | 近12小时有有效水源并已冻结，或近24小时强水源+持续低温留存 |

---

## 3.4 通用评分原则

所有 Plugin 评分均为 **0-100 分制**，分值对应建议等级：

| 分数段 | 等级 | 含义 |
|-------|------|------|
| **95-100** | `Perfect` | 完美条件 |
| **80-94** | `Recommended` | 推荐出行，条件优良 |
| **50-79** | `Possible` | 可能可见，存在风险 |
| **0-49** | `Not Recommended` | 不推荐 |

**Plugin 自主安全检查**: 每个 Plugin 在 `score()` 内部自行检查其关注时段的天气安全条件（降水概率、能见度等），仅使用通过检查的时段做评分。例如 CloudSeaPlugin 关注 06:00-09:00，若 08:00 降水概率 > 50%，则仅基于 06:00、07:00、09:00 评分。

> [!NOTE]
> **Phase 2 优化**：因当前仅 GoldenMountainPlugin 需要 L2 远程数据（其他 Plugin 均基于本地数据评分），Scheduler 在全天天气极端恶劣时可跳过 Phase 2 远程 API 调用以节省配额。

> [!NOTE]
> **评分阈值可配置**：文档中展示的阈值和得分为默认参考值，实际运行时由 `engine_config.yaml` 加载。

---

## 3.5 GoldenMountainPlugin — 日照金山

### 基本信息

```python
class GoldenMountainPlugin:
    """日照金山评分器 — 通过构造函数指定 sunrise/sunset 模式"""
    display_name = "日照金山"
    data_requirement = DataRequirement(
        needs_l2_target=True,
        needs_l2_light_path=True,
        needs_astro=True,
    )
    
    def __init__(self, event_type: str = "sunrise_golden_mountain") -> None:
        self._event_type = event_type  # "sunrise_golden_mountain" 或 "sunset_golden_mountain"
    
    @property
    def event_type(self) -> str:
        return self._event_type
```

> [!TIP]
> **双实例注册**: 需分别创建 sunrise 和 sunset 两个实例并注册到 ScoreEngine（见 §3.11）。

### 触发条件 (内置于 score())

`score()` 内部首先检查触发条件，不满足则返回 `None`：
- 总云量 ≥ 80% → 返回 `None`
- 观景台无匹配 Target → 返回 `None`
- L2 数据获取后，Plugin 自行进行目标可见性和光路通畅度分析

> [!NOTE]
> GoldenMountainPlugin 内含 L2 分析逻辑（目标可见性检查 + 光路通畅度计算），
> 无需外部 Analyzer 组件。

### 评分模型

**公式**:
$$ Score = S_{light} + S_{target} + S_{local} $$

**评分维度与阶梯**:

| 维度 | 满分 | 评分阶梯 |
|------|------|---------|
| **光路通畅** ($S_{light}$) | 35 | 10点均值云量 ≤10%: 35 · 10-20%: 30 · 20-30%: 20 · 30-50%: 10 · >50%: 0 |
| **目标可见** ($S_{target}$) | 40 | Primary目标高+中云 ≤10%: 40 · ≤20%: 35 · ≤30%: 25 · ≤50%: 10 · >50%: 0 |
| **本地通透** ($S_{local}$) | 25 | 总云量 ≤15%: 25 · ≤30%: 20 · ≤50%: 10 · >50%: 0 |

> [!IMPORTANT]
> **维度一票否决**: 任一维度得分过低时直接否决：
> - $S_{light} = 0$（光路完全被挡）→ 总分置 0
> - $S_{target} = 0$（目标完全不可见）→ 总分置 0
> - $S_{local} = 0$（本地浓云密布）→ 总分置 0

> [!NOTE]
> **光路检查**: 沿日出/日落方位角方向设置检查点（默认每 `light_path.interval_km`=10km 一个，共 `light_path.count`=10 个，即 10km~100km），取所有点 (low_cloud + mid_cloud) 的算术平均值作为光路云量。检查点数量和间隔均通过 `engine_config.yaml` 配置。

### 评分示例

以牛背山→贡嘎 2026-02-11 日出为例：

```python
golden_score = {
    "event_type": "sunrise_golden_mountain",
    "time_window": "07:15 - 07:45",
    "score_breakdown": {
        "light_path":     {"score": 35, "max": 35, "detail": "10点均值云量8%, ≤10%满分"},
        "target_visible": {"score": 35, "max": 40, "detail": "贡嘎高+中云13%, ≤20%区间"},
        "local_clear":    {"score": 20, "max": 25, "detail": "本地总云22%, ≤30%区间"},
    },
    "total_score": 90,   # 35+35+20 = 90
    "status": "Recommended",
    "confidence": "High",
    "highlights": ["贡嘎金山"],
    "warnings": ["雅拉神山被遮挡(secondary, 不影响评分)"],
}
```

---

## 3.6 StargazingPlugin — 观星

### 基本信息

```python
class StargazingPlugin:
    event_type = "stargazing"
    display_name = "观星"
    data_requirement = DataRequirement(
        needs_astro=True,  # 需要月相、月出月落、天文晨暮曦
    )
```

### 触发条件 (内置于 score())

`score()` 内部首先检查：夜间总云量 ≥ 70% 时返回 `None`。

### 时间窗口判定

| 优先级 | 条件 | 时间窗口 | 品质 |
|--------|------|---------|------|
| 🥇 最佳 | 月亮在地平线下 | `max(天文暮曦, 月落)` → `min(天文晨曦, 月出)` | `optimal` |
| 🥈 次佳 | 月相 < 50%（非满月/半月以上） | `天文暮曦` → `天文晨曦` | `good` |
| 🥉 一般 | 月相 ≥ 50% 但有月下时段 | `月落` → `天文晨曦`（若月落在夜间） | `partial` |
| ❌ 不佳 | 满月整夜照耀 | 无优质窗口 | `poor` |

### 评分模型

**公式**:
$$ Score = Base - Deduction_{cloud} - Deduction_{wind} $$

| 维度 | 规则 |
|------|------|
| **基准分 (Base)** | optimal: 100 · good: 90 · partial: 70 · poor: 100 - phase×0.8 |
| **云量扣分** | $Deduction_{cloud} = TotalCloudCover\\% \times 0.8$ |
| **风速扣分** | wind > 40km/h: -30 · > 20km/h: -10 · ≤20: 0 (影响长曝光) |

### 评分示例

```python
stargazing_score = {
    "event_type": "stargazing",
    "time_window": "19:55 - 03:15",
    "secondary_window": "03:15 - 05:55",
    "score_breakdown": {
        "base":  {"score": 100, "max": 100, "detail": "optimal: 月落13:40→完美暗夜至03:15月出"},
        "cloud": {"score":  -2, "max": 0,   "detail": "夜间平均云量3%, 扣2.4→2"},
        "wind":  {"score":   0, "max": 0,   "detail": "2.8km/h ≤20, 无扣分"},
    },
    "total_score": 98,
    "status": "Perfect",
    "confidence": "High",
}
```

---

## 3.7 CloudSeaPlugin — 云海

### 基本信息

```python
class CloudSeaPlugin:
    event_type = "cloud_sea"
    display_name = "云海"
    data_requirement = DataRequirement()  # 仅需 L1 本地天气，无特殊需求
```

### 触发条件 (内置于 score())

`score()` 内部首先检查：云底高度 ≥ 站点海拔时返回 `None`。
Plugin 自行从 `DataContext.local_weather` 和 `DataContext.viewpoint.location.altitude` 计算高差。

### 评分模型

仅当 `CloudBase < SiteAltitude` 时触发评分。

鉴于川西高海拔站点较少，湿度数据可能不准，我们引入 **中云（Mid Level Clouds）** 作为修正因子。若低云满而中云也厚，往往意味着云层极厚或处于云雾大混沌中（人在云中），而非人在云上。

$$ Score = (Score_{gap} + Score_{density}) \times Factor_{mid\_cloud} + Score_{wind} $$

| 维度 | 满分 | 评分阶梯 |
|------|------|---------|
| **高差** ($Score_{gap}$) | 50 | Gap > 800m: 50 · > 500m: 40 · > 200m: 20 · > 0m: 10 |
| **密度** ($Score_{density}$) | 30 | LowCloud >80%: 30 · >50%: 20 · >30%: 10 · ≤30%: 5 (碎云) |
| **中云修正** ($Factor_{mid}$) | x | MidCloud ≤30%: 1.0 (云层分界清晰) · 30-60%: 0.7 (云层较厚) · >60%: 0.3 (大概率在大雾中) |
| **稳定** ($Score_{wind}$) | 20 | Wind <3km/h: 20 · <5km/h: 15 · <8km/h: 10 · ≥8km/h: 5 |

### 评分示例

```python
cloud_sea_score = {
    "event_type": "cloud_sea",
    "time_window": "06:00 - 09:00",
    "score_breakdown": {
        "gap":     {"score": 50, "max": 50, "detail": "高差1060m > 800m, 壮观云海"},
        "density": {"score": 20, "max": 30, "detail": "低云75%, >50%档位"},
        "mid_structure": {"factor": 1.0, "detail": "中云5%, 上层通透, 层次分明"},
        "wind":    {"score": 20, "max": 20, "detail": "风速2.8km/h, 极静"},
    },
    "total_score": 90,   # (50+20)×1.0+20 = 90
    "status": "Recommended",
    "confidence": "High",
}
```

---

## 3.8 FrostPlugin — 雾凇

### 基本信息

```python
class FrostPlugin:
    event_type = "frost"
    display_name = "雾凇"
    data_requirement = DataRequirement()  # 仅需 L1 本地天气
```

### 触发条件 (内置于 score())

`score()` 内部首先检查：温度 ≥ 2°C 时返回 `None`。
Plugin 自行从 `DataContext.local_weather` 提取温度序列。

### 评分模型

仅当 `温度 < 2°C` 时触发评分。雾凇最佳观赏时段为**日出前 2-3 小时至日出后 1 小时**。

$$ Score = Score_{temp} + Score_{moisture} + Score_{wind} + Score_{cloud} $$

| 维度 | 满分 | 评分阶梯 |
|------|------|---------|
| **温度适宜** ($Score_{temp}$) | 40 | -5°C ≤ T < 0°C: 40 · -10°C ≤ T < -5°C: 30 · 0°C ≤ T ≤ 2°C: 25 · T < -10°C: 15 |
| **湿度条件** ($Score_{moisture}$) | 30 | 能见度 < 5km: 30 (雾气充沛) · < 10km: 20 · < 20km: 10 · ≥ 20km: 5 (空气干燥) |
| **风速稳定** ($Score_{wind}$) | 20 | Wind < 3km/h: 20 · < 5km/h: 15 · < 10km/h: 10 · ≥ 10km/h: 0 |
| **云况适宜** ($Score_{cloud}$) | 10 | LowCloud 30-60%: 10 (适度低云保温) · < 30%: 5 (晴空辐射冷却) · > 60%: 3 |

> [!TIP]
> **雾凇形成条件**: 低温（冰点以下）+ 高湿（能见度低/雾气）+ 微风（利于凝结）+ 适度云量（保温但不降水）。

### 评分示例

```python
frost_score = {
    "event_type": "frost",
    "time_window": "05:00 - 08:30",
    "score_breakdown": {
        "temperature": {"score": 40, "max": 40, "detail": "-3.8°C, 在[-5,0)区间满分"},
        "moisture":    {"score":  5, "max": 30, "detail": "能见度35km, ≥20km空气干燥"},
        "wind":        {"score": 20, "max": 20, "detail": "2.8km/h < 3km/h, 理想"},
        "cloud":       {"score":  7, "max": 10, "detail": "低云75%, >60%略重"},
    },
    "total_score": 72,   # 40+5+20+7 = 72
    "status": "Possible",
    "confidence": "High",
    "note": "温度理想但空气干燥，雾凇形成概率较低",
}
```

---

## 3.9 SnowTreePlugin — 树挂积雪

### 基本信息

```python
class SnowTreePlugin:
    event_type = "snow_tree"
    display_name = "树挂积雪"
    data_requirement = DataRequirement(past_hours=24)  # 需要过去24h本地天气
```

### 数据来源约束（Open-Meteo）

`SnowTreePlugin` 不依赖不存在的 `tree_snow_present` 字段，而是基于可用天气字段推断“树上仍有可见积雪”：

- `hourly.snowfall`：过去每小时降雪量（cm）
- `hourly.temperature_2m`：降雪期与降雪后的低温保持能力
- `hourly.weather_code` + `hourly.cloud_cover` + `hourly.precipitation_probability`：当前是否晴朗
- `hourly.wind_speed_10m`：树冠积雪稳定性
- `past_hours`：建议至少拉取过去 24 小时序列，用于计算"距今时间 + 留存条件"

> [!IMPORTANT]
> **past_hours 数据获取策略**:
> - **D+2 ~ D+N**: Open-Meteo Forecast API 返回逐小时数据 (D+1 00:00 ~ D+N 00:00)，D+2 的 past_24h = D+1 的 00:00-23:00 数据，已在 API 响应中
> - **D+1**: past_24h = 今天 00:00 之前的数据：
>   1. 优先从 SQLite `weather_cache` 查询（之前运行可能已缓存）
>   2. 若无缓存，通过 Forecast API `past_days=1` 参数获取”

派生指标（Plugin 内部计算）：

- `recent_snowfall_12h_cm`
- `recent_snowfall_24h_cm`
- `hours_since_last_snow`
- `snowfall_duration_h_24h`（24h 内降雪小时数）
- `subzero_hours_since_last_snow`
- `max_temp_since_last_snow`
- `max_wind_since_last_snow` (新增)：降雪后出现过的最大阵风
- `sunshine_hours_since_snow` (新增)：降雪后经历的日照时数（按云量加权）

### 触发条件 (内置于 score())

`score()` 内部首先从 `DataContext.local_weather` 计算以下派生指标，再判定触发条件。
不满足时返回 `None`。

**派生指标计算** (Plugin 内部):
- `recent_snowfall_12h_cm` / `recent_snowfall_24h_cm`
- `hours_since_last_snow`
- `snowfall_duration_h_24h`
- `subzero_hours_since_last_snow` / `max_temp_since_last_snow`
- `max_wind_since_last_snow` / `sunshine_hours_since_snow`

**触发路径** (降雪门槛适度放松):
- **常规路径**: 近 12 小时有雪 (≥0.2cm) 且当前晴朗
- **留存路径**: 近 24 小时大雪 (≥1.5cm) + 降雪时段≥3h + 持续低温≥8h + 最高温≤1.5°C
- 未满足任一路径 → 返回 `None`

### 评分模型

$$ Score = Score_{snow} + Score_{clear} + Score_{stable} - Deduction_{age} - Deduction_{temp} - Deduction_{sun} - Deduction_{history\_wind} $$

| 维度 | 满分 | 评分阶梯 |
|------|------|---------|
| **积雪信号** ($Score_{snow}$) | 60 | `recent_snowfall_24h_cm ≥2.5` 且 `snowfall_duration_h_24h≥4`: 60 · ≥1.5且≥3: 52 · ≥0.8且≥2: 44 · ≥0.2: 32 |
| **晴朗程度** ($Score_{clear}$) | 20 | `weather_code=0`且云量≤20%: 20 · `weather_code∈{1,2}`且云量≤45%: 16 · 其他: 8 |
| **稳定保持** ($Score_{stable}$) | 20 | **Current Wind** <12km/h: 20 · <20km/h: 14 · ≥20km/h: 8 (拍摄时刻风速) |

| 扣分项 | 扣分规则 |
|--------|---------|
| **降雪距今扣分** ($Deduction_{age}$) | `hours_since_last_snow` ≤3h: 0 · ≤8h: 2 · ≤12h: 5 · ≤16h: 8 · ≤20h: 12 · >20h: 20 |
| **升温融化扣分** ($Deduction_{temp}$) | `max_temp_since_last_snow` ≤-2°C: 0 · ≤-0.5°C: 2 · ≤1°C: 6 · ≤2.5°C: 12 · >2.5°C: 22 |
| **累积日照扣分** ($Deduction_{sun}$) | **Accumulated Sun Energy**: 每小时晴朗(Clouds<30%)+1分, 强晒(Clouds<10%)+2分。累计 >2: -5分, >5: -15分, >8: -30分 (烈日杀手) |
| **历史大风扣分** ($Deduction_{wind}$) | **Max Wind Since Snow**: >30km/h (劲风): -20分 · >50km/h (狂风): -50分 (直接吹秃) |

> [!TIP]
> **树挂积雪留存逻辑**:
> 1. **日照杀伤**: 即使气温 < 0°C，高原强烈的紫外线直射也会迅速融化树梢积雪。晴朗对于“拍照”是加分，但对“积雪留存”是重大减分。
> 2. **风力摧毁**: 30km/h (5级风) 是分界线，新雪很松，一阵大风即可吹散。此处采用 `max_wind_since_last_snow` 而非当前风速。

### 评分示例

**场景：昨晚20:00停雪，今日15:00（距停雪19h），全天暴晒，气温回升至2°C**

```python
snow_tree_score = {
    "event_type": "snow_tree",
    "time_window": "15:00 - 16:00",
    "score_breakdown": {
        "snow_signal":   {"score": 60, "max": 60, "detail": "昨晚大雪累计3.0cm"},
        "clear_weather": {"score": 20, "max": 20, "detail": "当前万里无云"},
        "stability":     {"score": 20, "max": 20, "detail": "当前微风 5km/h"},
        "age_deduction": {"score":-12, "max": 0, "detail": "距停雪19h"},
        "temp_deduction":{"score":-12, "max": 0, "detail": "最高温曾达 2.1°C"},
        "sun_deduction": {"score":-30, "max": 0, "detail": "累积暴晒8小时，严重融化"},
        "wind_deduction":{"score":  0, "max": 0, "detail": "历史最大风速 15km/h"},
    },
    "total_score": 46, # 60+20+20 -12-12-30 = 46
    "status": "Not Recommended", 
    "confidence": "High",
    "note": "虽然从不下雪到现在一直晴朗，但长时间暴晒加微热，树挂大概率已无存",
}
```

---

## 3.10 IceIciclePlugin — 冰挂

### 基本信息

```python
class IceIciclePlugin:
    event_type = "ice_icicle"
    display_name = "冰挂"
    data_requirement = DataRequirement(past_hours=24)  # 需要过去24h本地天气
```

### 数据来源约束（Open-Meteo）

`IceIciclePlugin` 同样采用可用字段推断，不依赖直接“冰挂存在”观测：

- `hourly.rain` + `hourly.showers` + `hourly.snowfall`：有效水源输入
- `hourly.temperature_2m`：冻结/融化过程
- `hourly.weather_code` + `hourly.cloud_cover` + `hourly.precipitation_probability`：当前观赏天气
- `hourly.wind_speed_10m`：冰挂稳定性
- `past_hours`：建议至少 24 小时，用于估计形成与留存

> [!IMPORTANT]
> **past_hours 数据获取策略**:
> - **D+2 ~ D+N**: Forecast API 响应已包含前一天逐小时数据，可直接使用
> - **D+1**: 优先查 SQLite `weather_cache`，若无缓存则通过 `past_days=1` 获取

派生指标（Plugin 内部计算）：

- `effective_water_input_12h_mm`（`rain+showers` 加雪量换算水当量）
- `effective_water_input_24h_mm`
- `hours_since_last_water_input`
- `subzero_hours_since_last_water`
- `max_temp_since_last_water`

### 触发条件

冰挂触发采用“常规 + 留存”双路径，与树挂积雪一致地放宽到 12 小时以上可留存场景。


### 评分模型

$$ Score = Score_{water} + Score_{freeze} + Score_{view} - Deduction_{age} - Deduction_{temp} $$

| 维度 | 满分 | 评分阶梯 |
|------|------|---------|
| **水源输入** ($Score_{water}$) | 50 | `effective_water_input_24h≥3.0mm`: 50 · ≥2.0: 42 · ≥1.0: 34 · ≥0.4: 24 |
| **冻结强度** ($Score_{freeze}$) | 30 | `subzero_hours_since_last_water≥14`且`temp_now≤-3°C`: 30 · ≥10且`temp_now≤-1°C`: 24 · ≥6且`temp_now≤0°C`: 16 · 其他: 10 |
| **观赏条件** ($Score_{view}$) | 20 | 云量≤20%且风速<12km/h: 20 · 云量≤45%且风速<20: 14 · 其他: 8 |

| 扣分项 | 扣分规则 |
|--------|---------|
| **水源距今扣分** ($Deduction_{age}$) | `hours_since_last_water_input` ≤3h: 0 · ≤8h: 2 · ≤12h: 5 · ≤16h: 8 · ≤20h: 12 · >20h: 20 |
| **升温融化扣分** ($Deduction_{temp}$) | `max_temp_since_last_water` ≤-2°C: 0 · ≤-0.5°C: 2 · ≤1°C: 6 · ≤2.5°C: 12 · >2.5°C: 22 |

> [!TIP]
> **冰挂留存逻辑**: 只要前段时间有足够水源并完成冻结，且之后持续低温，即使超过 12 小时仍可能保持较好观感。

### 评分示例

```python
ice_icicle_score = {
    "event_type": "ice_icicle",
    "time_window": "08:30 - 12:30",
    "score_breakdown": {
        "water_input":   {"score": 42, "max": 50, "detail": "24小时有效水源约2.3mm"},
        "freeze_strength":{"score": 24, "max": 30, "detail": "冻结时长11小时, 当前-1.8°C"},
        "view_quality":  {"score": 14, "max": 20, "detail": "云量28%, 风速14km/h"},
        "age_deduction": {"score": -8, "max": 0, "detail": "最近有效水源距今约15小时"},
        "temp_deduction":{"score": -2, "max": 0, "detail": "期间最高温-0.3°C, 融化风险较低"},
    },
    "total_score": 70,
    "status": "Possible",
    "confidence": "Medium",
    "note": "冰挂仍可见，但水源已过峰值，后续主要依赖低温留存",
}
```

---

## 3.11 ScoreEngine — Plugin 注册中心

```python
class ScoreEngine:
    """Plugin 注册中心"""
    
    def __init__(self):
        self._plugins: dict[str, ScorerPlugin] = {}
    
    def register(self, plugin: ScorerPlugin) -> None:
        """注册一个评分器 Plugin"""
        self._plugins[plugin.event_type] = plugin
    
    def all_plugins(self) -> list[ScorerPlugin]:
        """返回所有已注册的 Plugin"""
        return list(self._plugins.values())
    
    def get(self, event_type: str) -> ScorerPlugin | None:
        """按事件类型获取 Plugin"""
        return self._plugins.get(event_type)
    
    def collect_requirements(self, 
                             plugins: list[ScorerPlugin]) -> DataRequirement:
        """聚合多个 Plugin 的数据需求"""
        return DataRequirement(
            needs_l2_target=any(p.data_requirement.needs_l2_target for p in plugins),
            needs_l2_light_path=any(p.data_requirement.needs_l2_light_path for p in plugins),
            needs_astro=any(p.data_requirement.needs_astro for p in plugins),
            past_hours=max((p.data_requirement.past_hours for p in plugins), default=0),
        )

# 初始化注册
engine = ScoreEngine()
engine.register(GoldenMountainPlugin("sunrise_golden_mountain"))  # 日出金山
engine.register(GoldenMountainPlugin("sunset_golden_mountain"))   # 日落金山
engine.register(StargazingPlugin())
engine.register(CloudSeaPlugin())
engine.register(FrostPlugin())
engine.register(SnowTreePlugin())
engine.register(IceIciclePlugin())
# 未来扩展: engine.register(AutumnFoliagePlugin())
```
