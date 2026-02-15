# M11B: TimelineReporter + CLIFormatter

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现时间线报告生成器和终端格式化输出，将 PipelineResult 转换为 timeline.json 格式和终端表格。

**依赖模块:** M02 (数据模型), M08 (评分模型), M11A (ForecastReporter — 保持事件筛选标准一致)

---

## 背景

输出层的第二步：提供逐时天气+事件标记的时间线视图，以及终端可读的格式化输出。TimelineReporter 和 CLIFormatter 均为纯格式化逻辑，耦合度高，适合在同一任务中实现。

---

## Task 1: TimelineReporter — 时间线报告

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
- tags 自动生成:
  - 日出时段 → 包含 `"sunrise_window"` tag
  - 云海事件活跃 → 对应时段包含 `"cloud_sea"` tag
  - 无事件的时段 → tags 为空列表
- 边界: hour=0 和 hour=23 正常处理
- 无活跃事件的日期 → hourly 仍有 24 条 weather 数据

---

## Task 2: CLIFormatter — 终端格式化

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

## 验证命令

```bash
python -m pytest tests/unit/test_timeline_reporter.py tests/unit/test_cli_formatter.py -v
```
