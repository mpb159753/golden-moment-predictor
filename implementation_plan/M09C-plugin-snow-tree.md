# M09C: SnowTreePlugin — 树挂积雪评分

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现树挂积雪评分 Plugin，需要 L1 本地天气数据 + 过去 24 小时历史数据。

**依赖模块:** M08 (ScoreEngine + DataContext + Plugin 接口)

**可并行:** M09A, M09B, M09D (各 Plugin 相互独立，无依赖关系)

---

## 背景

SnowTreePlugin 是 L1 Plugin，使用 `DataContext.local_weather`（含过去24h历史），通过分析近期降雪量、降雪持续时长、冰冻时间等派生指标，评估树挂积雪的观赏条件。评分模型包含双触发路径（常规/留存）和多项扣分机制。

### Plugin 通用结构

```python
class XxxPlugin:
    def __init__(self, config: dict):
        """config 来自 ConfigManager.get_plugin_config(event_type)"""
        self._config = config

    @property
    def event_type(self) -> str: ...
    @property
    def display_name(self) -> str: ...
    @property
    def data_requirement(self) -> DataRequirement: ...

    def score(self, context: DataContext) -> ScoreResult | None:
        """
        1. 安全检查 (关注时段的降水/能见度)
        2. 触发判定 (不满足则 return None)
        3. 计算评分
        4. 返回 ScoreResult
        """

    def dimensions(self) -> list[str]:
        """返回评分维度名称列表"""
```

### 安全检查通用逻辑

每个 Plugin 在 `score()` 中自行检查关注时段的天气安全条件：
- 若该时段 `precipitation_probability > safety.precip_threshold`，剔除该时段数据
- 若该时段 `visibility < safety.visibility_threshold`，剔除该时段数据
- 仅使用通过安全检查的时段做评分

安全阈值从配置中获取 (`safety.precip_threshold`, `safety.visibility_threshold`)。

---

## Task 1: SnowTreePlugin 实现

**Files:**
- Create: `gmp/scoring/plugins/snow_tree.py`
- Test: `tests/unit/test_plugin_snow_tree.py`

### 配置参数 (来自 `engine_config.yaml → scoring.snow_tree`)

```yaml
snow_tree:
  trigger:
    recent_path: { min_snowfall_12h_cm: 0.2 }
    retention_path: { min_snowfall_24h_cm: 1.5, min_duration_h: 3, min_subzero_hours: 8, max_temp: 1.5 }
  weights: { snow_signal: 60, clear_weather: 20, stability: 20 }
  thresholds:
    snow_signal:
      - {snowfall: 2.5, duration: 4, score: 60}
      - {snowfall: 1.5, duration: 3, score: 52}
      - {snowfall: 0.8, duration: 2, score: 44}
      - {snowfall: 0.2, duration: 0, score: 32}
    clear_weather:
      - {weather_code: [0], max_cloud: 20, score: 20}
      - {weather_code: [1, 2], max_cloud: 45, score: 16}
      - {score: 8}
    stability_wind: [12, 20]                 # <12=20, <20=14, ≥20=8
  deductions:
    age: [{hours: 3, deduction: 0}, {hours: 8, deduction: 2}, ...]
    temp: [{temp: -2, deduction: 0}, {temp: -0.5, deduction: 2}, ...]
    sun: [{sun_score: 2, deduction: 0}, {sun_score: 5, deduction: 15}, {sun_score: 8, deduction: 30}]
    wind_severe_threshold: 50                # >50km/h=-50
    wind_moderate_threshold: 30              # >30km/h=-20
  past_hours: 24
```

### 数据需求

```python
data_requirement = DataRequirement(past_hours=24)
```

### 派生指标 (Plugin 内部从 `local_weather` 计算)

- `recent_snowfall_12h_cm` / `recent_snowfall_24h_cm`
- `hours_since_last_snow`
- `snowfall_duration_h_24h`
- `subzero_hours_since_last_snow` / `max_temp_since_last_snow`
- `max_wind_since_last_snow`
- `sunshine_hours_since_snow` (按云量加权)

### 触发路径

- **常规路径**: 近 12h 降雪 ≥ `min_snowfall_12h_cm` + 当前晴朗
- **留存路径**: 近 24h 降雪 ≥ 大雪阈值 + 持续低温 + 时长足够
- 均不满足 → None

### 评分公式

`Score = Score_snow + Score_clear + Score_stable - Deduction_age - Deduction_temp - Deduction_sun - Deduction_wind`

### 应测试的内容

- 近期无降雪 → 返回 None
- 近 12h 雪 0.5cm, 距今 6h, 晴 → 触发常规路径, score≥70
- 大雪 3cm, 距今 19h, 暴晒 8h → 触发留存路径, score≈46
- 各扣分项独立验证
- 历史大风 >50km/h → 大幅扣分
- 累积日照扣分验证
- `past_hours=24` 数据需求正确

---

## 验证命令

```bash
python -m pytest tests/unit/test_plugin_snow_tree.py -v
```
