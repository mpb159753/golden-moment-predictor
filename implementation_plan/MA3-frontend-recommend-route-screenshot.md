# MA3: A 方案 — BestRecommendList + 线路模式 + 截图

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 BottomSheet 收起态的今日最佳推荐列表、线路模式在地图上的展示、以及 A 方案特有的截图场景。

**依赖模块:** MA1 (首页布局), MA2 (BottomSheet), M19 (ScoreRing), M20 (EventIcon), M22 (RouteLine)

---

## 背景

BottomSheet 收起态展示"今日最佳推荐"是首屏给用户的第一印象，需要简洁且信息量足够。线路模式允许用户查看多站连线关系。截图场景覆盖"地图总览截图"和"单站预测截图"两种运营需求。

### 设计参考

- [10-frontend-A-immersive-map.md §10.A.6 线路模式](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-A-immersive-map.md)
- [10-frontend-A-immersive-map.md §10.A.7 截图场景](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-A-immersive-map.md)
- [10-frontend-A-immersive-map.md §10.A.9 组件树](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-A-immersive-map.md)

---

## Task 1: BestRecommendList 今日最佳推荐

**Files:**
- Create: `frontend/src/components/scheme-a/BestRecommendList.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `recommendations` | Array | [] | `[{ viewpoint, event, score }]` 最多 3 项 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `select` | recommendation | 点击某项推荐 |

### 布局

```
≡ 今日最佳推荐
┌─────────────────────────────┐
│  🏔️ 牛背山  98分  → 日出金山 │  ← 可点击
│  ☁️ 磐羊湖  90分  → 壮观云海 │
│  ⭐ 折多山  65分  → 观星     │
└─────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/components/scheme-a/BestRecommendList.vue -->
<template>
  <div class="best-recommend">
    <h3 class="section-title">
      <span class="title-icon">≡</span>
      今日最佳推荐
    </h3>
    <ul class="recommend-list">
      <li
        v-for="rec in recommendations"
        :key="rec.viewpoint.id"
        class="recommend-item"
        @click="emit('select', rec)"
      >
        <EventIcon :type="rec.event.event_type" size="sm" />
        <span class="vp-name">{{ rec.viewpoint.name }}</span>
        <ScoreRing :score="rec.score" size="sm" :showLabel="true" />
        <span class="event-label">{{ rec.event.event_label }}</span>
        <span class="arrow">→</span>
      </li>
    </ul>
    <p v-if="recommendations.length === 0" class="empty-hint">
      暂无推荐，数据加载中...
    </p>
  </div>
</template>

<script setup>
import EventIcon from '@/components/event/EventIcon.vue'
import ScoreRing from '@/components/score/ScoreRing.vue'

const props = defineProps({
  recommendations: { type: Array, default: () => [] },
})

const emit = defineEmits(['select'])
</script>

<style scoped>
.best-recommend {
  padding: 0 16px;
}

.section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-icon {
  font-size: var(--text-lg);
}

.recommend-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recommend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.recommend-item:hover {
  background: var(--bg-primary);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}

.recommend-item:last-child {
  border-bottom: none;
}

.vp-name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--text-primary);
  min-width: 60px;
}

.event-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  flex: 1;
}

.arrow {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.empty-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
  padding: 20px 0;
}
</style>
```

**Step 1: 创建 BestRecommendList.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-a/BestRecommendList.vue
git commit -m "feat(frontend-a): add BestRecommendList for BottomSheet collapsed state"
```

---

## Task 2: 线路模式面板

**Files:**
- Create: `frontend/src/components/scheme-a/RoutePanel.vue`
- Modify: `frontend/src/views/HomeView.vue` (集成线路模式)

### 线路模式交互 (参考 §10.A.6)

1. 用户点击 MapTopBar 的"线路"按钮 → `routeMode = true`
2. 地图上绘制 `RouteLine` (各站之间的虚线+箭头)
3. BottomSheet 内容切换为 `RoutePanel`
4. 点击某站 → 地图飞至该站 + 面板滚动至该站

### RoutePanel 布局

```
┌────────────────────────────────┐
│  ≡ 理小路 (2站)                │
│  ────────────────────────────  │
│  1. 折多山    75分 🏔️          │
│     建议停留2小时观赏日出金山    │
│  ────────────────────────────  │
│  2. 牛背山    90分 🏔️ ☁️       │
│     建议停留3小时，金山+云海组合 │
└────────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/components/scheme-a/RoutePanel.vue -->
<template>
  <div class="route-panel">
    <div class="route-header">
      <h3>{{ route.name }} ({{ route.stops?.length ?? 0 }}站)</h3>
      <button class="close-btn" @click="emit('close')">✕</button>
    </div>

    <div class="stops-list">
      <div
        v-for="(stop, index) in route.stops"
        :key="stop.viewpoint_id"
        :ref="el => stopRefs[stop.viewpoint_id] = el"
        class="stop-item"
        :class="{ active: selectedStopId === stop.viewpoint_id }"
        @click="emit('select-stop', stop)"
      >
        <div class="stop-order">{{ index + 1 }}</div>
        <div class="stop-content">
          <div class="stop-title">
            <span class="stop-name">{{ stop.viewpoint_name }}</span>
            <ScoreRing :score="getStopScore(stop)" size="sm" />
            <EventIcon
              v-for="evt in getStopEvents(stop)"
              :key="evt.event_type"
              :type="evt.event_type"
              size="sm"
            />
          </div>
          <p v-if="stop.stay_note" class="stay-note">{{ stop.stay_note }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import EventIcon from '@/components/event/EventIcon.vue'

const props = defineProps({
  route: { type: Object, required: true },
  selectedStopId: { type: String, default: null },
})

const emit = defineEmits(['close', 'select-stop'])

const stopRefs = ref({})

function getStopScore(stop) {
  return stop.forecast?.daily?.[0]?.best_event?.score ?? 0
}

function getStopEvents(stop) {
  return stop.forecast?.daily?.[0]?.events?.filter(e => e.score >= 50) ?? []
}

// 供父组件调用: 滚动到指定站点
function scrollToStop(vpId) {
  const el = stopRefs.value[vpId]
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

defineExpose({ scrollToStop })
</script>

<style scoped>
.route-panel {
  padding: 0 16px;
}

.route-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.route-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: var(--text-lg);
  color: var(--text-muted);
  cursor: pointer;
}

.stops-list {
  padding: 8px 0;
}

.stop-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.stop-item:hover,
.stop-item.active {
  background: var(--bg-primary);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}

.stop-order {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: 600;
  flex-shrink: 0;
}

.stop-content {
  flex: 1;
}

.stop-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stop-name {
  font-weight: 600;
  font-size: var(--text-sm);
}

.stay-note {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-top: 4px;
}
</style>
```

**Step 1: 创建 RoutePanel.vue**

**Step 2: 在 HomeView 中集成线路模式**

线路模式时 BottomSheet 自动弹至 `half` 状态，`RoutePanel` 在 `#half` slot 中渲染（而非 `#collapsed`，避免 20% 的高度无法展示完整站点信息）：

```javascript
// HomeView.vue 中线路模式切换逻辑
function onToggleRoute(enabled) {
  routeMode.value = enabled
  if (enabled) {
    sheetState.value = 'half'  // 线路模式自动弹开面板
  } else {
    sheetState.value = 'collapsed'
  }
}
```

```vue
<!-- BottomSheet half slot 中条件渲染 -->
<template #half>
  <RoutePanel
    v-if="routeMode && selectedRoute"
    :route="selectedRoute"
    :selected-stop-id="selectedId"
    @close="routeMode = false"
    @select-stop="onRouteStopClick"
  />
  <div v-else-if="currentViewpoint" class="half-content">
    <DaySummary :day="currentDay" @click="expandSheet" />
    <EventList :events="currentDay?.events ?? []" />
  </div>
</template>

<!-- collapsed slot 保持纯粹的推荐列表 -->
<template #collapsed>
  <BestRecommendList
    :recommendations="bestRecommendations"
    @select="onRecommendSelect"
  />
</template>
```

**Step 3: 提交**

```bash
git add frontend/src/components/scheme-a/RoutePanel.vue frontend/src/views/HomeView.vue
git commit -m "feat(frontend-a): add RoutePanel for route mode in BottomSheet"
```

---

## Task 3: 截图场景

**Files:**
- Modify: `frontend/src/views/HomeView.vue` (截图逻辑增强)

### 两种截图模式 (参考 §10.A.7)

| 场景 | 触发 | 截图区域 | 处理 |
|------|------|----------|------|
| **地图总览** | 地图右下角 📸 按钮 | 全屏地图 + Marker + Logo 水印 | 临时隐藏 BottomSheet + TopBar |
| **单站预测** | **BottomSheet 全展态内 📸 按钮** | BottomSheet 内容 | 截取面板内容区域 |

### "地图总览"截图流程

```javascript
async function captureMapOverview() {
  // 1. 隐藏 UI 覆盖层
  hideUIForScreenshot()

  // 2. 等待一帧确保 DOM 更新
  await nextTick()
  await new Promise(r => setTimeout(r, 100))

  // 3. 截图
  const { capture } = useScreenshot()
  await capture(document.querySelector('.home-view'), 'gmp-map-overview.png')

  // 4. 恢复 UI
  restoreUI()
}
```

### "单站预测"截图

在 HomeView 的 BottomSheet `#full` slot 内添加 `ScreenshotBtn`，截取面板内容：

```vue
<!-- 在 HomeView.vue 的 BottomSheet #full slot 中添加 -->
<template #full>
  <div v-if="currentViewpoint" ref="sheetContentRef" class="full-content">
    <DaySummary :day="currentDay" :clickable="false" />
    <EventList :events="currentDay?.events ?? []" showBreakdown />
    <WeekTrend ... />
    <HourlyTimeline ... />
    <div class="full-actions">
      <button class="full-report-btn" @click="goToDetail">查看完整报告 →</button>
      <ScreenshotBtn
        :target="sheetContentRef"
        filename="gmp-prediction.png"
        label="📸 截图分享"
      />
    </div>
  </div>
</template>
```

### GMP Logo 水印

在地图右下角常驻 GMP 品牌 Logo，截图时包含在内:

```html
<div class="map-watermark">
  <span class="watermark-text">GMP 川西景观预测</span>
</div>
```

```css
.map-watermark {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 80;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  backdrop-filter: blur(4px);
}
```

**Step 1: 添加水印和截图场景**

**Step 2: 提交**

```bash
git add frontend/src/views/HomeView.vue
git commit -m "feat(frontend-a): add map overview screenshot and watermark"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. BottomSheet 收起态 → 显示"今日最佳推荐"列表 (≤3项)
2. 点击推荐项 → 地图飞行 + BottomSheet 弹至半展
3. 点击"线路"按钮 → 地图画线 + BottomSheet 切换为线路面板
4. 点击线路中的站点 → 地图飞行 + 面板滚动到该站
5. 地图右下角 📸 按钮 → 截取地图总览 (UI 隐藏)
6. BottomSheet 全展态截图按钮 → 截取面板内容

```bash
npm run build
```
