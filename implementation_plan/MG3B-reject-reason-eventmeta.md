# MG3B: 后端 — forecast.json reject_reason + eventMeta 补充

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 为 forecast.json 中 0 分事件生成 `reject_reason` 精简拒绝原因，并补充前端 `eventMeta.js` 缺失的 `clear_sky` 条目。

**依赖模块:** M11A (ForecastReporter), MG2 (ClearSkyPlugin)

---

## 背景

当前 0 分事件只显示 `score: 0`，用户无法理解原因。设计文档 [§11.4](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/11-frontend-architecture-v2.md) 要求在 BottomSheet 半展态显示 0 分事件的拒绝原因。

此外，前端 [eventMeta.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/constants/eventMeta.js) 缺少 `clear_sky` 事件的颜色和名称映射。

---

## Task 1: ForecastReporter 生成 reject_reason 字段

**Files:**
- Modify: [forecast_reporter.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/output/forecast_reporter.py)
- Test: [test_forecast_reporter.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/tests/unit/test_forecast_reporter.py)

### 要实现的方法

在 `ForecastReporter` 中新增静态方法：

```python
@staticmethod
def _generate_reject_reason(event: ScoreResult) -> str | None:
    """为 0 分事件生成精简拒绝原因

    逻辑: 从 breakdown 中找到得分最低的维度，用其 detail 生成一句话。
    Returns: None (score > 0) 或 str (score == 0)
    """
```

修改 [_format_event()](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/output/forecast_reporter.py#L112-L127)，在输出 dict 中新增 `reject_reason` 字段。

### 应测试的内容

- 新增测试类 `TestForecastReporterRejectReason`：
  - score=0 的事件包含非空 `reject_reason` 字符串
  - score>0 的事件 `reject_reason` 为 None
  - reject_reason 提取最差维度的 detail 信息
- 已有测试全部通过（无回归）

---

## Task 2: 前端 eventMeta 补充 clear_sky

**Files:**
- Modify: [eventMeta.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/constants/eventMeta.js)

### 修改内容

```diff
 export const EVENT_COLORS = {
+    clear_sky: '#FFB300',
     sunrise_golden_mountain: '#FF8C00',
     ...
 }

 export const EVENT_NAMES = {
+    clear_sky: '晴天',
     sunrise_golden_mountain: '日出金山',
     ...
 }
```

---

## 验证命令

```bash
source venv/bin/activate

# 后端单元测试
pytest tests/unit/test_forecast_reporter.py -v

# 前端测试
cd frontend && npx vitest run --reporter verbose

# 集成验证 — 检查 reject_reason
python -m gmp.main generate-all --output public/data --no-archive
cat public/data/viewpoints/gongga_zimei_pass/forecast.json | python3 -m json.tool | grep -A2 reject_reason | head -20
```

Expected: 0 分事件包含 `"reject_reason": "..."` 字段，score>0 的事件 `reject_reason` 为 null。

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.4, §11.6, M11A*
