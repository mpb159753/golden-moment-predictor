# MG2B: 后端/前端 — 通用能力自动注入

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现通用能力（clear_sky、stargazing、frost、snow_tree、ice_icicle）自动注入机制，让所有观景台无需手动配置即可自动获得这些评分项。同时更新 index.json 输出和前端 EventIcon 映射。

**依赖模块:** MG2A (ClearSkyPlugin), M08 (ScoreEngine)

---

## 背景

当前系统要求每个观景台在 YAML 中手动配置 capabilities。例如红石滩只配了 `sunset`，即使当天晴空万里也看不到晴天评分。

### 能力分层

| 层级 | capabilities | 配置方式 |
|------|-------------|---------|
| **基底层** | `clear_sky`, `stargazing` | **自动注入** |
| **通用层** | `frost`, `snow_tree`, `ice_icicle` | **自动注入** |
| **地形层** | `sunrise`, `sunset`, `cloud_sea` | 需手动配置 |

### 预期效果

红石滩（仅配了 `sunset`）改动后的 forecast.json：

```diff
 "events": [
+  { "event_type": "clear_sky", "score": 75 },
   { "event_type": "sunset_golden_mountain", "score": 0 },
+  { "event_type": "stargazing", "score": 60 },
   // frost/snow_tree/ice_icicle 条件不满足时 Plugin 返回 None，不出现
 ]
```

---

## Task 1: 自动注入通用 capabilities

**Files:**
- Modify: [engine.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/scoring/engine.py)
- Test: [test_engine.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/tests/scoring/test_engine.py)

### 修改内容

1. 新增常量：

```python
_UNIVERSAL_CAPABILITIES: list[str] = [
    "clear_sky",    # 晴天（基底）
    "stargazing",   # 观星（基底）
    "frost",        # 雾凇（通用）
    "snow_tree",    # 雪挂树（通用）
    "ice_icicle",   # 冰挂（通用）
]
```

2. 修改 `filter_active_plugins()` 方法：

```diff
 def filter_active_plugins(
     self, capabilities, target_date, events_filter=None
 ) -> list[ScorerPlugin]:
     allowed: set[str] = set()
+    all_caps = list(set(capabilities + _UNIVERSAL_CAPABILITIES))
-    for cap in capabilities:
+    for cap in all_caps:
         mapped = _CAPABILITY_EVENT_MAP.get(cap, [cap])
         allowed.update(mapped)
     ...
```

### 应测试的内容

- 仅配置 `sunset` 的 viewpoint → 自动包含 clear_sky, stargazing, frost, snow_tree, ice_icicle 对应的 Plugin
- `events_filter` 仍然有效（可以过滤掉自动注入的事件）
- 已有完整 capabilities 的 viewpoint → 结果不变（无重复）

---

## Task 2: 更新 index.json 的 capabilities 输出

**Files:**
- Modify: [batch_generator.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/core/batch_generator.py)

### 修改内容

在生成 index.json 的 viewpoint 条目时，合并通用 capabilities：

```python
from gmp.scoring.engine import _UNIVERSAL_CAPABILITIES

all_capabilities = list(set(vp.capabilities + _UNIVERSAL_CAPABILITIES))
```

使前端可以知道每个景点实际拥有的所有事件类型。

---

## Task 3: 更新 list-viewpoints CLI 命令

**Files:**
- Modify: [main.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/main.py)

### 修改内容

在 `capability_zh` 字典中添加：

```diff
 capability_zh: dict[str, str] = {
+    "clear_sky": "晴天",
     "sunrise": "日出",
     ...
 }
```

---

## Task 4: 前端 EventIcon 添加 clear_sky 映射

**Files:**
- Modify: [EventIcon.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/event/EventIcon.vue)

### 修改内容

在 `EVENT_CONFIG` 中新增 `clear_sky` 条目：

```javascript
import ClearSky from '@/assets/icons/clear-sky.svg'

clear_sky: { color: '#FFB300', name: '晴天', icon: ClearSky },
```

> **注意**：`clear-sky.svg` 由 MG1 产出。如果 MG1 尚未完成，先创建占位符 SVG。

---

## 不需要修改的文件

- **49 个 viewpoint YAML 配置**：通用 capabilities 是代码层自动注入的，不需要修改任何配置文件
- **timeline_reporter.py**：clear_sky 无 time_window，不会出现在 events_active 中（符合预期）

---

## 验证命令

```bash
source venv/bin/activate

# 单元测试
pytest tests/scoring/test_engine.py -v -k "universal or filter"

# 集成验证 — 红石滩应出现 clear_sky 事件
python -m gmp.main predict transit_lixiao_redstone --output json | python3 -m json.tool | head -40

# 批量生成，检查 index.json 中 capabilities 是否包含通用能力
python -m gmp.main generate-all --output public/data --no-archive
cat public/data/index.json | python3 -m json.tool | head -30

# 前端测试
cd frontend && npx vitest run --reporter verbose
```

---

## 风险与注意事项

1. **forecast.json 体积**：每天多了最多 5 个事件的数据，但大部分 Plugin 在条件不满足时返回 None，不写入 JSON
2. **Season filter**：`frost`, `snow_tree`, `ice_icicle` 有季节限制（`season_months`），即使自动注入也不会在夏天出现

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.2, MG2A, MG1*
