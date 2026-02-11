# Module 05: 评分插件 — 简单型 (云海/雾凇/树挂/冰挂) + ScoreEngine

## 模块背景

本模块实现 4 个"仅需 L1 本地天气数据"的简单评分插件，以及 Plugin 注册中心 ScoreEngine。这 4 个插件不需要远程 API 数据（不需要 L2 滤网），实现相对独立，因此归为一组。

**包含的 Plugin**:
- `CloudSeaPlugin` — 云海评分
- `FrostPlugin` — 雾凇评分
- `SnowTreePlugin` — 树挂积雪评分
- `IceIciclePlugin` — 冰挂评分

**在系统中的位置**: 评分层 (`gmp/scorer/`) — 通过 ScoreEngine 注册，被 Scheduler 调度调用。

**前置依赖**: Module 01（`DataRequirement`, `DataContext`, `ScoreResult`, `IScorerPlugin` Protocol）

## 设计依据

- [03-scoring-plugins.md](../design/03-scoring-plugins.md): §3.2 Plugin 核心契约, §3.4 通用评分原则, §3.7 CloudSea, §3.8 Frost, §3.9 SnowTree, §3.10 IceIcicle, §3.11 ScoreEngine
- [06-class-sequence.md](../design/06-class-sequence.md): §6.3 分析层类图, §6.7 云海评分流程, §6.8 雾凇评分流程, §6.9 树挂评分流程
- [09-testing-config.md](../design/09-testing-config.md): §9.2 Plugin 测试用例

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/scorer/__init__.py` | 包初始化 |
| `gmp/scorer/plugin.py` | ScorerPlugin Protocol + DataRequirement 重导出 |
| `gmp/scorer/engine.py` | ScoreEngine 注册中心 |
| `gmp/scorer/cloud_sea.py` | CloudSeaPlugin |
| `gmp/scorer/frost.py` | FrostPlugin |
| `gmp/scorer/snow_tree.py` | SnowTreePlugin |
| `gmp/scorer/ice_icicle.py` | IceIciclePlugin |
| `tests/unit/test_plugin_cloud_sea.py` | 云海评分测试 |
| `tests/unit/test_plugin_frost.py` | 雾凇评分测试 |
| `tests/unit/test_plugin_snow_tree.py` | 树挂积雪评分测试 |
| `tests/unit/test_plugin_ice_icicle.py` | 冰挂评分测试 |
| `tests/unit/test_score_engine.py` | ScoreEngine 测试 |

## 代码接口定义

### `gmp/scorer/engine.py`

```python
from gmp.core.models import DataRequirement

class ScoreEngine:
    """Plugin 注册中心"""
    
    def __init__(self):
        self._plugins: dict[str, "ScorerPlugin"] = {}
    
    def register(self, plugin: "ScorerPlugin") -> None:
        self._plugins[plugin.event_type] = plugin
    
    def all_plugins(self) -> list:
        return list(self._plugins.values())
    
    def get(self, event_type: str):
        return self._plugins.get(event_type)
    
    def collect_requirements(self, plugins: list) -> DataRequirement:
        return DataRequirement(
            needs_l2_target=any(p.data_requirement.needs_l2_target for p in plugins),
            needs_l2_light_path=any(p.data_requirement.needs_l2_light_path for p in plugins),
            needs_astro=any(p.data_requirement.needs_astro for p in plugins),
        )
```

### `gmp/scorer/cloud_sea.py` — 云海评分

```python
class CloudSeaPlugin:
    event_type = "cloud_sea"
    display_name = "云海"
    data_requirement = DataRequirement()  # 仅需 L1
    
    def check_trigger(self, l1_data: dict) -> bool:
        cloud_base = l1_data.get("cloud_base_altitude", float('inf'))
        site_alt = l1_data.get("site_altitude", 0)
        return cloud_base < site_alt
    
    def score(self, context: DataContext) -> ScoreResult:
        """评分公式:
        Score = (Score_gap + Score_density) × Factor_mid_cloud + Score_wind
        
        维度:
        - 高差 (50分): >800m:50, >500m:40, >200m:20, >0m:10
        - 密度 (30分): 低云>80%:30, >50%:20, <30%:5
        - 中云修正: ≤30%:1.0, 30-60%:0.7, >60%:0.3
        - 稳定 (20分): 风速<10:20, 每增5扣5
        """
    
    def dimensions(self) -> list[str]:
        return ["gap", "density", "mid_structure", "wind"]
```

### `gmp/scorer/frost.py` — 雾凇评分

```python
class FrostPlugin:
    event_type = "frost"
    display_name = "雾凇"
    data_requirement = DataRequirement()  # 仅需 L1
    
    def check_trigger(self, l1_data: dict) -> bool:
        return l1_data.get("temperature_2m", 999) < 2.0
    
    def score(self, context: DataContext) -> ScoreResult:
        """评分公式:
        Score = Score_temp + Score_moisture + Score_wind + Score_cloud
        
        维度:
        - 温度 (40分): -5~-1:40, -10~-5:30, 0~2:25, <-10:15
        - 湿度 (30分): 能见度<5km:30, <10km:20, <20km:10, ≥20km:5
        - 风速 (20分): <3km/h:20, <5:15, <10:10, ≥10:0
        - 云况 (10分): 低云30-60%:10, <30%:5, >60%:3
        """
    
    def dimensions(self) -> list[str]:
        return ["temperature", "moisture", "wind", "cloud"]
```

### `gmp/scorer/snow_tree.py` — 树挂积雪评分

```python
class SnowTreePlugin:
    event_type = "snow_tree"
    display_name = "树挂积雪"
    data_requirement = DataRequirement()  # 仅需 L1
    
    def check_trigger(self, l1_data: dict) -> bool:
        """双路径触发:
        - fresh_path: 近12h降雪≥0.2cm + 距今≤12h + 当前晴朗
        - retention_path: 近24h降雪≥1.5cm + 降雪时段≥3h + 零下≥8h 
                          + 最高温≤1.5°C + 距今≤20h + 当前晴朗
        """
    
    def score(self, context: DataContext) -> ScoreResult:
        """评分公式:
        Score = Score_snow + Score_clear + Score_stable 
              - Deduction_age - Deduction_temp - Deduction_sun - Deduction_wind
        
        加分项:
        - 积雪信号 (60分): 按降雪量+时长阶梯
        - 晴朗程度 (20分): weather_code + 云量
        - 稳定保持 (20分): 当前风速

        扣分项:
        - 降雪距今: ≤3h:0, ≤8h:2, ≤12h:5, ≤16h:8, ≤20h:12, >20h:20
        - 升温融化: ≤-2°C:0, ≤-0.5°C:2, ≤1°C:6, ≤2.5°C:12, >2.5°C:22
        - 累积日照: 按晴朗+强晒小时数 >2:-5, >5:-15, >8:-30
        - 历史大风: max_wind>30:-20, >50:-50
        """
    
    def dimensions(self) -> list[str]:
        return ["snow_signal", "clear_weather", "stability", 
                "age_deduction", "temp_deduction", "sun_deduction", "wind_deduction"]
```

### `gmp/scorer/ice_icicle.py` — 冰挂评分

```python
class IceIciclePlugin:
    event_type = "ice_icicle"
    display_name = "冰挂"
    data_requirement = DataRequirement()  # 仅需 L1
    
    def check_trigger(self, l1_data: dict) -> bool:
        """双路径触发:
        - fresh_freeze_path: 12h水源≥0.4mm + 距今≤12h + 零下≥4h + 当前晴+冻
        - retention_path: 24h水源≥2.0mm + 距今≤20h + 零下≥10h 
                          + 最高温≤1.5°C + 当前晴+冻
        """
    
    def score(self, context: DataContext) -> ScoreResult:
        """评分公式:
        Score = Score_water + Score_freeze + Score_view - Deduction_age - Deduction_temp
        
        加分项:
        - 水源输入 (50分): ≥3.0mm:50, ≥2.0:42, ≥1.0:34, ≥0.4:24
        - 冻结强度 (30分): 按零下时长+当前温度阶梯
        - 观赏条件 (20分): 云量+风速

        扣分项:
        - 水源距今: ≤3h:0, ..., >20h:20
        - 升温融化: ≤-2°C:0, ..., >2.5°C:22
        """
    
    def dimensions(self) -> list[str]:
        return ["water_input", "freeze_strength", "view_quality",
                "age_deduction", "temp_deduction"]
```

## 实现要点

### 通用评分等级映射

```python
def _score_to_status(score: int) -> str:
    if score >= 95: return "Perfect"
    if score >= 80: return "Recommended"
    if score >= 50: return "Possible"
    return "Not Recommended"
```

建议在 `gmp/scorer/plugin.py` 或 `gmp/scorer/utils.py` 中提供此辅助函数，供所有 Plugin 复用。

### 树挂积雪的复杂性

SnowTreePlugin 是所有简单型 Plugin 中最复杂的，因为它有 4 个加分维度和 4 个扣分维度。建议：
- 每个维度的评分逻辑抽取为独立私有方法
- 扣分项使用阶梯查找表 (list of (threshold, deduction)) 简化逻辑

### ScoreResult 构建

所有 Plugin 的 `score()` 方法都应返回统一结构的 `ScoreResult`：

```python
ScoreResult(
    total_score=87,
    status="Recommended",
    breakdown={
        "dimension_name": {"score": 35, "max": 35, "detail": "说明文字"},
        ...
    }
)
```

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
python -m pytest tests/unit/test_plugin_cloud_sea.py tests/unit/test_plugin_frost.py \
  tests/unit/test_plugin_snow_tree.py tests/unit/test_plugin_ice_icicle.py \
  tests/unit/test_score_engine.py -v
```

### 具体测试用例

#### CloudSeaPlugin

| 测试函数 | 输入 | 预期 |
|---------|------|------|
| `test_trigger_positive` | 云底2600m, 站点3660m | True |
| `test_trigger_negative` | 云底5000m, 站点3660m | False |
| `test_score_perfect` | Gap1060m, 低云90%, 中云15%, 风2.8 | score=100, Perfect |
| `test_score_thick_mid_cloud` | Gap500m, 低云80%, 中云65% | score 大幅降低 (0.3 因子) |
| `test_score_high_wind` | Gap800m, 低云85%, 风25km/h | 风速扣分 |

#### FrostPlugin

| 测试函数 | 输入 | 预期 |
|---------|------|------|
| `test_trigger_positive` | 温度-3.8°C | True |
| `test_trigger_negative` | 温度5°C | False |
| `test_score_excellent` | -3°C, 能见度3km, 风1km/h, 低云45% | score≥90 |
| `test_score_dry` | -3.8°C, 能见度35km, 风2.8, 低云75% | score=67 |
| `test_score_windy` | -3°C, 能见度3km, 风15km/h | 风速0分 |

#### SnowTreePlugin

| 测试函数 | 输入 | 预期 |
|---------|------|------|
| `test_trigger_fresh_path` | 近12h雪0.5cm, 距今6h, 当前晴 | True |
| `test_trigger_retention_path` | 近24h雪2cm, 时段4h, 零下10h, 最高0°C, 距今18h, 晴 | True |
| `test_trigger_no_snow` | 无近期降雪 | False |
| `test_score_fresh_snow` | 大雪3cm, 距今3h, 晴朗, 低温 | score≥80 |
| `test_score_sun_destruction` | 大雪3cm, 距今19h, 暴晒8h, 升温2°C | score=46 |
| `test_score_wind_destruction` | 大雪3cm, 历史大风35km/h | 大幅扣分 |

#### IceIciclePlugin

| 测试函数 | 输入 | 预期 |
|---------|------|------|
| `test_trigger_fresh_freeze` | 12h水0.5mm, 距今8h, 零下5h, 晴, -1°C | True |
| `test_trigger_retention` | 24h水2.5mm, 距今15h, 零下12h, 最高0°C | True |
| `test_score_possible` | 水2.3mm, 冻结11h, -1.8°C, 云28%, 风14, 距15h | score=70 |

#### ScoreEngine

| 测试函数 | 验证内容 |
|---------|---------|
| `test_register_and_get` | 注册后可按 event_type 获取 |
| `test_all_plugins` | 返回所有已注册 Plugin |
| `test_collect_requirements` | 正确聚合多个 Plugin 的需求 |
| `test_register_new_plugin` | 注册自定义 Plugin |
| `test_events_filter` | 结合 capabilities 过滤 Plugin |

## 验收标准

- [ ] 4 个 Plugin 的 `check_trigger()` 逻辑正确
- [ ] 4 个 Plugin 的 `score()` 评分与设计文档示例一致
- [ ] ScoreEngine 注册和聚合功能正确
- [ ] 评分等级映射正确 (Perfect/Recommended/Possible/Not Recommended)
- [ ] 所有测试通过
