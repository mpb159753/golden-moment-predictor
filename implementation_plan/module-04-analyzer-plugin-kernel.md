# M04 - 分析器与 Plugin 内核

## 1. 模块目标

搭建评分体系的“内核层”，让后续具体景观 Plugin 可插拔运行：

- L1 本地分析器（安全/触发基础）
- L2 远程分析器（目标可见/光路通畅）
- Plugin 契约与注册中心（`ScorerPlugin` + `ScoreEngine`）

---

## 2. 背景上下文

- 参考：`design/03-scoring-plugins.md`、`design/06-class-sequence.md`
- 关键设计：
  - 先 L1，再触发 Plugin，再决定是否进入 L2
  - `DataRequirement` 决定数据按需获取
  - `ScoreEngine.collect_requirements` 聚合需求

---

## 3. 交付范围

### 本模块要做

1. `scorer/plugin.py`（Protocol + `DataRequirement`）
2. `scorer/engine.py`（注册中心）
3. `analyzer/local_analyzer.py`（L1）
4. `analyzer/remote_analyzer.py`（L2）

### 本模块不做

- 不实现 4 个具体 Plugin 的评分公式（M05）
- 不实现 Scheduler 主循环（M06）

---

## 4. 输入与输出契约

### 输入

- `local_weather`（逐小时 DataFrame）
- 目标天气与光路天气（仅 L2 用）
- 配置阈值（降水、能见度、云量阈值等）

### 输出

- `AnalysisResult`（`passed/score/reason/details`）
- 可供 Plugin `check_trigger` 使用的标准化 `details` 字段

---

## 5. 实施任务清单

1. 在 `scorer/plugin.py` 落地接口定义：
   - `event_type/display_name/data_requirement/check_trigger/score/dimensions`
2. 在 `scorer/engine.py` 实现：
   - `register`、`all_plugins`、`get`、`collect_requirements`
3. 在 `local_analyzer.py` 实现：
   - `_check_safety`（降水>50 或能见度<1000 失败）
   - 云海与雾凇触发基础指标提取
   - 输出 `details`（供 M05 使用）
4. 在 `remote_analyzer.py` 实现：
   - 目标可见性（中高云组合阈值）
   - 光路通畅度（10 点组合云量均值）

---

## 6. 验收标准

1. `collect_requirements` 对多插件聚合正确；
2. L1 一票否决条件可拦截后续流程；
3. L2 输出结构可被 GoldenMountainPlugin 直接消费；
4. 所有字段命名稳定，避免“隐式约定”。

---

## 7. 测试清单

- `tests/unit/test_score_engine.py`
  - 注册、查询、聚合需求
- `tests/unit/test_local_analyzer.py`
  - 安全通过/失败、云海触发、雾凇触发
- `tests/unit/test_remote_analyzer.py`
  - 目标可见与不可见、光路通畅与阻塞

---

## 8. 新会话启动提示词

```text
请按 implementation_plan/module-04-analyzer-plugin-kernel.md 完成 M04：
实现 scorer/plugin.py、scorer/engine.py、analyzer/local_analyzer.py、analyzer/remote_analyzer.py。
要求：L1/L2 输出结构稳定、可供后续插件评分直接使用，并补齐对应单测。
完成后汇报关键 details 字段定义与测试结果。
```
