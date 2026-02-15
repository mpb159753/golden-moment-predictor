# M10A: GoldenMountainPlugin — 日照金山

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现日照金山评分 Plugin，支持 sunrise/sunset 双实例，包含目标山峰方位角匹配、光路云量评估、阶梯评分与一票否决机制。

**依赖模块:** M03 (GeoUtils), M04 (AstroUtils), M08 (ScoreEngine + DataContext)

---

## 背景

GoldenMountainPlugin 是 L2 级别 Plugin，需要额外数据：
- 目标山峰天气 (`needs_l2_target`)
- 光路检查点天气 (`needs_l2_light_path`)
- 天文数据 (`needs_astro`)

这些数据已由 Scheduler 提前获取并填入 `DataContext`，Plugin 从 context 中直接读取。

---

## Task 1: GoldenMountainPlugin 实现

**Files:**
- Create: `gmp/scoring/plugins/golden_mountain.py`
- Test: `tests/unit/test_plugin_golden_mountain.py`

### 配置参数 (来自 `engine_config.yaml → scoring.golden_mountain`)

```yaml
golden_mountain:
  trigger:
    max_cloud_cover: 80                    # 总云量 ≥ 80% 时未触发
  weights:
    light_path: 35
    target_visible: 40
    local_clear: 25
  thresholds:
    light_path_cloud: [10, 20, 30, 50]     # ≤10%=35, ≤20%=30, ≤30%=20, ≤50%=10, >50%=0
    target_cloud: [10, 20, 30, 50]         # ≤10%=40, ≤20%=35, ≤30%=25, ≤50%=10, >50%=0
    local_cloud: [15, 30, 50]              # ≤15%=25, ≤30%=20, ≤50%=10, >50%=0
  veto_threshold: 0                        # 任一维度=0则总分置0
```

### 设计要点

1. **双实例**: `GoldenMountainPlugin("sunrise_golden_mountain")` 和 `GoldenMountainPlugin("sunset_golden_mountain")`
2. **方位角匹配**: 根据 `event_type` 选择 `sun_events.sunrise_azimuth` 或 `sunset_azimuth`
3. **Target 筛选**: 使用 `GeoUtils.is_opposite_direction()` 和 `Target.applicable_events` 判断哪些目标适用

### 评分逻辑

```python
class GoldenMountainPlugin:
    def __init__(self, event_type: str, config: dict):
        self._event_type = event_type  # "sunrise_golden_mountain" 或 "sunset_golden_mountain"
        self._config = config

    @property
    def data_requirement(self):
        return DataRequirement(
            needs_l2_target=True,
            needs_l2_light_path=True,
            needs_astro=True,
        )

    def score(self, context: DataContext) -> ScoreResult | None:
        # 1. 安全检查 (日出/日落时段天气)
        # 2. 触发判定: 总云量 ≥ max_cloud_cover → None
        # 3. 确定日出/日落时段方位角
        # 4. 筛选适用 Target (GeoUtils.is_opposite_direction + applicable_events)
        # 5. 无适用 Target → None
        # 6. 计算光路云量: 从 context.light_path_weather 取相关时刻
        #    - 取 (low_cloud + mid_cloud) 的10点均值
        # 7. 计算目标可见性: 从 context.target_weather 取 primary target 的 (high_cloud + mid_cloud)
        # 8. 计算本地通透: 从 context.local_weather 取总云量
        # 9. 阶梯评分 + 一票否决
        # 10. 生成 ScoreResult (含 highlights/warnings)
```

### Target 适用性判定

```python
def _is_target_applicable(self, target: Target, sun_azimuth: float) -> bool:
    """判断目标是否适用当前事件"""
    # 1. 如果 target.applicable_events 不为 None:
    #    检查 "sunrise" 或 "sunset" 是否在列表中
    # 2. 如果 applicable_events 为 None (自动计算):
    #    bearing = GeoUtils.calculate_bearing(viewpoint, target)
    #    return GeoUtils.is_opposite_direction(bearing, sun_azimuth)
```

### 应测试的内容

**触发判定:**
- 总云量 ≥ 80% → None
- 无匹配 Target → None
- 正常场景 → ScoreResult

**方位角匹配:**
- sunrise 事件: 贡嘎 bearing≈245°, sunrise_azimuth≈108.5° → 匹配
- sunset 事件: 雅拉 `applicable_events=["sunset"]` → 匹配

**评分:**
- 光路 8%, 目标 13%, 本地 22% → score=90, Recommended
- 光路 0%, 目标 5%, 本地 10% → score=100, Perfect
- 光路 60% → S_light=0, 一票否决, 总分=0
- 目标 55% → S_target=0, 一票否决, 总分=0
- 本地 55% → S_local=0, 一票否决, 总分=0

**双实例:**
- sunrise 和 sunset 实例独立评分
- 同时注册到 ScoreEngine

---

## 验证命令

```bash
python -m pytest tests/unit/test_plugin_golden_mountain.py -v
```
