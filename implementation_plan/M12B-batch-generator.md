# M12B: 批量生成器 BatchGenerator

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现批量生成编排器 `BatchGenerator`，负责遍历所有观景台/线路→调用 Scheduler 评分→生成 JSON 文件→归档。

**依赖模块:** M11 (输出层: Reporters + JSONFileWriter), M12 (GMPScheduler)

---

## 背景

`BatchGenerator` 从 `GMPScheduler` 中抽离出来，专注于批量编排和文件输出职责：
1. 遍历所有已配置的观景台，逐站调用 `scheduler.run()` 评分
2. 遍历所有已配置的线路，逐线路调用 `scheduler.run_route()` 评分
3. 使用 `ForecastReporter` / `TimelineReporter` 将评分结果转为 JSON 格式
4. 使用 `JSONFileWriter` 写入文件系统
5. 生成 `index.json` + `meta.json`
6. 归档到 `archive/` 目录

### 设计动机

将文件输出和批量编排从 Scheduler 中分离，遵循单一职责原则：
- **Scheduler**: 核心评分管线（单站/线路评分）
- **BatchGenerator**: 批量编排 + 文件 I/O

---

## Task 1: BatchGenerator 实现

**Files:**
- Create: `gmp/core/batch_generator.py`
- Test: `tests/unit/test_batch_generator.py`

### 要实现的类

```python
class BatchGenerator:
    def __init__(
        self,
        scheduler: GMPScheduler,
        viewpoint_config: ViewpointConfig,
        route_config: RouteConfig,
        forecast_reporter: ForecastReporter,
        timeline_reporter: TimelineReporter,
        json_writer: JSONFileWriter,
    ):
        """接收 Scheduler 和输出层组件"""

    def generate_all(
        self,
        days: int = 7,
        events: list[str] | None = None,
        fail_fast: bool = False,
        no_archive: bool = False,
    ) -> dict:
        """批量生成所有观景台+线路的预测

        Steps:
        1. 遍历所有 viewpoints → scheduler.run() → forecast/timeline 生成
        2. 遍历所有 routes → scheduler.run_route() → 线路 forecast 生成
        3. 写入 forecast.json / timeline.json (JSONFileWriter)
        4. 生成 index.json (观景台/线路索引)
        5. 生成 meta.json (时间戳/版本/执行统计)
        6. no_archive=False 时归档到 archive/YYYY-MM-DDTHH-MM/

        Returns:
            {
                "viewpoints_processed": int,
                "routes_processed": int,
                "failed_viewpoints": list[str],  # 失败的 viewpoint IDs
                "failed_routes": list[str],       # 失败的 route IDs
                "output_dir": str,
                "archive_dir": str | None,
            }
        """

    def _process_viewpoint(
        self, viewpoint_id: str, days: int, events: list[str] | None
    ) -> PipelineResult | None:
        """处理单个观景台：评分 + 文件生成，失败返回 None"""

    def _process_route(
        self, route_id: str, days: int, events: list[str] | None
    ) -> dict | None:
        """处理单条线路：评分 + 文件生成，失败返回 None"""
```

### 应测试的内容

**Happy Path:**
- 2 个 viewpoint, 1 个 route → 输出完整文件集
- 各站 `scheduler.run()` 被正确调用
- `JSONFileWriter` 写入正确路径

**容错:**
- fail_fast=False: 单站失败跳过, 返回 `failed_viewpoints` 列表
- fail_fast=True: 单站失败立即中止, 抛出异常
- 单条线路中某站失败 → 线路级别记录 warning

**归档:**
- no_archive=False → 调用 `json_writer.archive()`
- no_archive=True → 不调用 `json_writer.archive()`

**输出统计:**
- `meta.json` 包含 `generated_at`, `engine_version`, `viewpoints_count`, `routes_count`
- `index.json` 包含所有成功处理的 viewpoint 和 route

---

## 验证命令

```bash
python -m pytest tests/unit/test_batch_generator.py -v
```
