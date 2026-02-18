# MC2: C 方案 — CardSwiper + PredictionCard 核心卡片

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 C 方案的核心交互组件：Swiper 卡片容器和可翻转的预测卡片 (正面视觉冲击 + 背面数据详情)。

**依赖模块:** MC1 (首页布局), M19 (ScoreRing), M20 (EventIcon), M21 (BreakdownTable, WeekTrend), M18 (useComboTags, useScoreColor)

---

## 背景

CardSwiper 和 PredictionCard 是方案 C 的灵魂组件。Swiper 管理卡片的左右滑动切换和堆叠效果；PredictionCard 是可翻转的大卡片，正面展示视觉冲击的评分概览，背面展示评分明细和七日趋势。

### 设计参考

- [10-frontend-C-card-flow.md §10.C.4 卡片设计](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)
- [10-frontend-C-card-flow.md §10.C.6 Swiper 容器](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)
- [10-frontend-C-card-flow.md §10.C.9 特有动画](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)

---

## Task 1: CardFront 卡片正面

**Files:**
- Create: `frontend/src/components/scheme-c/CardFront.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoint` | Object | — | 观景台信息 `{ id, name, elevation, location }` |
| `dayForecast` | Object | null | 当日预测 `{ date, summary, best_event, events }` |
| `comboTags` | Array | [] | 组合推荐标签 |

### 卡片正面结构 (参考 §10.C.4)

```
┌──────────────────────────────┐
│                              │  ← 渐变背景 (评分对应色)
│         🏔️ 山脉插画           │  ← 顶部装饰
│                              │
│      ─── 牛 背 山 ───         │  ← 观景台名称 (大字居中)
│        海拔 3660m             │  ← 辅助信息
│                              │
│        ╭──────────╮          │
│        │    98    │          │  ← 超大评分环 ScoreRing(xl)
│        │   推 荐   │          │
│        ╰──────────╯          │
│                              │
│   🏔️ 日出金山 90   ☁️ 云海 88 │  ← 事件图标 + 分数
│   ⭐ 观星    45   ❄️ 雾凇 -- │
│                              │
│  ┌──────────────────────┐    │
│  │ 🌄☁️ 日出金山+壮观云海  │    │  ← summary 文字
│  │ 🎯 组合日  📸摄影师推荐│    │  ← 组合标签
│  └──────────────────────┘    │
│                              │
│   07:15 - 07:45 最佳时段     │  ← 最佳时间窗口
│                              │
│          GMP 景观预测          │  ← 品牌水印
└──────────────────────────────┘
```

### 卡片视觉随评分变化 (参考 §10.C.4)

| 状态 | 背景渐变 | CSS 类名 |
|------|----------|----------|
| **Perfect (95+)** | 金色→橙色渐变 | `card--perfect` |
| **Recommended (80-94)** | 翠绿→青色渐变 | `card--recommended` |
| **Possible (50-79)** | 琥珀→浅黄渐变 | `card--possible` |
| **Not Recommended (0-49)** | 灰色→浅灰渐变 | `card--not-recommended` |

### 实现

```vue
<!-- frontend/src/components/scheme-c/CardFront.vue -->
<template>
  <div :class="['card-front', statusClass]">
    <!-- 顶部装饰区域 -->
    <div class="card-illustration">
      <span class="mountain-icon">🏔️</span>
    </div>

    <!-- 观景台名称 -->
    <div class="card-title">
      <h2>{{ viewpoint?.name ?? '加载中' }}</h2>
      <p class="elevation" v-if="viewpoint?.elevation">
        海拔 {{ viewpoint.elevation }}m
      </p>
    </div>

    <!-- 超大评分环 -->
    <div class="main-score">
      <ScoreRing
        :score="bestScore"
        size="xl"
        :showLabel="true"
        :animated="true"
      />
      <StatusBadge :score="bestScore" class="status-badge" />
    </div>

    <!-- 事件列表网格 -->
    <div class="events-grid">
      <div
        v-for="evt in displayEvents"
        :key="evt.event_type"
        class="event-item"
      >
        <EventIcon :type="evt.event_type" size="sm" />
        <span class="event-label">{{ evt.event_label }}</span>
        <span class="event-score">{{ evt.score ?? '--' }}</span>
      </div>
    </div>

    <!-- Summary + 组合标签 -->
    <div class="card-summary" v-if="dayForecast?.summary">
      <p class="summary-text">{{ dayForecast.summary }}</p>
      <div class="combo-tags" v-if="comboTags.length">
        <span
          v-for="tag in comboTags"
          :key="tag.type"
          class="combo-tag"
        >
          {{ tag.icon }} {{ tag.label }}
        </span>
      </div>
    </div>

    <!-- 最佳时段 -->
    <div class="best-window" v-if="bestTimeWindow">
      {{ bestTimeWindow }} 最佳时段
    </div>

    <!-- 品牌水印 -->
    <div class="card-watermark">GMP 景观预测</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'
import EventIcon from '@/components/event/EventIcon.vue'

const props = defineProps({
  viewpoint: { type: Object, default: null },
  dayForecast: { type: Object, default: null },
  comboTags: { type: Array, default: () => [] },
})

const { getStatus } = useScoreColor()

const bestScore = computed(() =>
  props.dayForecast?.best_event?.score ?? 0
)

const statusClass = computed(() => {
  const status = getStatus(bestScore.value)
  return `card--${status}`
})

// 展示所有事件 (有分数的 + 该观景台支持但本日无分的用 '--')
const displayEvents = computed(() =>
  props.dayForecast?.events ?? []
)

// 最佳时间窗口
const bestTimeWindow = computed(() => {
  const evt = props.dayForecast?.best_event
  if (!evt?.best_window) return null
  return `${evt.best_window.start} - ${evt.best_window.end}`
})
</script>

<style scoped>
.card-front {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg);
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: white;
  text-align: center;
  position: relative;
  overflow: hidden;
}

/* 渐变背景 — 按评分状态 */
.card--perfect {
  background: linear-gradient(160deg, #FFD700, #FF8C00);
}

.card--recommended {
  background: linear-gradient(160deg, #10B981, #06B6D4);
}

.card--possible {
  background: linear-gradient(160deg, #F59E0B, #FDE68A);
  color: var(--text-primary);
}

.card--not-recommended {
  background: linear-gradient(160deg, #6B7280, #D1D5DB);
  color: var(--text-primary);
}

.card-illustration {
  font-size: 48px;
  opacity: 0.6;
}

.card-title h2 {
  font-size: var(--text-2xl);
  font-weight: 700;
  margin: 0;
  letter-spacing: 4px;
}

.elevation {
  font-size: var(--text-sm);
  opacity: 0.7;
  margin: 4px 0 0;
}

.main-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.events-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 24px;
  width: 100%;
  max-width: 280px;
}

.event-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
}

.event-label {
  flex: 1;
  text-align: left;
}

.event-score {
  font-weight: 600;
}

.card-summary {
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  width: 100%;
  max-width: 280px;
}

.summary-text {
  font-size: var(--text-sm);
  margin: 0 0 8px;
}

.combo-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.combo-tag {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
}

.best-window {
  font-size: var(--text-sm);
  opacity: 0.8;
}

.card-watermark {
  position: absolute;
  bottom: 12px;
  font-size: var(--text-xs);
  opacity: 0.4;
}
</style>
```

**Step 1: 创建 CardFront.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/CardFront.vue
git commit -m "feat(frontend-c): add CardFront with score-based gradient, events grid, combo tags"
```

---

## Task 2: CardBack 卡片背面

**Files:**
- Create: `frontend/src/components/scheme-c/CardBack.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoint` | Object | — | 观景台信息 |
| `dayForecast` | Object | null | 当日预测 |
| `weeklyData` | Array | [] | 七日数据 (用于 WeekTrend) |

### 卡片背面结构 (参考 §10.C.4)

```
┌──────────────────────────────┐
│  牛背山 · 2月12日 评分详情     │
├──────────────────────────────┤
│  🏔️ 日出金山  90分 推荐       │
│  ┌──────────────────────┐   │
│  │ 光路通畅  ████████░ 35/35│   │
│  │ 目标可见  ███████░░ 35/40│   │
│  │ 本地晴朗  ██████░░░ 20/25│   │
│  └──────────────────────┘   │
│                              │
│  ☁️ 云海     88分 推荐       │
│  ┌──────────────────────┐   │
│  │ ...                     │   │
│  └──────────────────────┘   │
│                              │
│  七日趋势                     │
│  ╱╲     ╱╲                   │
│ ╱  ╲   ╱  ╲                  │
│╱    ╲╱╱    ╲                  │
│ 12 13 14 15 16 17 18         │
│                              │
│  [查看完整报告 →]              │
└──────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/components/scheme-c/CardBack.vue -->
<template>
  <div class="card-back">
    <!-- 标题 -->
    <div class="back-header">
      <h3>{{ viewpoint?.name }} · {{ formatDate(dayForecast?.date) }} 评分详情</h3>
    </div>

    <!-- 各事件的评分明细 -->
    <div class="breakdowns" v-if="recommendedEvents.length">
      <div
        v-for="evt in recommendedEvents"
        :key="evt.event_type"
        class="event-breakdown"
      >
        <div class="event-header">
          <EventIcon :type="evt.event_type" size="sm" />
          <span class="event-name">{{ evt.event_label }}</span>
          <span class="event-score">{{ evt.score }}分</span>
          <StatusBadge :score="evt.score" />
        </div>
        <BreakdownTable
          v-if="evt.breakdown"
          :breakdown="evt.breakdown"
          compact
        />
      </div>
    </div>

    <!-- 七日趋势 (紧凑版) -->
    <div class="trend-section" v-if="weeklyData.length">
      <h4>七日趋势</h4>
      <WeekTrend
        :daily="weeklyData"
        compact
        @select="onTrendSelect"
      />
    </div>

    <!-- 查看完整报告 -->
    <button class="detail-btn" @click="emit('view-detail')">
      查看完整报告 →
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EventIcon from '@/components/event/EventIcon.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'
import BreakdownTable from '@/components/forecast/BreakdownTable.vue'
import WeekTrend from '@/components/forecast/WeekTrend.vue'

const props = defineProps({
  viewpoint: { type: Object, default: null },
  dayForecast: { type: Object, default: null },
  weeklyData: { type: Array, default: () => [] },
})

const emit = defineEmits(['view-detail', 'date-select'])

// 只展示有 breakdown 的事件 (Recommended 以上)
const recommendedEvents = computed(() =>
  (props.dayForecast?.events ?? []).filter(e => e.score >= 50)
)

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function onTrendSelect(date) {
  emit('date-select', date)
}
</script>

<style scoped>
.card-back {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg);
  padding: 20px;
  background: var(--bg-card);
  color: var(--text-primary);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
  margin: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.event-breakdown {
  margin-bottom: 12px;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.event-name {
  font-weight: 600;
  font-size: var(--text-sm);
}

.event-score {
  font-weight: 600;
  font-size: var(--text-sm);
  margin-left: auto;
}

.trend-section h4 {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 8px;
}

.detail-btn {
  width: 100%;
  padding: 12px;
  margin-top: auto;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: white;
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.detail-btn:hover {
  background: #2563EB;
}
</style>
```

**Step 1: 创建 CardBack.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/CardBack.vue
git commit -m "feat(frontend-c): add CardBack with breakdowns, weekly trend, detail link"
```

---

## Task 3: PredictionCard 可翻转卡片

**Files:**
- Create: `frontend/src/components/scheme-c/PredictionCard.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoint` | Object | — | 观景台信息 |
| `forecast` | Object | null | 该观景台的 forecast.json 数据 |
| `selectedDate` | String | — | 当前选中日期 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `click` | viewpointId | 点击卡片 (触发翻转) |
| `view-detail` | viewpointId | 从背面点击"查看完整报告" |
| `long-press` | viewpointId | 长按 (触发截图) |

### 3D 翻转交互 (参考 §10.C.3, §10.C.9)

- 点击卡片 → Y 轴 180° 翻转，背面显示数据
- 再次点击 → 翻转回正面
- 长按 → 触发截图

### 实现

```vue
<!-- frontend/src/components/scheme-c/PredictionCard.vue -->
<template>
  <div
    class="prediction-card"
    :class="{ flipped: isFlipped }"
    @click="toggleFlip"
    @touchstart.passive="onTouchStart"
    @touchend="onTouchEnd"
    ref="cardRef"
  >
    <!-- 正面 -->
    <div class="card-face card-face--front">
      <CardFront
        :viewpoint="viewpoint"
        :day-forecast="currentDayForecast"
        :combo-tags="comboTags"
      />
    </div>

    <!-- 背面 -->
    <div class="card-face card-face--back">
      <CardBack
        :viewpoint="viewpoint"
        :day-forecast="currentDayForecast"
        :weekly-data="forecast?.daily ?? []"
        @view-detail="emit('view-detail', viewpoint?.id)"
        @date-select="onDateSelect"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useComboTags } from '@/composables/useComboTags'
import CardFront from './CardFront.vue'
import CardBack from './CardBack.vue'

const props = defineProps({
  viewpoint: { type: Object, default: null },
  forecast: { type: Object, default: null },
  selectedDate: { type: String, default: '' },
})

const emit = defineEmits(['click', 'view-detail', 'long-press'])

const cardRef = ref(null)
const isFlipped = ref(false)
let longPressTimer = null

const { computeTags } = useComboTags()

// 当日预测
const currentDayForecast = computed(() => {
  if (!props.forecast?.daily) return null
  if (props.selectedDate) {
    return props.forecast.daily.find(d => d.date === props.selectedDate) ?? props.forecast.daily[0]
  }
  return props.forecast.daily[0]
})

// 组合标签
const comboTags = computed(() => {
  const events = currentDayForecast.value?.events ?? []
  return computeTags(events)
})

function toggleFlip() {
  isFlipped.value = !isFlipped.value
  emit('click', props.viewpoint?.id)
}

// 翻转回正面 (供外部调用，如滑动切换时)
function flipToFront() {
  isFlipped.value = false
}

// 长按检测
function onTouchStart() {
  longPressTimer = setTimeout(() => {
    emit('long-press', props.viewpoint?.id)
  }, 600)
}

function onTouchEnd() {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

function onDateSelect(date) {
  // 在背面切换日期后，数据自动更新
}

defineExpose({ flipToFront, cardRef })
</script>

<style scoped>
.prediction-card {
  perspective: 1000px;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.card-face {
  backface-visibility: hidden;
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  transition: transform var(--duration-slow) var(--ease-out-expo);
}

.card-face--front {
  transform: rotateY(0deg);
}

.card-face--back {
  transform: rotateY(180deg);
}

.prediction-card.flipped .card-face--front {
  transform: rotateY(180deg);
}

.prediction-card.flipped .card-face--back {
  transform: rotateY(0deg);
}
</style>
```

**Step 1: 创建 PredictionCard.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/PredictionCard.vue
git commit -m "feat(frontend-c): add PredictionCard with 3D flip and long-press"
```

---

## Task 4: CardSwiper 滑动容器

**Files:**
- Create: `frontend/src/components/scheme-c/CardSwiper.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoints` | Array | [] | 所有观景台列表 |
| `forecasts` | Object | {} | `{ viewpointId: forecast.json }` |
| `selectedDate` | String | — | 当前选中日期 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `slide-change` | index | 卡片切换 |
| `card-click` | viewpointId | 卡片点击 |
| `view-detail` | viewpointId | 查看完整报告 |

### Swiper 配置 (参考 §10.C.6)

```javascript
const swiperOptions = {
  effect: 'cards',           // 堆叠卡片效果
  grabCursor: true,
  centeredSlides: true,
  slidesPerView: 1.15,       // 两侧微微露出相邻卡片
  spaceBetween: 16,
  pagination: { type: 'bullets', dynamicBullets: true },
}
```

### 实现

```vue
<!-- frontend/src/components/scheme-c/CardSwiper.vue -->
<template>
  <div class="card-swiper-container">
    <Swiper
      ref="swiperRef"
      :modules="[EffectCards, Pagination]"
      :effect="'cards'"
      :grab-cursor="true"
      :centered-slides="true"
      :slides-per-view="1"
      :space-between="16"
      :pagination="{ el: '.swiper-pagination', dynamicBullets: true }"
      class="card-swiper"
      @slide-change="onSlideChange"
    >
      <SwiperSlide
        v-for="vp in viewpoints"
        :key="vp.id"
        class="card-slide"
      >
        <PredictionCard
          :ref="el => cardRefs[vp.id] = el"
          :viewpoint="vp"
          :forecast="forecasts[vp.id]"
          :selected-date="selectedDate"
          @click="onCardClick(vp.id)"
          @view-detail="onViewDetail"
          @long-press="onLongPress"
        />
      </SwiperSlide>
    </Swiper>

    <!-- 左右提示 -->
    <div class="swipe-hints" v-if="viewpoints.length > 1">
      <span class="hint-left" v-if="currentIndex > 0">
        ← {{ viewpoints[currentIndex - 1]?.name }}
      </span>
      <span class="hint-right" v-if="currentIndex < viewpoints.length - 1">
        {{ viewpoints[currentIndex + 1]?.name }} →
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Swiper, SwiperSlide } from 'swiper/vue'
import { EffectCards, Pagination } from 'swiper/modules'
import 'swiper/css'
import 'swiper/css/effect-cards'
import 'swiper/css/pagination'
import PredictionCard from './PredictionCard.vue'

const props = defineProps({
  viewpoints: { type: Array, default: () => [] },
  forecasts: { type: Object, default: () => ({}) },
  selectedDate: { type: String, default: '' },
})

const emit = defineEmits(['slide-change', 'card-click', 'view-detail'])

const swiperRef = ref(null)
const cardRefs = ref({})
const currentIndex = ref(0)

function onSlideChange(swiper) {
  // 翻转回正面 (如果之前翻转了)
  const prevVp = props.viewpoints[currentIndex.value]
  if (prevVp && cardRefs.value[prevVp.id]) {
    cardRefs.value[prevVp.id].flipToFront()
  }

  currentIndex.value = swiper.activeIndex
  emit('slide-change', swiper.activeIndex)
}

function onCardClick(vpId) {
  emit('card-click', vpId)
}

function onViewDetail(vpId) {
  emit('view-detail', vpId)
}

function onLongPress(vpId) {
  // 长按截图 → MC3 实现
}

// 供外部调用: 跳转到指定卡片
function slideTo(index) {
  const swiper = swiperRef.value?.$el?.swiper
  if (swiper) {
    swiper.slideTo(index)
  }
}

defineExpose({ slideTo })
</script>

<style scoped>
.card-swiper-container {
  position: fixed;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.card-swiper {
  width: 100%;
  height: 65vh;
  pointer-events: auto;
}

.card-slide {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 左右提示 */
.swipe-hints {
  position: fixed;
  bottom: 48px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 24px;
  pointer-events: none;
  z-index: 10;
}

.hint-left,
.hint-right {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.4);
}

/* Desktop 横屏: 显示多张卡片 */
@media (min-width: 1024px) {
  .card-swiper {
    height: 70vh;
  }
}
</style>
```

**Step 1: 创建 CardSwiper.vue**

**Step 2: 验证 Swiper 工作**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
- Swiper 容器正确加载
- 卡片可以左右滑动切换
- 堆叠卡片效果 (cards effect)
- 底部显示左右提示文字

**Step 3: 提交**

```bash
git add frontend/src/components/scheme-c/CardSwiper.vue
git commit -m "feat(frontend-c): add CardSwiper with Swiper.js cards effect"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 首页加载 → 显示大卡片，背景为暗色模糊地图
2. 卡片正面 → 渐变背景色反映评分状态
3. 事件图标 + 分数 + 组合标签正确显示
4. 左右滑动 → 卡片堆叠切换效果，底部提示更新
5. 点击卡片 → 3D 翻转至背面，显示评分明细 + 七日趋势
6. 再次点击 → 翻转回正面
7. 切换卡片时 → 之前翻转的卡片自动回到正面
8. 点击"查看完整报告" → 导航至详情页

```bash
npm run build
```
