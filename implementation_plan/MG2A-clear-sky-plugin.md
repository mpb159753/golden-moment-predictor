# MG2A: 后端 — ClearSkyPlugin 创建与注册

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 ClearSkyPlugin 评分插件，注册到 ScoreEngine，并添加评分配置。独立完成后即可对手动配置了 `clear_sky` capability 的观景台生效。

**依赖模块:** M08 (ScoreEngine), M09B (FrostPlugin — 参考模式)

---

## 背景

GMP 当前有 7 个评分 Plugin，缺少对"晴天"这一基础天气条件的评分。在川西，晴天本身就有价值——即使没有日照金山、云海等稀有景观，晴朗的天气也意味着适合出行。

ClearSkyPlugin 的设计参照 [FrostPlugin](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/scoring/plugins/frost.py) 的 L1 Plugin 模式：仅需本地天气数据，无需 L2 目标天气或天文数据。

### 评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| `cloud_cover` | 50 分 | 总云量越低越好（晴空核心指标） |
| `precipitation` | 25 分 | 无降水（雨/雪概率低） |
| `visibility` | 25 分 | 能见度高（空气通透） |

**触发条件**：平均总云量 < 80%（纯阴天/暴雨天不触发，返回 None）

---

## Task 1: 新增 ClearSkyPlugin

**Files:**
- Create: `gmp/scoring/plugins/clear_sky.py`
- Test: `tests/scoring/plugins/test_clear_sky.py`

### 要实现的类

```python
class ClearSkyPlugin(ScorerPlugin):
    """晴天评分 — L1 Plugin，仅需本地天气"""

    @property
    def event_type(self) -> str:
        return "clear_sky"

    @property
    def data_requirement(self) -> DataRequirement:
        return DataRequirement()  # L1: 仅需本地天气

    def score(self, context: DataContext) -> ScoreResult | None:
        """评分逻辑:
        1. 计算日间平均总云量，≥ trigger.max_cloud_cover 返回 None
        2. 按 cloud_cover / precipitation / visibility 三维度打分
        3. 加权求和
        """
```

**参考模式**：[frost.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/scoring/plugins/frost.py) 的结构（L1 Plugin，使用 `context.local_weather`）

### 应测试的内容

- 晴天（云量 10%）→ 高分（~90+）
- 多云（云量 50%）→ 中等分（~40-60）
- 阴天（云量 85%）→ 返回 None（未触发）
- 暴雨（降水概率 90%）→ 低分
- 完美条件（0% 云量 + 0% 降水 + 高能见度）→ 100 分

---

## Task 2: 注册 ClearSkyPlugin

**Files:**
- Modify: [engine.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/scoring/engine.py) — 在 `_CAPABILITY_EVENT_MAP` 中添加 `clear_sky` 映射
- Modify: [main.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/main.py) — 在 `_register_plugins()` 中注册 ClearSkyPlugin

### Engine 修改

```diff
 _CAPABILITY_EVENT_MAP: dict[str, list[str]] = {
+    "clear_sky": ["clear_sky"],
     "sunrise": ["sunrise_golden_mountain"],
     ...
 }
```

### Main 修改

```diff
+from gmp.scoring.plugins.clear_sky import ClearSkyPlugin

 def _register_plugins(engine: ScoreEngine, config: ConfigManager) -> None:
     ...
+    engine.register(ClearSkyPlugin(config.get_plugin_config("clear_sky")))
```

---

## Task 3: 添加评分配置

**Files:**
- Modify: [engine_config.yaml](file:///Users/mpb/WorkSpace/golden-moment-predictor/config/engine_config.yaml)

### 新增配置块

```yaml
  clear_sky:
    trigger:
      max_cloud_cover: 80
    weights:
      cloud_cover: 50
      precipitation: 25
      visibility: 25
    thresholds:
      cloud_pct: [10, 30, 50, 70]
      cloud_scores: [50, 40, 25, 10, 0]
      precip_pct: [10, 30, 50]
      precip_scores: [25, 20, 10, 0]
      visibility_km: [30, 15, 5]
      visibility_scores: [25, 20, 10, 5]
```

---

## 验证命令

```bash
source venv/bin/activate

# 单元测试
pytest tests/scoring/plugins/test_clear_sky.py -v

# 集成验证 — 对牛背山跑一次预测(需手动给牛背山加 clear_sky capability 或等 MG2B 自动注入)
python -m gmp.main predict niubei_gongga --output json | python3 -m json.tool | head -40
```

---

## 风险与注意事项

1. **评分膨胀**：晴天评分使得晴天的观景台最高分普遍升高。这是预期行为。
2. **本 Task 完成后**：ClearSkyPlugin 仅对手动配置了 `clear_sky` capability 的观景台生效。需要 MG2B（自动注入）才能让所有观景台自动拥有。

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.2, MG1*
