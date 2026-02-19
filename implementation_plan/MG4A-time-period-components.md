# MG4A: 前端 — 时段评分 + 新组件（TimePeriodBar / MiniTrend）

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现四段摄影时段评分 composable 和两个新 UI 组件（TimePeriodBar 四段评分条、MiniTrend 七日迷你趋势），为 MG4B 的 BottomSheet 半展态重构提供构建块。

**依赖模块:** M18 (composables), M19 (评分组件)

---

## 背景

设计文档 [§11.4](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/11-frontend-architecture-v2.md) 要求 BottomSheet 半展态显示"四段时段评分 + 七日趋势条"。这需要：

1. **时段划分逻辑**：将一天分为日出(5-8)、白天(8-16)、日落(16-19)、夜晚(19-5) 四段
2. **TimePeriodBar 组件**：横向显示四段评分的紧凑组件
3. **MiniTrend 组件**：七日趋势条，可点击选日期

### 组件树

```
BottomSheet (MG4B)
└── half slot (选中观景台后)
    ├── 标题行 (景点名 + 最高分 + 图标)
    ├── TimePeriodBar.vue        ← 本计划
    └── MiniTrend.vue            ← 本计划
```

---

## Task 1: useTimePeriod composable

**Files:**
- Create: `frontend/src/composables/useTimePeriod.js`
- Test: `frontend/src/__tests__/composables/useTimePeriod.test.js`

### 要实现的函数

```javascript
export function useTimePeriod() {
  /**
   * 四段摄影时段定义
   * @type {Array<{id, label, icon, start, end}>}
   */
  const periods = [...]

  /**
   * 根据 timeline hourly 数据计算每个时段的最佳事件+评分
   * @param {Array} hourly - timeline.json 的 hourly 数组
   * @returns {Array<{id, label, icon, start, end, bestScore, bestEvent, events}>}
   */
  function getPeriodScores(hourly) { ... }

  return { periods, getPeriodScores }
}
```

### 应测试的内容

- 返回 4 个时段
- 日出时段(5-8)有 sunrise_golden_mountain 活跃事件时，该时段 bestEvent 正确
- 空 hourly 数据 → 所有时段 bestScore=0, bestEvent=null
- 夜晚时段跨午夜 (19-5) → 正确包含 hour 0-4 和 19-23

---

## Task 2: TimePeriodBar 组件

**Files:**
- Create: `frontend/src/components/forecast/TimePeriodBar.vue`
- Test: `frontend/src/__tests__/components/TimePeriodBar.test.js`

### Props

| Prop | Type | Required | 说明 |
|------|------|----------|------|
| `periods` | Array | ✅ | `getPeriodScores()` 返回值 |

### 布局

四列等宽网格，每列包含 icon + label + score：

```
┌──────┬──────┬──────┬──────┐
│  🌄  │  ☀️  │  🌅  │  ⭐  │
│ 日出  │ 白天  │ 日落  │ 夜晚 │
│  85  │  --  │  72  │  60  │
└──────┴──────┴──────┴──────┘
```

0 分时段显示 `--`。使用 [useScoreColor](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/composables/useScoreColor.js) 为分数着色。

### 应测试的内容

- 渲染 4 个 `.period-cell`
- 显示时段 label 和 icon
- 显示分数（bestScore > 0 时）
- 0 分时段显示 `--`

---

## Task 3: MiniTrend 组件

**Files:**
- Create: `frontend/src/components/forecast/MiniTrend.vue`
- Test: `frontend/src/__tests__/components/MiniTrend.test.js`

### Props

| Prop | Type | Required | 说明 |
|------|------|----------|------|
| `daily` | Array | ✅ | forecast.json 的 daily 数组 |
| `selectedDate` | String | — | 当前选中日期 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `select` | dateString | 点击日期时触发 |

### 布局

横向 7 格迷你趋势条：

```
┌──┬──┬──┬──┬──┬──┬──┐
│19│20│21│22│23│24│25│  ← 日期
│30│39│50│90│55│30│ 5│  ← best_event.score
└──┴──┴──┴──┴──┴──┴──┘
              ▲
          selected (蓝色高亮)
```

分数使用 [useScoreColor](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/composables/useScoreColor.js) 着色。选中日期高亮。

### 应测试的内容

- 渲染 N 个 `.trend-day`（N = daily 数组长度）
- 显示日期数字
- 显示分数
- 点击触发 `select` 事件并传递日期字符串
- 选中日期有 `.selected` class

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend

# 单元测试
npx vitest run src/__tests__/composables/useTimePeriod.test.js --reporter verbose
npx vitest run src/__tests__/components/TimePeriodBar.test.js --reporter verbose
npx vitest run src/__tests__/components/MiniTrend.test.js --reporter verbose

# 全量回归
npx vitest run --reporter verbose
```

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.4, M18, M19*
