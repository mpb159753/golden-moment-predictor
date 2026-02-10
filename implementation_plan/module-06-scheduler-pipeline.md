# M06 - GMPScheduler 与主流水线

## 1. 模块目标

把“获取数据 → 过滤触发 → 插件评分”串成统一可扩展主流程，支持 `days=1..7` 与 `events` 过滤。

---

## 2. 背景上下文

- 参考：`design/01-architecture.md`、`design/03-scoring-plugins.md`、`design/06-class-sequence.md`
- 核心流程：
  1. 收集活跃插件
  2. 聚合数据需求
  3. Phase1 获取本地天气 + 按需天文
  4. L1 本地滤网
  5. 插件触发
  6. 仅在需要时执行 Phase2 + L2
  7. 构建 `DataContext` 循环评分

---

## 3. 交付范围

### 本模块要做

- `core/scheduler.py`
- 如需要：`core/pipeline.py`（封装中间结果对象）

### 本模块不做

- 不实现 HTTP 路由（M08）
- 不实现最终 JSON reporter（M07）

---

## 4. 输入与输出契约

### 输入

- `viewpoint_id`、`days`、`events(optional)`
- Config/Fetcher/Astro/Analyzer/ScoreEngine 依赖

### 输出

- 结构化中间结果（供 ForecastReporter 与 TimelineReporter 使用）
- 包含每日 `events`、`confidence`、`meta.cache_stats`

---

## 5. 实施任务清单

1. 实现 `run(viewpoint_id, days, events=None)`：
   - 参数校验：days 1~7
   - 加载观景台配置
2. 实现 `_collect_active_plugins(viewpoint, events, date)`：
   - capability 过滤
   - events 过滤
   - season 过滤
3. 实现“按需获取”策略：
   - `any(needs_astro)` 决定天文计算
   - 触发插件中 `any(needs_l2_*)` 决定 L2
4. 实现 L1/L2 失败分支：
   - L1 失败：当天 `events=[]` 并写 summary 线索
   - L2 部分失败：标记 `partial_data`
5. 汇总每日日志与缓存统计。

---

## 6. 验收标准

1. `events` 过滤可减少不必要的 L2/API 调用；
2. 所有插件通过统一循环调用，无硬编码某插件逻辑；
3. 7 天循环输出结构稳定；
4. 可正确映射置信度（T+1~2 High, T+3~4 Medium, T+5~7 Low）。

---

## 7. 测试清单

- `tests/integration/test_pipeline.py`
  - 晴天全链路
  - 雨天 L1 拦截
  - events 过滤跳过 L2
- `tests/unit/test_scheduler.py`
  - 插件筛选、需求聚合、天数参数校验

---

## 8. 新会话启动提示词

```text
请按 implementation_plan/module-06-scheduler-pipeline.md 实现 M06：
完成 GMPScheduler 主流程（插件收集、需求聚合、懒加载、L1/L2、逐日评分）。
要求：禁止硬编码某个插件，必须通过 Plugin 循环执行；补齐调度相关单测/集成测试。
```
