# M21: 前端预测展示组件 (DaySummary / WeekTrend / HourlyTimeline / BreakdownTable)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现四个预测展示公共组件，覆盖单日摘要、七日趋势、逐时时间线和评分明细表。

**依赖模块:** M16 (项目初始化), M18 (useScoreColor, useComboTags), M19 (ScoreRing), M20 (EventIcon)

---

## 背景

预测展示组件在**详情页** (ViewpointDetail / RouteDetail) 中被三方案共用复用。

### 设计参考

- [10-frontend-common.md §10.0.3 DaySummary/WeekTrend/HourlyTimeline/BreakdownTable](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)

---

## Task 1: DaySummary 单日摘要

**Files:**
- Create: `frontend/src/components/forecast/DaySummary.vue`
- Test: `frontend/src/__tests__/components/DaySummary.test.js`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `day` | Object | — | forecast.json 中 daily 数组的一项 |
| `clickable` | Boolean | true | 点击时 emit 'select' 事件 |

### day 对象结构

```javascript
// 来自 forecast.json → daily[n]
{
  date: '2026-02-12',
  summary: '🌄☁️ 日照金山+壮观云海 — 绝佳组合日',
  best_event: { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
  events: [ /* ...EventCard 格式... */ ]
}
```

### 实现结构

```
┌──────────────────────────────┐
│  2月12日 周三                │
│  🌄☁️ 日照金山+壮观云海       │
│  ┌──────┐ ┌──────┐ ┌──────┐ │
│  │🏔️ 90 │ │☁️ 90 │ │⭐ 45 │ │
│  │ 推荐  │ │ 推荐  │ │ 一般 │ │
│  └──────┘ └──────┘ └──────┘ │
│  [🎯 组合日] [📸 摄影师推荐]  │
└──────────────────────────────┘
```

### 实现

```vue
<template>
  <div
    class="day-summary"
    :class="{ 'day-summary--clickable': clickable }"
    @click="clickable && $emit('select', day.date)"
  >
    <!-- 日期 -->
    <div class="day-summary__date">
      {{ formatDate(day.date) }}
    </div>

    <!-- 摘要文字 -->
    <div class="day-summary__text">{{ day.summary }}</div>

    <!-- 事件评分网格 -->
    <div class="day-summary__events">
      <div
        v-for="event in day.events"
        :key="event.event_type"
        class="day-summary__event-chip"
      >
        <EventIcon :eventType="event.event_type" :size="20" />
        <ScoreRing :score="event.score" size="sm" />
        <StatusBadge :status="event.status" />
      </div>
    </div>

    <!-- 组合推荐标签 -->
    <div v-if="comboTags.length" class="day-summary__tags">
      <span v-for="tag in comboTags" :key="tag.type" class="day-summary__tag">
        {{ tag.icon }} {{ tag.label }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useComboTags } from '@/composables/useComboTags'
import EventIcon from '@/components/event/EventIcon.vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'

const props = defineProps({
  day: { type: Object, required: true },
  clickable: { type: Boolean, default: true },
})

defineEmits(['select'])

const { computeTags } = useComboTags()
const comboTags = computed(() => computeTags(props.day.events))

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00+08:00')
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.getMonth() + 1}月${d.getDate()}日 ${weekdays[d.getDay()]}`
}
</script>
```

---

## Task 2: WeekTrend 七日趋势图

**Files:**
- Create: `frontend/src/components/forecast/WeekTrend.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `daily` | Array | [] | forecast.json 的 daily 数组 |
| `height` | Number | 280 | 图表高度 (px) |

### ECharts 配置要点

- **图表类型:** 面积折线图 (Area Line)
- **X 轴:** 日期 (格式化为"MM-DD 周X")
- **Y 轴:** 0-100 评分
- **系列:** 每个 event_type 一条线，颜色对应 EventIcon 主色
- **交互:** hover 显示 tooltip，点击触发 `select` 事件

```javascript
// ECharts 按需引入
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])
```

### 实现

```vue
<template>
  <div ref="chartRef" :style="{ width: '100%', height: `${height}px` }" />
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
// ECharts 按需引入 (见上方)

const props = defineProps({
  daily: { type: Array, default: () => [] },
  height: { type: Number, default: 280 },
})

const emit = defineEmits(['select'])

const chartRef = ref(null)
let chart = null

// 事件颜色映射 (与 EventIcon 一致)
const EVENT_COLORS = {
  sunrise_golden_mountain: '#FF8C00',
  sunset_golden_mountain: '#FF4500',
  cloud_sea: '#87CEEB',
  stargazing: '#4A0E8F',
  frost: '#B0E0E6',
  snow_tree: '#E0E8EF',
  ice_icicle: '#ADD8E6',
}

function buildOption() {
  // 收集所有出现过的 event_type
  const eventTypes = new Set()
  props.daily.forEach(day => {
    day.events.forEach(e => eventTypes.add(e.event_type))
  })

  const dates = props.daily.map(d => d.date)

  const series = [...eventTypes].map(type => ({
    name: type,
    type: 'line',
    smooth: true,
    areaStyle: { opacity: 0.1 },
    itemStyle: { color: EVENT_COLORS[type] || '#9CA3AF' },
    data: props.daily.map(day => {
      const event = day.events.find(e => e.event_type === type)
      return event ? event.score : null
    }),
  }))

  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    grid: { top: 10, right: 20, bottom: 40, left: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', min: 0, max: 100 },
    series,
  }
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())
  chart.on('click', params => {
    emit('select', props.daily[params.dataIndex]?.date)
  })
})

watch(() => props.daily, () => {
  chart?.setOption(buildOption())
}, { deep: true })

onUnmounted(() => chart?.dispose())
</script>
```

---

## Task 3: HourlyTimeline 逐时时间线

**Files:**
- Create: `frontend/src/components/forecast/HourlyTimeline.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `hourly` | Array | [] | timeline.json 的 hourly 数组 |

### hourly 数据结构

```javascript
// 来自 timeline_YYYY-MM-DD.json → hourly[n]
{
  hour: 6,
  time: '06:00',
  safety_passed: true,
  weather: { temperature_2m: -3.2, cloud_cover_total: 25, ... },
  events_active: [
    { event_type: 'cloud_sea', status: 'Active', score: 90 }
  ]
}
```

### 实现

水平滚动时间轴 + 彩色事件区间条:

```
  04:00  05:00  06:00  07:00  08:00  09:00  10:00  ...
  ──────────────────────────────────────────────────
               ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓             云海 (06-09)
                      ▓▓▓▓▓▓▓▓▓▓                   日出金山 (07-08)
  ──────────────────────────────────────────────────
  天气: -3°C  ☀️ 少云
```

- 每个事件用对应主色的彩色条显示其 active 时段
- 当前时刻有指示线
- 底部显示天气概要

---

## Task 4: BreakdownTable 评分明细表

**Files:**
- Create: `frontend/src/components/forecast/BreakdownTable.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `breakdown` | Object | {} | score_breakdown 对象 |
| `totalScore` | Number | 0 | 总分 |
| `totalMax` | Number | 100 | 满分 |

### breakdown 数据结构

```javascript
// 来自 forecast.json → events[n].score_breakdown
{
  light_path:     { score: 35, max: 35 },
  target_visible: { score: 35, max: 40 },
  local_clear:    { score: 20, max: 25 },
}
```

### 实现

使用 ScoreBar 组件渲染每行:

```vue
<template>
  <div class="breakdown-table">
    <div v-for="(item, key) in breakdown" :key="key" class="breakdown-table__row">
      <ScoreBar
        :label="dimensionName(key)"
        :score="item.score"
        :max="item.max"
      />
    </div>
    <div class="breakdown-table__total">
      <span>总分</span>
      <span class="breakdown-table__total-value">
        {{ totalScore }} / {{ totalMax }}
      </span>
    </div>
  </div>
</template>

<script setup>
import ScoreBar from '@/components/score/ScoreBar.vue'

defineProps({
  breakdown: { type: Object, default: () => ({}) },
  totalScore: { type: Number, default: 0 },
  totalMax: { type: Number, default: 100 },
})

/** 评分维度 key → 中文名映射 */
const DIMENSION_NAMES = {
  light_path: '光路通畅',
  target_visible: '目标可见',
  local_clear: '本地晴朗',
  gap: '海拔差',
  density: '云层厚度',
  wind: '风力条件',
  temperature: '温度条件',
  humidity: '湿度条件',
  stability: '稳定性',
  precipitation: '降水条件',
  moon_phase: '月相',
  visibility: '能见度',
  cloud_cover: '云量',
}

function dimensionName(key) {
  return DIMENSION_NAMES[key] || key
}
</script>
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/components/DaySummary.test.js
```
