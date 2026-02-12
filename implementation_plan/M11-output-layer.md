# M11: 输出层 (Reporters + SummaryGenerator + JSONFileWriter)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现输出层全部组件：ForecastReporter、TimelineReporter、CLIFormatter、SummaryGenerator、JSONFileWriter。

**依赖模块:** M02 (数据模型: `PipelineResult`, `ScoreResult`), M08 (评分模型)

---

## 背景

输出层负责将 Scheduler 产生的 `PipelineResult` 转换为各种格式：
- **ForecastReporter**: 生成 `forecast.json` (精选事件卡片)
- **TimelineReporter**: 生成 `timeline.json` (逐时天气+事件标记)
- **CLIFormatter**: 生成终端表格输出
- **SummaryGenerator**: 基于规则模板生成单日文字摘要
- **JSONFileWriter**: 管理文件写入、目录创建、归档

### JSON 输出结构参考

详细 JSON 格式见 [05-api.md §5.2](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md)

### 目录结构

```
public/data/
├── index.json
├── viewpoints/{id}/forecast.json
├── viewpoints/{id}/timeline.json
├── routes/{id}/forecast.json
└── meta.json

archive/YYYY-MM-DDTHH-MM/
└── (同 public/data 结构)
```

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
```

### 应测试的内容

- 完整 PipelineResult → 包含所有字段
- events 按 score 降序排列
- best_event 为最高分事件
- summary 由 SummaryGenerator 生成
- confidence 字段正确

---

## Task 3: TimelineReporter — 时间线报告

**Files:**
- Create: `gmp/output/timeline_reporter.py`
- Test: `tests/unit/test_timeline_reporter.py`

### 要实现的类

```python
class TimelineReporter:
    def generate(self, result: PipelineResult, date: date) -> dict:
        """将 PipelineResult → timeline.json 格式的 dict

        输出格式 (见 05-api.md):
        {
            "viewpoint_id": "...",
            "generated_at": "...",
            "date": "...",
            "hourly": [
                {
                    "hour": 6,
                    "time": "06:00",
                    "safety_passed": true,
                    "weather": {...},
                    "events_active": [{...}]
                }
            ]
        }
        """

    def _assign_tags(self, hour: int, ...) -> list[str]:
        """根据时刻和事件生成 tags (sunrise_window, cloud_sea, etc.)"""
```

### 应测试的内容

- 24 小时逐时输出
- safety_passed 正确标记
- 活跃事件在对应时段标记
- tags 自动生成

---

## Task 4: CLIFormatter — 终端格式化

**Files:**
- Create: `gmp/output/cli_formatter.py`
- Test: `tests/unit/test_cli_formatter.py`

### 要实现的类

```python
class CLIFormatter:
    def __init__(self, color_enabled: bool = True):
        self._color = color_enabled

    def format_forecast(self, result: PipelineResult) -> str:
        """生成终端表格输出"""

    def format_detail(self, result: PipelineResult) -> str:
        """生成详细输出 (含 score_breakdown)"""

    def _colorize_status(self, status: str) -> str:
        """根据 status 着色"""
```

### 应测试的内容

- 输出包含日期、事件类型、分数、状态
- Perfect/Recommended/Possible/Not Recommended 各有不同着色
- detail 模式包含 breakdown 信息
- color_enabled=False 时无转义序列

---

## Task 5: JSONFileWriter — 文件写入

**Files:**
- Create: `gmp/output/json_file_writer.py`
- Test: `tests/unit/test_json_file_writer.py`

### 要实现的类

```python
class JSONFileWriter:
    def __init__(self, output_dir: str = "public/data", archive_dir: str = "archive"):
        self._output_dir = output_dir
        self._archive_dir = archive_dir

    def write_viewpoint(self, viewpoint_id: str, forecast: dict, timeline: dict) -> None:
        """写入 viewpoints/{id}/forecast.json 和 timeline.json"""

    def write_route(self, route_id: str, forecast: dict) -> None:
        """写入 routes/{id}/forecast.json"""

    def write_index(self, viewpoints: list, routes: list) -> None:
        """写入 index.json"""

    def write_meta(self, metadata: dict) -> None:
        """写入 meta.json"""

    def archive(self, timestamp: str) -> None:
        """将当前 output_dir 内容复制到 archive_dir/timestamp/"""
```

### 应测试的内容

- 写入文件到正确路径 (使用 tmp_path)
- 子目录自动创建
- JSON 格式正确可读
- archive 复制完整
- index.json 包含 viewpoints 和 routes
- meta.json 包含 generated_at 和 engine_version

---

## 验证命令

```bash
python -m pytest tests/unit/test_summary_generator.py tests/unit/test_forecast_reporter.py tests/unit/test_timeline_reporter.py tests/unit/test_cli_formatter.py tests/unit/test_json_file_writer.py -v
```
