# MB2: B 方案 — 手风琴卡片与列表联动

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 B 方案的核心列表组件 ViewpointListItem (手风琴可展开卡片)，支持收起/展开两种状态及列表↔地图联动。

**依赖模块:** M16 (项目初始化), M17 (数据层), M18-M21 (公共组件), MB1 (首页布局)

---

## 背景

ViewpointListItem 是 B 方案的核心卡片组件。每张卡片代表一个观景台的当日预测摘要，点击后手风琴展开显示事件详情、评分明细和七日趋势。同一时间只有一张卡片处于展开态。

### 设计参考

- [10-frontend-B-split-list.md §10.B.4 列表卡片设计](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)
- [10-frontend-B-split-list.md §10.B.5 排序与筛选](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)
- [10-frontend-B-split-list.md §10.B.3 交互逻辑 — Intersection Observer](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)

---

## Task 1: ViewpointListItem 收起态

**Files:**
- Create: `frontend/src/components/scheme-b/ViewpointListItem.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoint` | Object | required | 观景台数据 (id, name, location, capabilities) |
| `forecast` | Object | null | 该观景台的 forecast.json 数据 |
| `selectedDate` | String | — | 当前选中日期 |
| `expanded` | Boolean | false | 是否展开 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `click` | — | 点击卡片 (用于地图联动) |
| `expand` | — | 点击展开/收起 |
| `go-detail` | — | 点击"查看完整详情" |

### 收起态布局

```
┌──────────────────────────────────────────┐
│  ScoreRing(90)  牛背山              ❯    │
│                 🏔️日出金山 ☁️云海          │
│                 日出金山+壮观云海 推荐     │
│  ┌──────┬──────┬──────┬──────┐          │
│  │🏔️ 90│☁️ 88│⭐ 45│❄️ --│          │
│  └──────┴──────┴──────┴──────┘          │
└──────────────────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/components/scheme-b/ViewpointListItem.vue -->
<template>
  <div
    class="viewpoint-list-item"
    :class="{ expanded }"
    :data-viewpoint-id="viewpoint.id"
    @click="emit('click')"
  >
    <!-- 收起态: 始终显示 -->
    <div class="collapsed-content" @click.stop="emit('expand')">
      <!-- 左侧: 总评分环 -->
      <ScoreRing
        :score="bestScore"
        size="lg"
        class="main-score"
      />

      <!-- 右侧: 信息 -->
      <div class="info">
        <div class="header-row">
          <h3 class="vp-name">{{ viewpoint.name }}</h3>
          <StatusBadge :score="bestScore" />
          <span class="expand-arrow" :class="{ rotated: expanded }">❯</span>
        </div>

        <!-- 事件图标 + summary 描述 -->
        <div class="summary-row">
          <span v-for="event in dayEvents" :key="event.event_type" class="event-mini-icon">
            <EventIcon :type="event.event_type" size="sm" />
          </span>
          <span class="summary-text">{{ todaySummary }}</span>
        </div>

        <!-- 所有事件 mini 评分一行 -->
        <div class="events-mini-row">
          <div
            v-for="event in dayEvents"
            :key="event.event_type"
            class="event-mini"
          >
            <EventIcon :type="event.event_type" size="sm" />
            <span class="mini-score">{{ event.score }}</span>
          </div>
          <!-- 不支持的事件显示 -- -->
          <div
            v-for="cap in missingCapabilities"
            :key="cap"
            class="event-mini disabled"
          >
            <EventIcon :type="cap" size="sm" />
            <span class="mini-score">--</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 展开态: 手风琴内容 -->
    <transition name="accordion">
      <div v-if="expanded" class="expanded-content">
        <!-- 事件详情卡片列表 -->
        <div class="events-detail">
          <EventCard
            v-for="event in dayEvents"
            :key="event.event_type"
            :event="event"
            show-breakdown
          />
        </div>

        <!-- 组合推荐标签 -->
        <div v-if="comboTags.length" class="combo-tags">
          <span v-for="tag in comboTags" :key="tag.type" class="combo-tag">
            {{ tag.icon }} {{ tag.label }}
          </span>
        </div>

        <!-- 七日趋势 -->
        <WeekTrend
          v-if="forecast?.daily"
          :daily="forecast.daily"
          @select="onTrendDateSelect"
          class="week-trend"
        />

        <!-- 查看完整详情 -->
        <button class="detail-btn" @click.stop="emit('go-detail')">
          查看完整详情 →
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'
import EventIcon from '@/components/event/EventIcon.vue'
import EventCard from '@/components/event/EventCard.vue'
import WeekTrend from '@/components/forecast/WeekTrend.vue'
import { useComboTags } from '@/composables/useComboTags'

const props = defineProps({
  viewpoint: { type: Object, required: true },
  forecast: { type: Object, default: null },
  selectedDate: { type: String, default: '' },
  expanded: { type: Boolean, default: false },
})

const emit = defineEmits(['click', 'expand', 'go-detail'])

const { computeTags } = useComboTags()

// 获取当日预测数据
const currentDay = computed(() => {
  if (!props.forecast?.daily) return null
  if (props.selectedDate) {
    return props.forecast.daily.find(d => d.date === props.selectedDate)
  }
  return props.forecast.daily[0]
})

// 当日事件列表
const dayEvents = computed(() =>
  currentDay.value?.events ?? []
)

// 最佳评分
const bestScore = computed(() =>
  currentDay.value?.best_event?.score ??
  dayEvents.value[0]?.score ?? 0
)

// summary 描述文本
const todaySummary = computed(() =>
  currentDay.value?.summary ?? ''
)

// 该观景台不支持但全局存在的事件类型 (显示 --)
const missingCapabilities = computed(() => {
  const active = dayEvents.value.map(e => e.event_type)
  return (props.viewpoint.capabilities ?? []).filter(
    cap => !active.includes(cap)
  )
})

// 组合推荐标签
const comboTags = computed(() =>
  computeTags(dayEvents.value)
)

function onTrendDateSelect(date) {
  // 趋势图日期选择通过 store 处理
  // 由父组件监听 date-change 事件
}
</script>

<style scoped>
.viewpoint-list-item {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  margin-bottom: 8px;
  overflow: hidden;
  transition: box-shadow var(--duration-fast);
}

.viewpoint-list-item:hover {
  box-shadow: var(--shadow-elevated);
}

.viewpoint-list-item.expanded {
  box-shadow: var(--shadow-elevated);
}

/* 收起态 */
.collapsed-content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  cursor: pointer;
}

.main-score {
  flex-shrink: 0;
}

.info {
  flex: 1;
  min-width: 0;
}

.header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.vp-name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.expand-arrow {
  margin-left: auto;
  font-size: var(--text-sm);
  color: var(--text-muted);
  transition: transform var(--duration-fast);
}

.expand-arrow.rotated {
  transform: rotate(90deg);
}

.summary-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
}

.summary-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.events-mini-row {
  display: flex;
  gap: 8px;
}

.event-mini {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.event-mini.disabled {
  opacity: 0.4;
}

.mini-score {
  font-weight: 600;
  font-size: var(--text-xs);
  color: var(--text-primary);
}

/* 展开态 */
.expanded-content {
  padding: 0 12px 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.events-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.combo-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.combo-tag {
  padding: 3px 10px;
  background: linear-gradient(135deg, #FFD700, #FF8C00);
  color: white;
  font-size: var(--text-xs);
  font-weight: 600;
  border-radius: var(--radius-full);
}

.week-trend {
  margin-top: 12px;
}

.detail-btn {
  width: 100%;
  padding: 10px;
  margin-top: 12px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: white;
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.detail-btn:hover {
  background: #2563EB;
}

/* 手风琴动画 */
.accordion-enter-active,
.accordion-leave-active {
  transition: max-height var(--duration-normal) var(--ease-out-expo),
              opacity var(--duration-fast) ease;
  overflow: hidden;
}

.accordion-enter-from,
.accordion-leave-to {
  max-height: 0;
  opacity: 0;
}

.accordion-enter-to,
.accordion-leave-from {
  max-height: 800px;
  opacity: 1;
}
</style>
```

**Step 1: 创建 ViewpointListItem.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-b/ViewpointListItem.vue
git commit -m "feat(frontend-b): add ViewpointListItem with accordion expand/collapse"
```

---

## Task 2: Intersection Observer 联动

**Files:**
- Create: `frontend/src/composables/useListMapSync.js`

### 功能

封装列表滚动↔地图联动逻辑，供 HomeView 使用。

### 实现

```javascript
// frontend/src/composables/useListMapSync.js

import { ref, onMounted, onUnmounted, nextTick } from 'vue'

/**
 * 列表↔地图联动 composable
 * @param {Object} options
 * @param {Function} options.onHighlightChange - 高亮变化回调 (viewpointId)
 * @param {String} options.selector - 卡片元素选择器 (默认 '[data-viewpoint-id]')
 * @param {Number} options.threshold - Intersection Observer 阈值 (默认 0.6)
 */
export function useListMapSync(options = {}) {
  const {
    onHighlightChange = () => {},
    selector = '[data-viewpoint-id]',
    threshold = 0.6,
  } = options

  const highlightedId = ref(null)
  let observer = null

  function setup(containerEl) {
    if (observer) observer.disconnect()

    observer = new IntersectionObserver((entries) => {
      const visible = entries.find(e => e.isIntersecting)
      if (visible) {
        const vpId = visible.target.dataset?.viewpointId
        if (vpId && vpId !== highlightedId.value) {
          highlightedId.value = vpId
          onHighlightChange(vpId)
        }
      }
    }, {
      root: containerEl,
      threshold,
    })

    // 观察所有卡片
    nextTick(() => {
      const elements = (containerEl || document).querySelectorAll(selector)
      elements.forEach(el => observer.observe(el))
    })
  }

  function scrollToItem(viewpointId) {
    const el = document.querySelector(`[data-viewpoint-id="${viewpointId}"]`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      // 闪烁高亮
      el.classList.add('flash-highlight')
      setTimeout(() => el.classList.remove('flash-highlight'), 1000)
    }
  }

  function cleanup() {
    observer?.disconnect()
    observer = null
  }

  onUnmounted(cleanup)

  return {
    highlightedId,
    setup,
    scrollToItem,
    cleanup,
  }
}
```

**Step 1: 创建 useListMapSync.js**

**Step 2: 更新 HomeView.vue 使用 useListMapSync**

在 HomeView.vue 的 `<script setup>` 中替换手动创建的 Intersection Observer 逻辑：

```javascript
import { useListMapSync } from '@/composables/useListMapSync'

const { highlightedId, setup: setupSync, scrollToItem } = useListMapSync({
  onHighlightChange: (vpId) => {
    const vp = viewpoints.value.find(v => v.id === vpId)
    if (vp && mapPanelRef.value) {
      mapPanelRef.value.panTo(vp.location.lon, vp.location.lat)
    }
  }
})
```

**Step 3: 提交**

```bash
git add frontend/src/composables/useListMapSync.js frontend/src/views/HomeView.vue
git commit -m "feat(frontend-b): add useListMapSync composable for list-map sync"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 列表卡片显示收起态 → ScoreRing + 观景台名称 + 事件 mini 评分
2. 点击卡片 → 手风琴展开 (300ms ease-out 动画)
3. 展开内容: EventCard × N + 组合标签 + WeekTrend + "查看完整详情"
4. 点击另一张卡片 → 前一张收起 + 新卡片展开
5. 滚动列表 → 地图自动 panTo 至当前可见的首个卡片
6. 点击地图 Marker → 列表 scrollIntoView + 卡片闪烁

```bash
npm run build
```
