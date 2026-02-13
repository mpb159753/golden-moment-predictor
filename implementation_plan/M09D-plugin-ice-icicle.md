# M09D: IceIciclePlugin — 冰挂评分

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现冰挂评分 Plugin，需要 L1 本地天气数据 + 过去 24 小时历史数据。

**依赖模块:** M08 (ScoreEngine + DataContext + Plugin 接口)

**可并行:** M09A, M09B, M09C (各 Plugin 相互独立，无依赖关系)

---

## 背景

IceIciclePlugin 是 L1 Plugin，使用 `DataContext.local_weather`（含过去24h历史），评估冰挂形成条件。需要计算有效水源输入（雨+雪转水当量）、冻结强度和观赏通透性。

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

## Task 1: IceIciclePlugin 实现

**Files:**
- Create: `gmp/scoring/plugins/ice_icicle.py`
- Test: `tests/unit/test_plugin_ice_icicle.py`

### 配置参数 (来自 `engine_config.yaml → scoring.ice_icicle`)

```yaml
ice_icicle:
  trigger:
    recent_path: { min_water_12h_mm: 0.4 }
    retention_path: { min_water_24h_mm: 1.0, min_subzero_hours: 6, max_temp: 1.5 }
  weights: { water_input: 50, freeze_strength: 30, view_quality: 20 }
  thresholds:
    water_input: [...]
    freeze_strength: [...]
    view_quality: [...]
  deductions:
    age: [...]
    temp: [...]
  past_hours: 24
```

### 数据需求

```python
data_requirement = DataRequirement(past_hours=24)
```

### 派生指标

- `effective_water_input_12h_mm` (`rain+showers` + 雪转水当量)
- `effective_water_input_24h_mm`
- `hours_since_last_water_input`
- `subzero_hours_since_last_water`
- `max_temp_since_last_water`

### 评分公式

`Score = Score_water + Score_freeze + Score_view - Deduction_age - Deduction_temp`

### 应测试的内容

- 近期无有效水源 → 返回 None
- 水源 2.3mm, 冻结 11h, -1.8°C → score≈70
- 各维度阶梯验证
- 扣分项验证
- 雪转水当量计算正确

---

## 验证命令

```bash
python -m pytest tests/unit/test_plugin_ice_icicle.py -v
```
