# MG5B: 前端 — ViewpointDetail 趋势优先布局重构

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 重构 ViewpointDetail 详情页布局，将 TrendChart 提升到顶部替代 DatePicker 作为日期选择器，整合四段时段评分、事件详情和逐时天气表。

**依赖模块:** MG4A (TimePeriodBar + useTimePeriod), MG5A (TrendChart + HourlyWeatherTable), MG3B (reject_reason)

---

## 背景

对应设计文档 [§11.5](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/11-frontend-architecture-v2.md)。当前 [ViewpointDetail.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/ViewpointDetail.vue) 的布局为：

```
当前:                          目标:
┌──────────────────┐          ┌──────────────────┐
│ ← 返回     📷    │          │ ← 返回     📷    │
│ DatePicker       │          │ TrendChart       │  ← 替代 DatePicker
│ DaySummary       │          │    (点击柱体选日)  │
│ EventList        │          │ DaySummary       │
│ HourlyTimeline   │          │  + reject_reasons │
│ WeekTrend        │          │ TimePeriodBar    │  ← 新增
│ 操作按钮         │          │ EventList        │
└──────────────────┘          │ HourlyWeatherTable│ ← 替代 HourlyTimeline
                              │ 操作按钮         │
                              └──────────────────┘
```

---

## Task 1: 重构 ViewpointDetail 布局

**Files:**
- Modify: [ViewpointDetail.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/ViewpointDetail.vue)
- Test: [ViewpointDetail.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/ViewpointDetail.test.js)

### 修改内容

1. **移除 imports**: DatePicker, HourlyTimeline (如有), WeekTrend（旧版）
2. **新增 imports**: TrendChart, TimePeriodBar, HourlyWeatherTable, EventIcon, useTimePeriod
3. **重组 template**: 按照目标布局重排组件顺序
4. **新增 computed**:

```javascript
// 0 分事件拒绝原因
const zeroScoreReasons = computed(() =>
  (currentDay.value?.events ?? [])
    .filter(e => e.score === 0 && e.reject_reason)
    .slice(0, 3)
)

// 时段评分
const periodScores = computed(() => {
  if (!timeline.value?.hourly) return []
  return getPeriodScores(timeline.value.hourly)
})
```

5. **日期选择**：TrendChart 的 `@select` 事件替代 DatePicker 的 `@change` 事件，调用相同的 `onDateSelect()` 方法

### 应测试的内容

- 渲染 TrendChart（或其 mock）
- 不渲染 DatePicker
- 有 timeline 数据时渲染 TimePeriodBar
- 有 0 分事件且有 reject_reason 时显示拒绝原因
- 有 timeline 数据时渲染 HourlyWeatherTable（替代 HourlyTimeline）
- 点击 TrendChart 触发日期切换

---

## Task 2: 清理 DatePicker 依赖

**Files:**
- Modify: [ViewpointDetail.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/ViewpointDetail.vue)

### 修改内容

1. 检查 DatePicker 在项目中的使用情况：

```bash
grep -rn "DatePicker" frontend/src/ --include="*.vue" --include="*.js"
```

2. 如果仅 ViewpointDetail 使用，则从 ViewpointDetail 中移除 import 和相关 computed (如 `availableDates`)
3. DatePicker 组件文件保留（其他页面可能复用），仅清理 ViewpointDetail 中的引用

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend

# 单元测试
npx vitest run src/__tests__/views/ViewpointDetail.test.js --reporter verbose

# 全量回归
npx vitest run --reporter verbose

# 视觉验证 — 启动 dev server
npm run dev
```

手动验证要点：
1. 进入详情页 → 顶部显示趋势柱状图（而非 DatePicker）
2. 点击柱体 → 切换选中日期
3. 四段时段评分正确显示
4. 逐时天气表可折叠/展开，显示温度和云量
5. 0 分事件显示 reject_reason

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.5, MG4A, MG5A, MG3B*
