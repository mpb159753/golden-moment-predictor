# MG2 — 基础景色条件添加（clear_sky Plugin + 通用能力自动注入）

## 背景

GMP（Golden Moment Predictor）是一个川西旅行景观预测系统。当前系统有 7 个评分 Plugin，但评分体系存在一个核心问题：

**只有手动配置了 capabilities 的景观才会被评分展示。** 例如红石滩只配了 `sunset` capability，即使当天晴空万里、具备雾凇条件，用户也看不到这些信息，只会看到"日落金山：0 分"。

### 用户需求

1. **晴天也有价值**：在川西，晴天本身就是好天气，应该被作为"基底评分"展示——即使没有日照金山、云海等稀有景观
2. **分层评分**：晴天是"值得去"，日照金山是"强烈建议去"
3. **减少配置负担**：晴天、观星、雾凇、雪挂树、冰挂等通用景观不应该需要为每个观景台手动配置

### 改动范围

本计划涉及**纯后端改动**（Python + YAML 配置），不涉及前端代码。

## 当前架构

### capabilities 工作流程

```
viewpoint.yaml (capabilities: [sunrise, sunset, ...])
       ↓
ScoreEngine.filter_active_plugins(capabilities, ...)
       ↓
_CAPABILITY_EVENT_MAP 映射 capability → [event_type, ...]
       ↓
只运行匹配的 Plugin → 生成 forecast.json
```

### _CAPABILITY_EVENT_MAP（当前）

文件：[engine.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/scoring/engine.py)

```python
_CAPABILITY_EVENT_MAP: dict[str, list[str]] = {
    "sunrise": ["sunrise_golden_mountain"],
    "sunset": ["sunset_golden_mountain"],
    "stargazing": ["stargazing"],
    "cloud_sea": ["cloud_sea"],
    "frost": ["frost"],
    "snow_tree": ["snow_tree"],
    "ice_icicle": ["ice_icicle"],
}
```

### Plugin 注册（当前）

文件：[main.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/main.py#L63-L75)

```python
def _register_plugins(engine: ScoreEngine, config: ConfigManager) -> None:
    gm_cfg = config.get_plugin_config("golden_mountain")
    engine.register(GoldenMountainPlugin("sunrise_golden_mountain", gm_cfg))
    engine.register(GoldenMountainPlugin("sunset_golden_mountain", gm_cfg))
    engine.register(StargazingPlugin(config.get_plugin_config("stargazing")))
    engine.register(CloudSeaPlugin(
        config.get_plugin_config("cloud_sea"),
        config.get_safety_config(),
    ))
    engine.register(FrostPlugin(config.get_plugin_config("frost")))
    engine.register(SnowTreePlugin(config.get_plugin_config("snow_tree")))
    engine.register(IceIciclePlugin(config.get_plugin_config("ice_icicle")))
```

### 观景台配置示例

红石滩 [transit_lixiao_redstone.yaml](file:///Users/mpb/WorkSpace/golden-moment-predictor/config/viewpoints/transit_lixiao_redstone.yaml)：
```yaml
id: transit_lixiao_redstone
name: 理小路红石滩（凉台沟）
capabilities:
  - sunset       # ← 只配了一个，结果 forecast 中只有 sunset_golden_mountain
```

牛背山 [niubei_gongga.yaml](file:///Users/mpb/WorkSpace/golden-moment-predictor/config/viewpoints/niubei_gongga.yaml)：
```yaml
id: niubei_gongga
name: 牛背山
capabilities:
  - sunrise
  - sunset
  - stargazing
  - cloud_sea
  - frost
  - snow_tree
  - ice_icicle    # ← 配了 7 个，比较完整
```

## 设计方案

### 能力分层

| 层级 | capabilities | 说明 | 配置方式 |
|------|-------------|------|---------|
| **基底层** | `clear_sky`, `stargazing` | 天气好就值得去 | **所有观景台自动拥有** |
| **通用层** | `frost`, `snow_tree`, `ice_icicle` | 川西高海拔通用冰雪景观 | **所有观景台自动拥有** |
| **地形层** | `sunrise`, `sunset`, `cloud_sea` | 取决于朝向/海拔/target 等 | **需手动配置** |

### 自动注入逻辑

新增一个 `_UNIVERSAL_CAPABILITIES` 常量，在 `filter_active_plugins()` 中自动添加到 capabilities 列表：

```python
# 所有观景台自动拥有的 capabilities（无需在 YAML 中手动配置）
_UNIVERSAL_CAPABILITIES: list[str] = [
    "clear_sky",    # 晴天（基底）
    "stargazing",   # 观星（基底）
    "frost",        # 雾凇（通用）
    "snow_tree",    # 雪挂树（通用）
    "ice_icicle",   # 冰挂（通用）
]
```

## 具体变更

### 第 1 步：新增 ClearSkyPlugin

#### [NEW] `gmp/scoring/plugins/clear_sky.py`

**评分逻辑设计**：

晴天评分的核心是"当天的天气有多好"，综合以下维度：

| 维度 | 权重 | 说明 |
|------|------|------|
| `cloud_cover` | 50 分 | 总云量越低越好（晴空指标核心） |
| `precipitation` | 25 分 | 无降水（雨/雪概率低） |
| `visibility` | 25 分 | 能见度高（空气通透） |

**触发条件**：平均总云量 < 80%（纯阴天/暴雨天不触发）

**评分阶梯（cloud_cover 维度示例）**：
- 总云量 < 10% → 50 分（完美晴天）
- 总云量 < 30% → 40 分（少云）
- 总云量 < 50% → 25 分（多云但以晴为主）
- 总云量 < 70% → 10 分（阴转多云）
- 总云量 ≥ 70% → 0 分

**参考模式**：参照 [frost.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/scoring/plugins/frost.py) 的结构：
- L1 Plugin（仅需本地天气数据 `context.local_weather`）
- 使用 `DataRequirement()` 默认值（无需 L2 target 数据或天文数据）
- 安全过滤：剔除降水概率过高的时段

**时间窗口**：空（全天评估），不设置 `time_window`

**Data requirement**：

```python
@property
def data_requirement(self) -> DataRequirement:
    return DataRequirement()  # L1: 仅需本地天气
```

---

### 第 2 步：注册 ClearSkyPlugin

#### [MODIFY] `gmp/scoring/engine.py`

1. 在 `_CAPABILITY_EVENT_MAP` 中新增 `clear_sky` 映射：

```diff
 _CAPABILITY_EVENT_MAP: dict[str, list[str]] = {
+    "clear_sky": ["clear_sky"],
     "sunrise": ["sunrise_golden_mountain"],
     "sunset": ["sunset_golden_mountain"],
     ...
 }
```

2. 新增 `_UNIVERSAL_CAPABILITIES` 常量：

```python
_UNIVERSAL_CAPABILITIES: list[str] = [
    "clear_sky",
    "stargazing",
    "frost",
    "snow_tree",
    "ice_icicle",
]
```

3. 修改 `filter_active_plugins()` 方法，自动合并通用 capabilities：

```diff
 def filter_active_plugins(
     self,
     capabilities: list[str],
     target_date: date,
     events_filter: list[str] | None = None,
 ) -> list[ScorerPlugin]:
     # 展开 capabilities → event_types
     allowed: set[str] = set()
+    # 自动注入通用 capabilities
+    all_caps = list(set(capabilities + _UNIVERSAL_CAPABILITIES))
-    for cap in capabilities:
+    for cap in all_caps:
         mapped = _CAPABILITY_EVENT_MAP.get(cap, [cap])
         allowed.update(mapped)
     ...
```

---

### 第 3 步：注册 ClearSkyPlugin 到工厂

#### [MODIFY] `gmp/main.py`

在 `_register_plugins()` 中添加 ClearSkyPlugin 注册：

```diff
+from gmp.scoring.plugins.clear_sky import ClearSkyPlugin

 def _register_plugins(engine: ScoreEngine, config: ConfigManager) -> None:
     gm_cfg = config.get_plugin_config("golden_mountain")
     engine.register(GoldenMountainPlugin("sunrise_golden_mountain", gm_cfg))
     engine.register(GoldenMountainPlugin("sunset_golden_mountain", gm_cfg))
     engine.register(StargazingPlugin(config.get_plugin_config("stargazing")))
     engine.register(CloudSeaPlugin(
         config.get_plugin_config("cloud_sea"),
         config.get_safety_config(),
     ))
     engine.register(FrostPlugin(config.get_plugin_config("frost")))
     engine.register(SnowTreePlugin(config.get_plugin_config("snow_tree")))
     engine.register(IceIciclePlugin(config.get_plugin_config("ice_icicle")))
+    engine.register(ClearSkyPlugin(config.get_plugin_config("clear_sky")))
```

---

### 第 4 步：添加 ClearSky 评分配置

#### [MODIFY] `config/engine_config.yaml`

在 `scoring:` 下新增 `clear_sky` 配置块：

```yaml
  clear_sky:
    trigger:
      max_cloud_cover: 80          # 平均总云量 ≥ 80% 时返回 None (未触发)
    weights:
      cloud_cover: 50              # 云量评分权重
      precipitation: 25            # 降水评分权重
      visibility: 25               # 能见度评分权重
    thresholds:
      cloud_pct: [10, 30, 50, 70]          # 总云量阈值
      cloud_scores: [50, 40, 25, 10, 0]    # 对应分值（含兜底）
      precip_pct: [10, 30, 50]             # 降水概率阈值
      precip_scores: [25, 20, 10, 0]       # 对应分值（含兜底）
      visibility_km: [30, 15, 5]           # 能见度阈值(km)
      visibility_scores: [25, 20, 10, 5]   # 对应分值（含兜底）
```

---

### 第 5 步：更新前端 EventIcon 映射（简要说明）

#### [MODIFY] `frontend/src/components/event/EventIcon.vue`

在 `EVENT_CONFIG` 中新增 `clear_sky` 条目：

```js
import ClearSky from '@/assets/icons/clear-sky.svg'

// 在 EVENT_CONFIG 中添加:
clear_sky: { color: '#FFB300', name: '晴天', icon: ClearSky },
```

> **注意**：`clear-sky.svg` 由 MG1 计划产出。如果 MG1 尚未完成，可以先创建一个占位符 SVG。

---

### 第 6 步：更新 index.json 中的 capabilities 展示

#### [MODIFY] `gmp/core/batch_generator.py`

`batch_generator.py` 在生成 `index.json` 时输出 viewpoint 的 capabilities。需要决定是否将通用 capabilities 也写入 index.json。

**建议**：在 index.json 中**包含**通用 capabilities，这样前端可以知道每个景点拥有哪些事件。

在 [batch_generator.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/core/batch_generator.py) 的 `_build_index_entry()` 或类似方法中：

```python
# 合并手动 capabilities 和通用 capabilities
from gmp.scoring.engine import _UNIVERSAL_CAPABILITIES
all_capabilities = list(set(vp.capabilities + _UNIVERSAL_CAPABILITIES))
```

同样在 [main.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/main.py#L459) 的 `list-viewpoints` 命令中更新 capabilities 展示。

---

### 第 7 步：更新 `list-viewpoints` 命令的中文映射

#### [MODIFY] `gmp/main.py`

在 `capability_zh` 字典（约 L430）中添加新的映射：

```diff
 capability_zh: dict[str, str] = {
+    "clear_sky": "晴天",
     "sunrise": "日出",
     "sunset": "日落",
     ...
 }
```

## 不需要修改的文件

- **49 个 viewpoint YAML 配置**：因为通用 capabilities 是代码层自动注入的，不需要修改任何 viewpoint 配置文件
- **timeline_reporter.py**：timeline 仍然使用 event 的 time_window 来分配小时，clear_sky 无 time_window，会在 events_active 中不出现（符合预期，clear_sky 是全天评估的日级事件）

## 测试计划

### 单元测试

1. **ClearSkyPlugin 测试** (`tests/scoring/plugins/test_clear_sky.py`)
   - 晴天（云量 10%）→ 高分（~90+）
   - 多云（云量 50%）→ 中等分（~40-60）
   - 阴天（云量 85%）→ 返回 None（未触发）
   - 暴雨（降水概率 90%）→ 低分
   - 完美条件（0% 云量 + 0% 降水 + 高能见度）→ 100 分

2. **filter_active_plugins 测试** (`tests/scoring/test_engine.py`)
   - 仅配置 `sunset` 的 viewpoint → 自动包含 clear_sky, stargazing, frost, snow_tree, ice_icicle
   - `events_filter` 仍然有效（可以过滤掉自动注入的事件）

3. **回归测试**
   - 已有的牛背山（配了完整 capabilities）→ 结果中新增 clear_sky 事件，其他事件评分不变

### 集成测试

```bash
# 在 venv 中运行
source venv/bin/activate

# 1. 验证红石滩现在有多个事件（之前只有 sunset_golden_mountain）
python -m gmp.main predict transit_lixiao_redstone --output json | python -m json.tool

# 2. 验证牛背山多了 clear_sky 事件
python -m gmp.main predict niubei_gongga --output json | python -m json.tool

# 3. 批量生成，验证 forecast.json 结构
python -m gmp.main generate-all --output public/data

# 4. 检查红石滩的 forecast.json 是否包含 clear_sky, frost 等事件
cat public/data/viewpoints/transit_lixiao_redstone/forecast.json | python -m json.tool | head -80
```

## 预期效果

### 改动前（红石滩 forecast.json）

```json
{
  "daily": [{
    "events": [
      { "event_type": "sunset_golden_mountain", "score": 0 }
    ]
  }]
}
```

### 改动后（红石滩 forecast.json）

```json
{
  "daily": [{
    "events": [
      { "event_type": "clear_sky", "display_name": "晴天", "score": 75 },
      { "event_type": "sunset_golden_mountain", "display_name": "日落金山", "score": 0 },
      { "event_type": "stargazing", "display_name": "观星", "score": 60 },
      { "event_type": "frost", "display_name": "雾凇", "score": null },
      { "event_type": "snow_tree", "display_name": "树挂积雪", "score": null },
      { "event_type": "ice_icicle", "display_name": "冰挂", "score": null }
    ]
  }]
}
```

> 注：`null` 表示该 Plugin 的触发条件未满足（如温度不够低，无法形成雾凇），Plugin 返回 `None`。这些不会出现在实际 JSON 中。

## 风险与注意事项

1. **评分膨胀**：新增 clear_sky 后，晴天的观景台最高分可能普遍升高。这是预期行为——晴天在川西确实有价值
2. **forecast.json 体积**：每天多了最多 5 个事件的数据，但大部分 Plugin 在条件不满足时返回 None，不会写入 JSON
3. **Season filter**：`frost`, `snow_tree`, `ice_icicle` 可能有季节限制（`season_months`），即使自动注入也不会在夏天出现

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: MG1 (SVG 图标设计)*
