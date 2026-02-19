# MG4B: 前端 — Marker 图标徽章 + BottomSheet 半展态重构

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 改造地图 Marker（显示分数 + 事件图标 emoji 徽章），重构 HomeView 的 BottomSheet 半展态内容（标题行 + 0 分原因 + 四段时段 + 七日趋势）。

**依赖模块:** MG3A (timeline weather), MG3B (reject_reason + eventMeta), MG4A (TimePeriodBar + MiniTrend + useTimePeriod)

---

## 背景

对应设计文档 [§11.3 地图 Marker](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/11-frontend-architecture-v2.md) 和 [§11.4 BottomSheet](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/11-frontend-architecture-v2.md)：

| 问题 | 现状 | 目标 |
|------|------|------|
| Marker 只有数字 | 显示 `75` | 显示 `☁️ 92`（emoji 徽章 + 分数） |
| 半展态无丰富内容 | DaySummary + EventList | 标题行 + 0 分原因 + 四段时段 + 七日趋势 |

---

## Task 1: ViewpointMarker 添加图标徽章

**Files:**
- Modify: [ViewpointMarker.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/map/ViewpointMarker.vue)
- Test: [ViewpointMarker.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/ViewpointMarker.test.js)

### 要新增的 Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `bestEvent` | String | null | 最佳事件类型 (如 `sunrise_golden_mountain`) |

### 修改内容

1. 在组件内定义 `EVENT_EMOJI` 映射表（因为 AMap Marker 使用 HTML 字符串，无法用 Vue 组件渲染 SVG）：

```javascript
const EVENT_EMOJI = {
  clear_sky: '☀️',
  sunrise_golden_mountain: '🏔️',
  sunset_golden_mountain: '🏔️',
  cloud_sea: '☁️',
  stargazing: '⭐',
  frost: '❄️',
  snow_tree: '❄️',
  ice_icicle: '❄️',
}
```

2. 修改 `createContent()` 中的默认态 HTML，在分数前添加 emoji 徽章

### 应测试的内容

- bestEvent 提供时，`createContent()` 返回的 HTML 包含对应 emoji
- bestEvent 为 null 时，仅显示数字（无回归）
- bestEvent 为未知类型时，不显示 emoji

---

## Task 2: HomeView 传递 bestEvent prop

**Files:**
- Modify: [HomeView.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/HomeView.vue)
- Test: [HomeView.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/HomeView.test.js)

### 修改内容

1. 新增 `getBestEvent(vpId)` 函数（类似现有 `getBestScore()`）：

```javascript
function getBestEvent(vpId) {
  const forecast = vpStore.forecasts[vpId]
  if (!forecast) return null
  const day = forecast.daily?.find(d => d.date === selectedDate.value)
    ?? forecast.daily?.[0]
  return day?.best_event?.event_type ?? null
}
```

2. 将 `:best-event="getBestEvent(vp.id)"` 传递给 `ViewpointMarker`

---

## Task 3: 重构 BottomSheet 半展态内容

**Files:**
- Modify: [HomeView.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/HomeView.vue)
- Test: [HomeView.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/HomeView.test.js)

### 修改 `#half` slot 内容

```
┌────────────────────────────────────┐
│ ① 标题行: 景点名          🏔️ 92  │
│ ② 0分原因: ❌☁️光路阻断  ❌⭐月光 │
│ ③ TimePeriodBar                    │
│    🌄日出 85 │ ☀️白天 -- │ ...     │
│ ④ MiniTrend                        │
│    19  20  21  22  23  24  25      │
│    30  39  50  90  55  30   5      │
└────────────────────────────────────┘
```

### 新增 computed

```javascript
import TimePeriodBar from '@/components/forecast/TimePeriodBar.vue'
import MiniTrend from '@/components/forecast/MiniTrend.vue'
import { useTimePeriod } from '@/composables/useTimePeriod'

const { getPeriodScores } = useTimePeriod()

// 0 分事件拒绝原因 (最多 3 个)
const zeroScoreReasons = computed(() =>
  (currentDay.value?.events ?? [])
    .filter(e => e.score === 0 && e.reject_reason)
    .slice(0, 3)
)

// 时段评分 (依赖 timeline)
const periodScores = computed(() => {
  if (!currentTimeline.value?.hourly) return []
  return getPeriodScores(currentTimeline.value.hourly)
})
```

### 应测试的内容

- 选中观景台后半展态显示景点名和最高分
- 有 0 分事件且存在 reject_reason 时，显示拒绝原因
- 有 timeline 数据时显示 TimePeriodBar
- 有 forecast.daily 时显示 MiniTrend
- 点击 MiniTrend 日期切换 selectedDate

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend

# 单元测试
npx vitest run src/__tests__/components/ViewpointMarker.test.js --reporter verbose
npx vitest run src/__tests__/views/HomeView.test.js --reporter verbose

# 全量回归
npx vitest run --reporter verbose

# 视觉验证 — 启动 dev server
npm run dev
```

手动验证要点：
1. 点击地图 Marker → Marker 显示 emoji + 分数
2. 半展态标题行显示景点名 + 最高分 + 图标
3. 有 0 分事件时显示拒绝原因标签
4. 四段时段评分正确显示

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.3, §11.4, MG3, MG4A*
