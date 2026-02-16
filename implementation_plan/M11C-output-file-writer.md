# M11C: JSONFileWriter — 文件写入与归档

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 JSON 文件写入器，管理输出目录结构、文件写入和历史归档。

**依赖模块:** M02 (数据模型), M11A (ForecastReporter), M11B (TimelineReporter)

---

## 背景

输出层的最后一步：将 ForecastReporter 和 TimelineReporter 生成的 dict 写入文件系统，管理目录结构和归档。

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

## Task 1: JSONFileWriter 实现

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
- meta.json 包含 generated_at

---

## 验证命令

```bash
python -m pytest tests/unit/test_json_file_writer.py -v
```
