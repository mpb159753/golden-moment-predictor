# MG6A: 日期导航增强 — 全展态 & 详情页 + 日期格式优化

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 解决两个核心问题：
1. BottomSheet 半展态有日期导航（MiniTrend），但上拉全展态后日期导航消失，无法切换日期查看详情
2. 日期显示仅有数字（如 19、20），容易看混 → 改为 `MM/DD 周X` 格式

**依赖模块:** MG5A (TrendChart), MG5B (ViewpointDetail 趋势优先布局)

---

## 背景

当前交互流程中存在日期导航丢失的问题：

```
半展态 (BottomSheet half):
┌─────────────────────────────────────┐
│  五花海                      🏔️ 90  │
│  🌄75  ☀️--  🌅75  ⭐--             │
│  19  [20]  21  22  23  24  25      │ ← MiniTrend: 可切换日期 ✅
│  90   90   86  41  83  95   0      │
│  ↑ 上拉查看完整报告                  │
└─────────────────────────────────────┘

全展态 (BottomSheet full):      ← 上拉后
┌─────────────────────────────────────┐
│  五花海  2月20日 周五                │
│  推荐观景 — 观星+日照金山+...        │
│  [事件列表 + breakdown]             │
│  ❌ 无日期导航！无法切换日期 ❌       │ ← 问题所在
└─────────────────────────────────────┘

详情页 (ViewpointDetail):
┌─────────────────────────────────────┐
│  ← 返回    河谷温泉机位       📷    │
│  [TrendChart 柱状图]                │ ← 有图表，但图标行无日期文字
│  🏔️ 🏔️ 🏔️ 🏔️ ☀️ ☀️ ☀️            │ ← 只有图标，无日期+分数
│  [DaySummary + EventList + ...]     │
└─────────────────────────────────────┘
```

### 涉及文件

| 文件 | 当前状态 | 问题 |
|------|----------|------|
| [HomeView.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/HomeView.vue) | full slot 无日期导航 | 全展态丢失日期切换能力 |
| [MiniTrend.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/MiniTrend.vue) | `dayNumber()` 仅显示日期数字 | 看不出月份和周几，容易混淆 |
| [TrendChart.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/TrendChart.vue) | 图标行仅有 EventIcon | 无日期文字和分数 |

---

## Task 1: MiniTrend 日期格式增强

**Files:**
- Modify: [MiniTrend.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/MiniTrend.vue)
- Test: [MiniTrend.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/MiniTrend.test.js)

### 修改内容

1. **将 `dayNumber()` 改为 `formatDay()` 显示 `MM/DD` + `周X`：**

```diff
- function dayNumber(dateStr) {
-     return parseInt(dateStr.split('-')[2], 10)
- }
+ const WEEKDAY_SHORT = ['日', '一', '二', '三', '四', '五', '六']
+
+ function formatDay(dateStr) {
+     const d = new Date(dateStr + 'T00:00:00+08:00')
+     const mm = String(d.getMonth() + 1).padStart(2, '0')
+     const dd = String(d.getDate()).padStart(2, '0')
+     return { date: `${mm}/${dd}`, weekday: `周${WEEKDAY_SHORT[d.getDay()]}` }
+ }
```

2. **模板调整 — 日期显示两行（MM/DD + 周X）：**

```diff
- <span class="trend-date">{{ dayNumber(day.date) }}</span>
+ <span class="trend-date">{{ formatDay(day.date).date }}</span>
+ <span class="trend-weekday">{{ formatDay(day.date).weekday }}</span>
```

3. **新增样式：**

```css
.trend-weekday {
    font-size: 10px;
    color: var(--color-text-secondary, #9CA3AF);
}
```

### 应测试的内容

- `formatDay('2026-02-20')` 返回 `{ date: '02/20', weekday: '周五' }`
- 每个日期单元格渲染日期文字和周几
- 选中态、点击事件不受影响

---

## Task 2: 全展态增加日期导航

**Files:**
- Modify: [HomeView.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/HomeView.vue) — full slot
- 无独立测试文件（集成在 HomeView 中）

### 修改内容

在 `#full` slot 的头部区域，紧接在 header 下方、EventList 上方，加入 MiniTrend 组件：

```diff
 <!-- 全展态: 七日预测 -->
 <template #full>
   <div v-if="currentViewpoint" ref="sheetContentRef" class="full-content">
     <!-- 紧凑头部 -->
     <div class="full-header">
       ...
     </div>
+    <!-- 日期导航条 -->
+    <MiniTrend
+      v-if="currentForecast?.daily"
+      :daily="currentForecast.daily"
+      :selected-date="selectedDate"
+      @select="onTrendDateSelect"
+    />
     <EventList :events="currentDay?.events ?? []" showBreakdown />
     ...
   </div>
 </template>
```

> **设计理由：** 全展态下用户需要在详细信息 (EventList、HourlyTimeline) 和日期切换之间无缝操作。将 MiniTrend 放在顶部确保日期导航始终可见，不需要滚动就能切换日期。

### 应测试的内容

- 浏览器手动验证：半展态上拉到全展态后，日期导航条仍然可见
- 点击日期可切换，EventList 和其他内容跟随更新

---

## Task 3: TrendChart 图标行增强（详情页）

**Files:**
- Modify: [TrendChart.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/TrendChart.vue)
- Test: [TrendChart.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/TrendChart.test.js)

### 修改内容

1. **`trend-icon-cell` 模板增强** — 在 EventIcon 下方增加日期标签和分数：

```html
<div
  v-for="(day, idx) in daily"
  :key="day.date"
  class="trend-icon-cell"
  :class="{ selected: day.date === selectedDate }"
  @click="$emit('select', day.date)"
>
  <EventIcon v-if="day.best_event" :event-type="day.best_event.event_type" :size="20" />
  <span class="trend-icon-date">{{ formatShortDate(day.date) }}</span>
  <span class="trend-icon-score">{{ day.best_event?.score ?? 0 }}</span>
</div>
```

2. **`formatShortDate` 方法** — 显示 `MM/DD 周X`：

```javascript
const WEEKDAY_SHORT = ['日', '一', '二', '三', '四', '五', '六']

function formatShortDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00+08:00')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}/${dd}`
}

function formatWeekday(dateStr) {
  const d = new Date(dateStr + 'T00:00:00+08:00')
  return `周${WEEKDAY_SHORT[d.getDay()]}`
}
```

> 注：TrendChart 下方图标行空间有限，日期显示 `MM/DD`，周几可选择性省略或用更小字号显示。

3. **样式调整** — 图标 cell 改为纵向布局：

```css
.trend-icon-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  min-width: 40px;
}

.trend-icon-date {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.trend-icon-score {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.trend-icon-cell.selected {
  background-color: rgba(255, 215, 0, 0.15);
  box-shadow: 0 0 0 2px rgba(255, 215, 0, 0.5);
}

.trend-icon-cell.selected .trend-icon-score {
  color: var(--color-primary);
  font-weight: 700;
}
```

### 应测试的内容

- 每个日期单元格渲染 EventIcon、日期文字、分数
- 选中态有 `.selected` class
- 点击触发 `select` 事件并传递日期
- `formatShortDate` 正确格式化为 `MM/DD`

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend

# 单元测试
npx vitest run src/__tests__/components/MiniTrend.test.js --reporter verbose
npx vitest run src/__tests__/components/TrendChart.test.js --reporter verbose

# 全量回归
npx vitest run --reporter verbose
```

### 手动验证要点

1. **MiniTrend 日期格式**: 半展态日期显示 `02/20 周五` 而非仅 `20`
2. **全展态日期导航**: 上拉展开后顶部仍有日期导航条，可点击切换日期
3. **TrendChart 图标行**: 详情页 TrendChart 底部每天显示 图标 + 日期 + 分数
4. **日期切换联动**: 点击任意日期，下方所有内容（DaySummary、EventList、TimePeriodBar 等）同步切换

---

*文档版本: v2.0 | 创建: 2026-02-19 | 更新: 2026-02-20 | 关联: 设计文档 §11.5, MG5A, MG5B*
