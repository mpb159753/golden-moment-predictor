# M09B: FrostPlugin — 雾凇评分

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现雾凇评分 Plugin，仅需 L1 本地天气数据。

**依赖模块:** M08 (ScoreEngine + DataContext + Plugin 接口)

**可并行:** M09A, M09C, M09D (各 Plugin 相互独立，无依赖关系)

---

## 背景

FrostPlugin 是 L1 Plugin，仅需 `DataContext.local_weather`（本地天气）。当温度低于触发阈值时，综合评估温度、湿度、风速和云量来判定雾凇形成概率。

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

## Task 1: FrostPlugin 实现

**Files:**
- Create: `gmp/scoring/plugins/frost.py`
- Test: `tests/unit/test_plugin_frost.py`

### 配置参数 (来自 `engine_config.yaml → scoring.frost`)

```yaml
frost:
  trigger: { max_temperature: 2.0 }
  weights: { temperature: 40, moisture: 30, wind: 20, cloud: 10 }
  thresholds:
    temp_ranges:
      optimal: {range: [-5, 0], score: 40}
      good: {range: [-10, -5], score: 30}
      acceptable: {range: [0, 2], score: 25}
      bad: {range: [-999, -10], score: 15}
    visibility_km: [5, 10, 20]               # <5=30, <10=20, <20=10, ≥20=5
    wind_speed: [3, 5, 10]                   # <3=20, <5=15, <10=10, ≥10=0
    cloud_pct:
      optimal: {range: [30, 60], score: 10}
      clear: {range: [0, 30], score: 5}
      heavy: {range: [60, 100], score: 3}
```

### 评分逻辑

1. **触发判定**: 温度 < `trigger.max_temperature` → 触发
2. **评分公式**: `Score = Score_temp + Score_moisture + Score_wind + Score_cloud`
3. **维度**: `["temperature", "moisture", "wind", "cloud"]`

### 应测试的内容

- 温度 ≥ 2°C → 返回 None
- -3.8°C, 能见度 35km, 风 2.8km/h, 低云 75% → score≈72
- -3°C, 能见度 3km (雾气充沛), 风 1km/h, 低云 45% → score≥90
- 各温度区间正确映射
- 各能见度区间正确映射
- 风速 ≥ 10km/h → wind 维度 0 分
- 安全检查: 降水 > 阈值 → 剔除

---

## 验证命令

```bash
python -m pytest tests/unit/test_plugin_frost.py -v
```
