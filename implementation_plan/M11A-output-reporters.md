# M11A: SummaryGenerator + ForecastReporter

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现文字摘要生成器和预测报告生成器，将 PipelineResult 转换为 forecast.json 格式。

**依赖模块:** M02 (数据模型: `PipelineResult`, `ScoreResult`), M08 (评分模型)

---

## 背景

输出层的第一步：将评分结果转换为结构化的预测报告。ForecastReporter 依赖 SummaryGenerator 生成文字摘要，两者紧密耦合，适合在同一任务中实现。

### JSON 输出结构参考

详细 JSON 格式见 [05-api.md §5.2](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md)

---

## Task 1: SummaryGenerator — 文字摘要

**Files:**
- Create: `gmp/output/summary_generator.py`
- Test: `tests/unit/test_summary_generator.py`

### 要实现的类

```python
class SummaryGenerator:
    def __init__(self, mode: str = "rule"):
        self._mode = mode  # 当前仅支持 "rule"

    def generate(self, events: list[ScoreResult]) -> str:
        """基于事件列表生成单日文字摘要

        规则:
        - 无事件 → "不推荐 — 条件不佳"
        - 所有事件无 Recommended 以上 → "不推荐 — 全天降水" (或类似)
        - 有 Perfect → "完美观景日 — {top_events}"
        - 有 Recommended → "推荐观景 — {top_events}"
        - 仅 Possible → "可能可见 — {top_events}"

        top_events: 按分数排序取前 2-3 个的 display_name
        """
```

### 应测试的内容

- 空事件列表 → 不推荐摘要
- 1 个 Perfect 事件 → 包含该事件名称
- 多个 Recommended → 列出 top 事件
- 仅 Possible → 措辞保守

---

## Task 2: ForecastReporter — 预测报告

**Files:**
- Create: `gmp/output/forecast_reporter.py`
- Test: `tests/unit/test_forecast_reporter.py`

### 要实现的类

```python
class ForecastReporter:
    def __init__(self, summary_gen: SummaryGenerator | None = None):
        self._summary_gen = summary_gen or SummaryGenerator()

    def generate(self, result: PipelineResult) -> dict:
        """将 PipelineResult → forecast.json 格式的 dict

        输出格式 (见 05-api.md §5.2):
        {
            "viewpoint_id": "...",
            "viewpoint_name": "...",
            "generated_at": "...",
            "forecast_days": 7,
            "daily": [
                {
                    "date": "2026-02-12",
                    "summary": "...",
                    "best_event": {...},
                    "events": [{...}]
                }
            ]
        }
        """

    def generate_route(
        self, stops_results: list[PipelineResult], route: Route
    ) -> dict:
        """将多站 PipelineResult → 线路 forecast.json 格式的 dict

        输出格式 (见 05-api.md §5.2):
        {
            "route_id": "...",
            "route_name": "...",
            "generated_at": "...",
            "stops": [
                {
                    "viewpoint_id": "...",
                    "viewpoint_name": "...",
                    "order": 1,
                    "stay_note": "...",
                    "forecast": {...}   # 同单站 forecast 格式
                }
            ]
        }
        """
```

### 应测试的内容

- 完整 PipelineResult → 包含所有字段
- events 按 score 降序排列
- best_event 为最高分事件
- summary 由 SummaryGenerator 生成
- confidence 字段正确
- 2 站 PipelineResult → stops 数组长度 2
- stops 按 order 排序
- 每站 forecast 格式与单站一致
- route_id / route_name 正确填充

---

## 验证命令

```bash
python -m pytest tests/unit/test_summary_generator.py tests/unit/test_forecast_reporter.py -v
```
