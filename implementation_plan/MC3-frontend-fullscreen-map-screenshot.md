# MC3: C 方案 — 全屏地图 + 截图场景

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 C 方案的全屏地图模态 (点击🗺️入口打开) 和两种截图场景 (预测卡片截图 + 对比组图截图)。

**依赖模块:** MC1 (首页布局), MC2 (核心卡片), M22 (AMapContainer, ViewpointMarker), M24 (ScreenshotBtn, useScreenshot)

---

## 背景

全屏地图是卡片流模式下查看所有观景台位置关系的补充入口。截图是 C 方案的核心优势——卡片本身就是完美的分享图，支持单卡截图和多卡对比组图。

### 设计参考

- [10-frontend-C-card-flow.md §10.C.5 背景地图 → 全屏地图入口](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)
- [10-frontend-C-card-flow.md §10.C.8 截图场景](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)

---

## Task 1: FullscreenMap 全屏地图

**Files:**
- Create: `frontend/src/components/scheme-c/FullscreenMap.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoints` | Array | [] | 所有观景台 |
| `forecasts` | Object | {} | 预测数据 |
| `selectedDate` | String | — | 当前日期 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `close` | — | 关闭全屏地图 |
| `select-viewpoint` | viewpointId | 点击 Marker 选择观景台 |

### 交互流程 (参考 §10.C.5)

右上角 🗺️ 按钮点击后:
1. 背景模糊层淡出 (300ms)
2. 卡片缩小并淡出 (300ms)
3. 地图变为可交互模式
4. 所有 Marker 出现 + 评分
5. 点击 Marker → 关闭地图 → 自动滑动到对应卡片

### 实现

```vue
<!-- frontend/src/components/scheme-c/FullscreenMap.vue -->
<template>
  <Transition name="map-modal">
    <div class="fullscreen-map">
      <!-- 关闭按钮 -->
      <button class="close-btn" @click="emit('close')">
        ✕
      </button>

      <!-- 地图容器 -->
      <AMapContainer
        height="100vh"
        :map-options="mapOptions"
        @ready="onMapReady"
      />

      <!-- Marker 覆盖层 -->
      <template v-if="mapInstance">
        <ViewpointMarker
          v-for="vp in viewpoints"
          :key="vp.id"
          :viewpoint="vp"
          :score="getBestScore(vp.id)"
          :selected="false"
          @click="onMarkerClick(vp)"
        />
      </template>
    </div>
  </Transition>
</template>

<script setup>
import { ref } from 'vue'
import AMapContainer from '@/components/map/AMapContainer.vue'
import ViewpointMarker from '@/components/map/ViewpointMarker.vue'

const props = defineProps({
  viewpoints: { type: Array, default: () => [] },
  forecasts: { type: Object, default: () => ({}) },
  selectedDate: { type: String, default: '' },
})

const emit = defineEmits(['close', 'select-viewpoint'])

const mapInstance = ref(null)

const mapOptions = {
  zoom: 8,
  center: [102.0, 30.5],
  mapStyle: 'amap://styles/dark',
  zooms: [6, 15],
}

function onMapReady(map) {
  mapInstance.value = map
}

function getBestScore(vpId) {
  const forecast = props.forecasts[vpId]
  if (!forecast) return 0
  const today = forecast.daily?.[0]
  return today?.best_event?.score ?? today?.events?.[0]?.score ?? 0
}

function onMarkerClick(vp) {
  emit('select-viewpoint', vp.id)
}
</script>

<style scoped>
.fullscreen-map {
  position: fixed;
  inset: 0;
  z-index: 500;
  background: #0a0a0a;
}

.close-btn {
  position: absolute;
  top: max(16px, env(safe-area-inset-top));
  right: 16px;
  z-index: 510;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  border: none;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: var(--text-lg);
  cursor: pointer;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 入场/退场动画 */
.map-modal-enter-active {
  transition: all 300ms var(--ease-out-expo);
}

.map-modal-leave-active {
  transition: all 200ms ease-in;
}

.map-modal-enter-from,
.map-modal-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
```

**Step 1: 创建 FullscreenMap.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/FullscreenMap.vue
git commit -m "feat(frontend-c): add FullscreenMap modal with markers and close animation"
```

---

## Task 2: "预测卡片"截图

**Files:**
- Modify: `frontend/src/components/scheme-c/PredictionCard.vue` (添加截图逻辑)
- Modify: `frontend/src/components/scheme-c/CardSwiper.vue` (长按事件传递)

### 截图处理 (参考 §10.C.8)

触发方式:
1. 长按卡片 → "保存到相册" 弹窗
2. 顶栏 📸 按钮 → 直接截取当前卡片

截图处理:
- 保存为 1080×1920 (9:16 竖版，小红书最佳比例)
- 自动添加 GMP 品牌水印 (已在 CardFront 中)
- 去除背景模糊地图，使用纯色渐变背景 (更适合传播)

### 实现

在 `CardSwiper.vue` 中添加截图方法:

```javascript
import { useScreenshot } from '@/composables/useScreenshot'

const { capture } = useScreenshot()

async function captureCurrentCard() {
  const currentVp = props.viewpoints[currentIndex.value]
  if (!currentVp) return

  const cardComponent = cardRefs.value[currentVp.id]
  if (!cardComponent?.cardRef) return

  // 确保卡片在正面
  cardComponent.flipToFront()

  await nextTick()

  await capture(
    cardComponent.cardRef,
    `gmp-${currentVp.name}-prediction.png`
  )
}

function onLongPress(vpId) {
  captureCurrentCard()
}
```

在 `CardSwiper.vue` 中暴露截图方法:

```javascript
defineExpose({ slideTo, captureCurrentCard })
```

**Step 1: 添加截图逻辑到 CardSwiper**

**Step 2: 连接 HomeView 的截图按钮**

在 `HomeView.vue` 中:

```javascript
const swiperRef = ref(null)

function onCapture() {
  swiperRef.value?.captureCurrentCard()
}
```

**Step 3: 提交**

```bash
git add frontend/src/components/scheme-c/CardSwiper.vue frontend/src/views/HomeView.vue
git commit -m "feat(frontend-c): add card screenshot on long-press and capture button"
```

---

## Task 3: "对比组图"截图

**Files:**
- Create: `frontend/src/components/scheme-c/CompareGrid.vue`
- Modify: `frontend/src/components/scheme-c/CardTopBar.vue` (长按📸触发)

### 对比组图结构 (参考 §10.C.8)

一次截取多张卡片拼成组图:

```
┌──────────┬──────────┬──────────┐
│ 牛背山   │ 磐羊湖   │ 折多山    │
│  98分    │  90分    │  75分     │
│  推荐    │  推荐    │  可能     │
│ 金山+云海│  云海    │  金山     │
└──────────┴──────────┴──────────┘
        2月12日 川西观景预测
```

触发: 长按顶栏 📸 → "生成今日组图"

### 实现

```vue
<!-- frontend/src/components/scheme-c/CompareGrid.vue -->
<template>
  <div ref="gridRef" class="compare-grid" v-if="visible">
    <div class="grid-cards">
      <div
        v-for="item in topViewpoints"
        :key="item.viewpoint.id"
        :class="['grid-card', getStatusClass(item.score)]"
      >
        <h4>{{ item.viewpoint.name }}</h4>
        <div class="grid-score">{{ item.score }}分</div>
        <StatusBadge :score="item.score" />
        <p class="grid-events">{{ item.eventSummary }}</p>
      </div>
    </div>
    <div class="grid-footer">
      {{ formatDate(selectedDate) }} 川西观景预测
    </div>
    <div class="grid-watermark">GMP 景观预测</div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'
import { useScreenshot } from '@/composables/useScreenshot'
import StatusBadge from '@/components/score/StatusBadge.vue'

const props = defineProps({
  viewpoints: { type: Array, default: () => [] },
  forecasts: { type: Object, default: () => ({}) },
  selectedDate: { type: String, default: '' },
})

const gridRef = ref(null)
const visible = ref(false)
const { getStatus } = useScoreColor()
const { capture } = useScreenshot()

// 取评分最高的前 3-6 个观景台
const topViewpoints = computed(() => {
  const results = []
  for (const vp of props.viewpoints) {
    const forecast = props.forecasts[vp.id]
    if (!forecast) continue
    const day = forecast.daily?.[0]
    if (!day) continue
    const bestScore = day.best_event?.score ?? 0
    const eventLabels = (day.events ?? [])
      .filter(e => e.score >= 50)
      .map(e => e.event_label)
      .join('+')
    results.push({
      viewpoint: vp,
      score: bestScore,
      eventSummary: eventLabels || '—',
    })
  }
  return results.sort((a, b) => b.score - a.score).slice(0, 6)
})

function getStatusClass(score) {
  return `grid-card--${getStatus(score)}`
}

function formatDate(dateStr) {
  if (!dateStr) return '今日'
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

// 生成组图截图
async function generateCompareScreenshot() {
  visible.value = true
  await nextTick()

  if (gridRef.value) {
    await capture(gridRef.value, 'gmp-compare-grid.png')
  }

  visible.value = false
}

defineExpose({ generateCompareScreenshot })
</script>

<style scoped>
.compare-grid {
  position: fixed;
  top: -9999px;  /* 离屏渲染 */
  left: 0;
  width: 1080px;
  padding: 40px;
  background: linear-gradient(160deg, #1a1a2e, #16213e);
  color: white;
}

.grid-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.grid-card {
  border-radius: var(--radius-md);
  padding: 24px 16px;
  text-align: center;
}

.grid-card--perfect {
  background: linear-gradient(160deg, #FFD700, #FF8C00);
}

.grid-card--recommended {
  background: linear-gradient(160deg, #10B981, #06B6D4);
}

.grid-card--possible {
  background: linear-gradient(160deg, #F59E0B, #FDE68A);
  color: var(--text-primary);
}

.grid-card--not-recommended {
  background: linear-gradient(160deg, #6B7280, #D1D5DB);
}

.grid-card h4 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px;
}

.grid-score {
  font-size: 36px;
  font-weight: 700;
  margin: 8px 0;
}

.grid-events {
  font-size: 14px;
  margin: 8px 0 0;
  opacity: 0.8;
}

.grid-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 18px;
  opacity: 0.6;
}

.grid-watermark {
  text-align: center;
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.3;
}
</style>
```

**Step 1: 创建 CompareGrid.vue**

**Step 2: 在 HomeView 中集成**

```javascript
import CompareGrid from '@/components/scheme-c/CompareGrid.vue'

const compareGridRef = ref(null)

// 长按📸触发
function onCaptureLongPress() {
  compareGridRef.value?.generateCompareScreenshot()
}
```

**Step 3: 提交**

```bash
git add frontend/src/components/scheme-c/CompareGrid.vue frontend/src/views/HomeView.vue
git commit -m "feat(frontend-c): add CompareGrid for multi-card screenshot"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 点击 🗺️ → 全屏地图弹出，带 300ms 缩放过渡
2. 全屏地图上显示所有 Marker + 评分
3. 点击 Marker → 关闭地图 → 自动滑动到对应卡片
4. 长按卡片 → 触发截图下载
5. 顶栏 📸 按钮 → 截取当前卡片
6. 长按 📸 → 生成今日对比组图

```bash
npm run build
```
