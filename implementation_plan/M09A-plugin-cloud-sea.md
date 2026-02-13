# M09A: CloudSeaPlugin — 云海评分

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现云海评分 Plugin，仅需 L1 本地天气数据。

**依赖模块:** M08 (ScoreEngine + DataContext + Plugin 接口)

**可并行:** M09B, M09C, M09D (各 Plugin 相互独立，无依赖关系)

---

## 背景

CloudSeaPlugin 是 L1 Plugin，仅需 `DataContext.local_weather`（本地天气），不需要远程目标天气或天文数据。所有阈值/权重/配置参数从构造函数接收，来源于 `engine_config.yaml`。

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

## Task 1: CloudSeaPlugin 实现

**Files:**
- Create: `gmp/scoring/plugins/cloud_sea.py`
- Test: `tests/unit/test_plugin_cloud_sea.py`

### 配置参数 (来自 `engine_config.yaml → scoring.cloud_sea`)

```yaml
cloud_sea:
  weights: { gap: 50, density: 30, wind: 20 }
  thresholds:
    gap_meters: [800, 500, 200]              # >800=50, >500=40, >200=20, ≤200=10
    density_pct: [80, 50, 30]                # >80%=30, >50%=20, >30%=10, ≤30%=5
    wind_speed: [3, 5, 8]                    # <3=20, <5=15, <8=10, ≥8=5
    mid_cloud_penalty: [30, 60]              # >60%=0.3, >30%=0.7, ≤30%=1.0
```

### 评分逻辑

1. **触发判定**: `cloud_base_altitude < viewpoint.location.altitude` → 触发，否则返回 None
2. **高差计算**: `gap = viewpoint.altitude - cloud_base_altitude`
3. **评分公式**: `Score = (Score_gap + Score_density) × Factor_mid + Score_wind`
4. **维度**: `["gap", "density", "mid_structure", "wind"]`

### 应测试的内容

- 云底高度 > 站点海拔 → 返回 None (未触发)
- 云底高度 < 站点海拔, Gap=1060m, 低云75%, 中云5%, 风2.8km/h → score≈90
- 极大 Gap (>800m) + 高密度 (>80%) + 极低风 (<3km/h) + 低中云 → 满分
- 极小 Gap (<200m) → gap 维度低分
- 中云 >60% → factor=0.3 大幅扣分
- 中云 30-60% → factor=0.7
- 安全检查: 关注时段有降水 → 剔除该时段
- 配置驱动: 修改阈值后评分结果变化

---

## 验证命令

```bash
python -m pytest tests/unit/test_plugin_cloud_sea.py -v
```
