# M10B: StargazingPlugin — 观星

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现观星评分 Plugin，基于月相、云量、风速等天文气象数据计算观星条件评分。

**依赖模块:** M04 (AstroUtils), M08 (ScoreEngine + DataContext)

---

## 背景

StargazingPlugin 是 L2 级别 Plugin，需要天文数据 (`needs_astro`)，用于月相和观星窗口判定。
数据已由 Scheduler 提前获取并填入 `DataContext`，Plugin 从 context 中直接读取。

---

## Task 1: StargazingPlugin 实现

**Files:**
- Create: `gmp/scoring/plugins/stargazing.py`
- Test: `tests/unit/test_plugin_stargazing.py`

### 配置参数 (来自 `engine_config.yaml → scoring.stargazing`)

```yaml
stargazing:
  trigger:
    max_night_cloud_cover: 70              # 夜间总云量 ≥ 70% 时未触发
  base_optimal: 100
  base_good: 90
  base_partial: 70
  cloud_penalty_factor: 0.8                # Deduction = TotalCloud% × factor
  wind_thresholds:
    severe: {speed: 40, penalty: 30}       # >40km/h: -30
    moderate: {speed: 20, penalty: 10}     # >20km/h: -10
```

### 评分逻辑

```python
class StargazingPlugin:
    def __init__(self, config: dict):
        self._config = config

    @property
    def data_requirement(self):
        return DataRequirement(needs_astro=True)

    def score(self, context: DataContext) -> ScoreResult | None:
        # 1. 获取 context.stargazing_window
        # 2. 夜间 (观星窗口内) 平均云量 ≥ max_night_cloud_cover → None
        # 3. 基准分 base = base_{quality} (根据 window.quality)
        #    poor 场景: base = 100 - phase × 0.8 (从配置获取)
        # 4. 云量扣分 = 夜间平均云量 × cloud_penalty_factor
        # 5. 风速扣分: 从 wind_thresholds 阶梯查找
        # 6. Score = base - cloud_deduction - wind_deduction
```

### 时间窗口输出

- `time_window`: 主窗口 (`optimal_start` ~ `optimal_end`)
- `secondary_window`: 次窗口 (如果有)

### 应测试的内容

**触发判定:**
- 夜间总云量 ≥ 70% → None
- stargazing_window 为 None → None (不应发生，但防御)

**评分:**
- optimal 暗夜, 云量 2%, 风 2.8km/h → base=100 - 1.6 - 0 ≈ 98, Perfect
- good 窗口, 云量 10%, 风 25km/h → base=90 - 8 - 10 = 72, Possible
- partial 窗口, 云量 30% → base=70 - 24 = 46, Not Recommended
- poor 窗口, 月相 95%, 云量 50% → base=100-76 - 40 ≈ 极低

**wind 扣分:**
- 风速 > 40km/h → -30
- 风速 > 20km/h → -10
- 风速 ≤ 20km/h → 0

**分数钳制:**
- 最终分数 clamp 到 [0, 100]

---

## 验证命令

```bash
python -m pytest tests/unit/test_plugin_stargazing.py -v
```
