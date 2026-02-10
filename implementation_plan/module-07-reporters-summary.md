# M07 - 输出层（Forecast/Timeline/Summary）

## 1. 模块目标

将调度器内部结果转换为前端/API 直接可用的两类输出：

- `forecast`（精选事件卡片）
- `timeline`（逐小时时间轴）

并实现规则摘要生成器。

---

## 2. 背景上下文

- 参考：`design/04-data-flow-example.md`、`design/05-api.md`、`06-class-sequence.md`
- 关键要求：
  - `/forecast` 与 `/timeline` 共享同一后端计算结果，仅视图不同
  - 输出字段命名与 API 文档保持一致
  - 摘要支持 `rule`/`llm` 模式，首版可先 `rule`

---

## 3. 交付范围

### 本模块要做

- `reporter/forecast_reporter.py`
- `reporter/timeline_reporter.py`
- `reporter/summary_generator.py`
- 可选 `reporter/base.py`

### 本模块不做

- 不实现 FastAPI 路由（M08）
- 不实现核心评分逻辑（M05）

---

## 4. 输入与输出契约

### 输入

- Scheduler 输出的中间结果（包含 daily events + hourly data）

### 输出

- `ForecastResponse` 结构：
  - `report_date/viewpoint/forecast_days/meta`
- `TimelineResponse` 结构：
  - `viewpoint/timeline_days`

---

## 5. 实施任务清单

1. `ForecastReporter.generate(...)`：
   - 输出每日事件数组
   - 注入 `summary`、`summary_mode`
   - 保留 `score_breakdown`
2. `TimelineReporter.generate(...)`：
   - 输出 24 小时数据
   - 计算并填充 tags（如 `sunrise_golden`, `frost_window`）
3. `SummaryGenerator`：
   - 规则模板先行（高分事件组合 → 文本）
   - 保留 `llm` 接口占位，默认回落规则模式

---

## 6. 验收标准

1. 输出 JSON 字段完整对齐 API 文档；
2. forecast/timeline 的同一天数据语义一致；
3. 摘要在“无事件/多事件”场景可读；
4. 事件条件、评分明细不丢失。

---

## 7. 测试清单

- `tests/unit/test_forecast_reporter.py`
  - 多事件输出、空事件输出、summary 模式
- `tests/unit/test_timeline_reporter.py`
  - 24小时结构、tags 赋值逻辑
- `tests/unit/test_summary_generator.py`
  - rule 模式关键模板分支

---

## 8. 新会话启动提示词

```text
请按 implementation_plan/module-07-reporters-summary.md 完成 M07：
实现 ForecastReporter、TimelineReporter、SummaryGenerator，输出字段必须与 05-api.md 对齐。
要求：补齐 reporter 单测，至少覆盖多事件、空事件、24小时 timeline 三类场景。
```
