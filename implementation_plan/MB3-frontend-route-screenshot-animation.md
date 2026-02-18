# MB3: B 方案 — 线路模式、截图与动画

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 B 方案的线路列表卡片、截图场景和方案特有动画效果。

**依赖模块:** MB1 (首页布局), MB2 (手风琴卡片), M19-M22 (公共组件), M24 (导出组件)

---

## 背景

B 方案的线路模式通过标签切换进入，列表替换为线路卡片。截图功能利用列表天然的"排行榜"布局生成适合分享的图片。动画方面主要包含卡片入场 stagger、手风琴展开、排序 FLIP 等效果。

### 设计参考

- [10-frontend-B-split-list.md §10.B.7 线路模式](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)
- [10-frontend-B-split-list.md §10.B.8 截图场景](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)
- [10-frontend-B-split-list.md §10.B.9 特有动画](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)

---

## Task 1: RouteListItem 线路卡片

**Files:**
- Create: `frontend/src/components/scheme-b/RouteListItem.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `route` | Object | required | 线路数据 (id, name, stops[]) |
| `selectedDate` | String | '' | 当前选中日期 (§10.B.7 卡片显示日期) |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `click` | — | 点击线路卡片 |
| `stop-click` | stop | 点击某一站 |

### 布局

```
┌──────────────────────────────────────────┐
│  理小路 (2站)                    📅 2/12 │
├──────────────────────────────────────────┤
│  ① 折多山  ──────→  ② 牛背山            │
│    🏔️ 75            🏔️☁️ 90             │
│    停留2h            停留3h               │
├──────────────────────────────────────────┤
│  最佳停靠建议: 牛背山 (90分) → 云海+金山  │
└──────────────────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/components/scheme-b/RouteListItem.vue -->
<template>
  <div class="route-list-item" @click="emit('click')">
    <!-- 头部: 线路名称 + 站数 + 日期 -->
    <div class="route-header">
      <h3 class="route-name">{{ route.name }}</h3>
      <span class="stop-count">({{ stops.length }}站)</span>
      <span class="route-date">📅 {{ formatDate(selectedDate) }}</span>
    </div>

    <!-- 站点连线 -->
    <div class="stops-flow">
      <div
        v-for="(stop, index) in stops"
        :key="stop.viewpoint_id"
        class="stop-node"
        @click.stop="emit('stop-click', stop)"
      >
        <!-- 序号圆圈 -->
        <div class="stop-order">{{ index + 1 }}</div>

        <!-- 站点信息 -->
        <div class="stop-info">
          <span class="stop-name">{{ stop.name }}</span>
          <div class="stop-events">
            <EventIcon
              v-for="event in getStopEvents(stop)"
              :key="event.event_type"
              :type="event.event_type"
              size="sm"
            />
            <span class="stop-score">{{ getStopScore(stop) }}</span>
          </div>
          <span v-if="stop.stay_hours" class="stop-duration">
            停留{{ stop.stay_hours }}h
          </span>
        </div>

        <!-- 连接线 (最后一站不显示) -->
        <div v-if="index < stops.length - 1" class="connector">
          <span class="connector-line">──→</span>
        </div>
      </div>
    </div>

    <!-- 底部: 最佳停靠建议 -->
    <div v-if="bestStop" class="best-stop-suggestion">
      最佳停靠建议: <strong>{{ bestStop.name }}</strong>
      ({{ getStopScore(bestStop) }}分)
      <span v-if="bestStopSummary"> → {{ bestStopSummary }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EventIcon from '@/components/event/EventIcon.vue'
import { useViewpointStore } from '@/stores/viewpoints'

const props = defineProps({
  route: { type: Object, required: true },
  selectedDate: { type: String, default: '' },
})

const emit = defineEmits(['click', 'stop-click'])

const vpStore = useViewpointStore()

const stops = computed(() => props.route.stops ?? [])

function getStopScore(stop) {
  const forecast = vpStore.forecasts[stop.viewpoint_id]
  if (!forecast) return 0
  const today = forecast.daily?.[0]
  return today?.best_event?.score ?? 0
}

function getStopEvents(stop) {
  const forecast = vpStore.forecasts[stop.viewpoint_id]
  if (!forecast) return []
  const today = forecast.daily?.[0]
  return today?.events ?? []
}

// 最佳停靠站 (评分最高的站)
const bestStop = computed(() => {
  if (!stops.value.length) return null
  return stops.value.reduce((best, stop) =>
    getStopScore(stop) > getStopScore(best) ? stop : best
  )
})

const bestStopSummary = computed(() => {
  if (!bestStop.value) return ''
  const forecast = vpStore.forecasts[bestStop.value.viewpoint_id]
  return forecast?.daily?.[0]?.summary ?? ''
})

// 日期格式化 (§10.B.7)
function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style scoped>
.route-list-item {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  margin-bottom: 8px;
  padding: 12px;
  cursor: pointer;
  transition: box-shadow var(--duration-fast);
}

.route-list-item:hover {
  box-shadow: var(--shadow-elevated);
}

.route-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 12px;
}

.route-name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.stop-count {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* 日期显示 (§10.B.7) */
.route-date {
  margin-left: auto;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.stops-flow {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.stop-node {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.stop-order {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 600;
  flex-shrink: 0;
}

.stop-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stop-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.stop-events {
  display: flex;
  align-items: center;
  gap: 2px;
}

.stop-score {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
}

.stop-duration {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.connector {
  display: flex;
  align-items: center;
  margin: 0 4px;
}

.connector-line {
  color: var(--text-muted);
  font-size: var(--text-sm);
  white-space: nowrap;
}

.best-stop-suggestion {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.best-stop-suggestion strong {
  color: var(--color-primary);
}
</style>
```

**Step 1: 创建 RouteListItem.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-b/RouteListItem.vue
git commit -m "feat(frontend-b): add RouteListItem with stop flow layout"
```

---

## Task 2: 排行榜截图

**Files:**
- Create: `frontend/src/components/scheme-b/RankingScreenshot.vue`

### 功能

"排行榜"截图是 B 方案最适合的截图类型——多地对比一目了然。自动截取前 5 个卡片生成分享图片。

### 布局

```
┌──────────────────────────────┐
│  2月12日 川西观景推荐排行      │
│  ──────────────────────────  │
│  🥇 牛背山  98分 金山+云海   │
│  🥈 磐羊湖  90分 云海       │
│  🥉 折多山  75分 金山       │
│  4. 达古冰川  68分 观星      │
│  5. ...                     │
│              GMP 景观预测引擎 │
└──────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/components/scheme-b/RankingScreenshot.vue -->
<template>
  <div>
    <!-- 截图按钮 -->
    <button class="ranking-screenshot-btn" @click="captureRanking">
      📸 排行截图
    </button>

    <!-- 隐藏的截图模板 (仅截图时渲染) -->
    <div v-if="capturing" ref="captureRef" class="ranking-template">
      <div class="ranking-header">
        <h2>{{ formatDate(selectedDate) }} 川西观景推荐排行</h2>
        <div class="ranking-divider" />
      </div>

      <ol class="ranking-list">
        <li
          v-for="(vp, index) in topViewpoints"
          :key="vp.id"
          class="ranking-item"
        >
          <span class="ranking-medal">{{ getMedal(index) }}</span>
          <span class="ranking-name">{{ vp.name }}</span>
          <ScoreRing :score="vp.score" size="sm" />
          <span class="ranking-summary">{{ vp.summary }}</span>
        </li>
      </ol>

      <div class="ranking-footer">
        <span class="brand">GMP 景观预测引擎</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import { useScreenshot } from '@/composables/useScreenshot'

const props = defineProps({
  viewpoints: { type: Array, default: () => [] },
  forecasts: { type: Object, default: () => ({}) },
  selectedDate: { type: String, default: '' },
})

const { capture } = useScreenshot()

const captureRef = ref(null)
const capturing = ref(false)

// 前 5 个最高分观景台
const topViewpoints = computed(() => {
  const results = []
  for (const vp of props.viewpoints) {
    const forecast = props.forecasts[vp.id]
    if (!forecast) continue
    const today = forecast.daily?.[0]
    if (!today) continue
    const bestEvent = today.best_event || today.events?.[0]
    if (bestEvent) {
      results.push({
        id: vp.id,
        name: vp.name,
        score: bestEvent.score,
        summary: today.summary ?? '',
      })
    }
  }
  return results
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
})

function getMedal(index) {
  const medals = ['🥇', '🥈', '🥉']
  return medals[index] ?? `${index + 1}.`
}

function formatDate(dateStr) {
  if (!dateStr) return '今日'
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

async function captureRanking() {
  capturing.value = true
  await nextTick()
  await capture(captureRef.value, 'gmp-ranking.png')
  capturing.value = false
}
</script>

<style scoped>
.ranking-screenshot-btn {
  padding: 6px 12px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: var(--bg-card);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.ranking-screenshot-btn:hover {
  background: var(--bg-primary);
  box-shadow: var(--shadow-card);
}

/* 截图模板 (位于屏幕外渲染) */
.ranking-template {
  position: fixed;
  left: -9999px;
  top: 0;
  width: 375px;
  padding: 24px;
  background: linear-gradient(180deg, #F8FAFC 0%, #EEF2FF 100%);
  font-family: var(--font-sans);
}

.ranking-header h2 {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.ranking-divider {
  height: 2px;
  background: linear-gradient(90deg, var(--color-primary), transparent);
  margin-bottom: 16px;
}

.ranking-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.ranking-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.ranking-medal {
  font-size: var(--text-lg);
  width: 32px;
  text-align: center;
}

.ranking-name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.ranking-summary {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  max-width: 120px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ranking-footer {
  margin-top: 16px;
  text-align: right;
}

.brand {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-weight: 500;
}
</style>
```

**Step 1: 创建 RankingScreenshot.vue**

**Step 2: 在 HomeView 中集成排行截图按钮**

在 ListTopBar 旁或列表顶部添加 `<RankingScreenshot />` 组件：

```javascript
import RankingScreenshot from '@/components/scheme-b/RankingScreenshot.vue'
```

```html
<RankingScreenshot
  :viewpoints="viewpoints"
  :forecasts="forecasts"
  :selected-date="selectedDate"
/>
```

**Step 3: 提交**

```bash
git add frontend/src/components/scheme-b/RankingScreenshot.vue frontend/src/views/HomeView.vue
git commit -m "feat(frontend-b): add ranking screenshot for list comparison sharing"
```

---

## Task 3: 方案特有动画

**Files:**
- Modify: `frontend/src/components/scheme-b/ViewpointListItem.vue`
- Modify: `frontend/src/views/HomeView.vue`

### 动画清单 (参考 §10.B.9)

| 动画 | 效果 | 时机 | 实现方式 |
|------|------|------|----------|
| **卡片入场** | 从下方 stagger 滑入 | 列表初始加载 | GSAP staggerFrom |
| **手风琴展开** | 高度渐变 + 内容淡入 | 点击卡片 | CSS transition (已在 MB2 实现) |
| **地图 panTo** | 平滑移动 + Marker 弹跳 | 列表滚动联动 | AMap 原生动画 (已在 MB1 实现) |
| **列表 scrollTo** | 平滑滚动 + 目标卡片闪烁 | 点击 Marker | scrollIntoView + CSS animation (已在 MB1 实现) |
| **排序切换** | 卡片 FLIP 动画重排 | 切换排序方式 | Vue TransitionGroup + FLIP |
| **日期切换** | 评分数字 CountUp + 颜色渐变 | 切换日期 | GSAP CountUp |

### 卡片入场 Stagger 动画

```javascript
// HomeView.vue onMounted 中，数据加载完成后
import gsap from 'gsap'

async function animateCardEntrance() {
  await nextTick()
  const cards = document.querySelectorAll('.viewpoint-list-item')
  gsap.fromTo(cards, {
    y: 40,
    opacity: 0,
  }, {
    y: 0,
    opacity: 1,
    duration: 0.4,
    stagger: 0.08,
    ease: 'power2.out',
  })
}
```

### 排序 FLIP 动画

在 HomeView 的列表区域使用 Vue 的 `<TransitionGroup>` 实现排序切换动画：

```vue
<!-- 替换原先的普通 div -->
<TransitionGroup name="flip-list" tag="div" class="viewpoint-list">
  <ViewpointListItem
    v-for="vp in sortedViewpoints"
    :key="vp.id"
    ...
  />
</TransitionGroup>
```

```css
.flip-list-move {
  transition: transform 0.5s var(--ease-out-expo);
}

.flip-list-enter-active,
.flip-list-leave-active {
  transition: all 0.3s ease;
}

.flip-list-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.flip-list-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.flip-list-leave-active {
  position: absolute;
}
```

### 日期切换 CountUp

在 ViewpointListItem 中，当 `selectedDate` 变化时，对评分数字使用 CountUp 效果：

```javascript
// ViewpointListItem.vue
import gsap from 'gsap'
import { watch } from 'vue'

const scoreDisplay = ref(0)

watch(bestScore, (newVal, oldVal) => {
  gsap.to(scoreDisplay, {
    value: newVal,
    duration: 0.6,
    ease: 'power2.out',
    onUpdate: () => {
      scoreDisplay.value = Math.round(scoreDisplay.value)
    }
  })
}, { immediate: true })
```

**Step 1: 添加入场 stagger 动画**

在 HomeView 的 `onMounted` 中追加 `animateCardEntrance()` 调用。

**Step 2: 添加排序 FLIP 动画**

将列表容器改为 `<TransitionGroup>`，添加对应 CSS。

**Step 3: 添加日期切换 CountUp**

在 ViewpointListItem 中添加 GSAP CountUp 逻辑。

**Step 4: 提交**

```bash
git add frontend/src/components/scheme-b/ViewpointListItem.vue frontend/src/views/HomeView.vue
git commit -m "feat(frontend-b): add stagger entrance, FLIP sort, and CountUp animations"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 首次加载 → 卡片从下方依次滑入 (stagger 0.08s)
2. 切换排序方式 → 卡片 FLIP 动画平滑重排
3. 切换日期 → 评分数字 CountUp 过渡 + 颜色渐变
4. 切换"线路"标签 → 显示线路卡片列表
5. 线路卡片 → 显示站点连线 + 最佳停靠建议
6. 📸 排行截图 → 生成带🥇🥈🥉的排行榜图片
7. 地图+列表 联合截图 → 捕获完整视口

```bash
npm run build
```
