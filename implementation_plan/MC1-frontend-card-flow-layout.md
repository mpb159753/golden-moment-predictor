# MC1: C 方案 — 卡片流首页布局

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 C 方案 (Card Flow) 的首页布局，包含 CardTopBar (日期标签 + 分页指示器 + 地图入口) + BackgroundMap (暗色模糊地图壁纸) + HomeView 三层结构。

**依赖模块:** M16 (项目初始化), M17 (数据层), M18 (composables), M22 (地图组件)

---

## 背景

C 方案的核心理念是"沉浸式阅读体验"。每个观景台是一张精心设计的大卡片，用户左右滑动浏览。首页由三层组成：底层暗色模糊地图 + 中间 Swiper 卡片容器 + 顶部日期/导航栏。

### 设计参考

- [10-frontend-C-card-flow.md §10.C.2 页面结构](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)
- [10-frontend-C-card-flow.md §10.C.3 交互逻辑](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)
- [10-frontend-C-card-flow.md §10.C.5 背景地图](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)
- [10-frontend-C-card-flow.md §10.C.10 组件树](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)

### 组件树 (方案 C 首页)

```
App.vue
└── HomeView.vue (方案C首页)
    ├── CardTopBar.vue            # 日期标签 + 分页指示器 + 地图入口
    ├── BackgroundMap.vue         # ★ 暗色模糊地图背景 ★
    ├── CardSwiper.vue            # ★ 方案C核心: Swiper容器 ★   → MC2
    │   └── PredictionCard.vue × N   → MC2
    ├── FullscreenMap.vue         # 地图全屏模式 → MC3
    └── ScreenshotBtn.vue         [公共]
```

---

## Task 1: 安装 Swiper 依赖

**Files:**
- Modify: `frontend/package.json`

方案 C 相比 A/B 需要额外引入 `swiper` 和 `@lottiefiles/lottie-player` (可选)。

**Step 1: 安装依赖**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm install swiper
```

**Step 2: 验证安装**

```bash
cat package.json | grep swiper
```

Expected: `"swiper": "^11.x.x"` (或类似版本号)

**Step 3: 提交**

```bash
git add package.json package-lock.json
git commit -m "chore(frontend-c): add swiper dependency for card flow"
```

---

## Task 2: BackgroundMap 暗色模糊地图壁纸

**Files:**
- Create: `frontend/src/components/scheme-c/BackgroundMap.vue`

> [!NOTE]
> C 方案专有组件统一放在 `components/scheme-c/` 目录下，与公共组件隔离。

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `center` | Array | [102.0, 30.5] | 当前中心坐标 [lon, lat] |
| `zoom` | Number | 11 | 缩放级别 |

### 功能要求

地图作为**动态壁纸**存在，不可交互 (参考 §10.C.5):

1. 在最底层渲染全屏高德地图 (暗色主题)
2. 上覆一层 `backdrop-filter: blur(20px)` + 半透明暗色遮罩
3. 当前观景台坐标高亮一个发光圆点
4. 切换卡片时，底层地图使用 `flyTo` 平滑过渡到新坐标

### 实现

```vue
<!-- frontend/src/components/scheme-c/BackgroundMap.vue -->
<template>
  <div class="background-map">
    <!-- 底层地图 -->
    <div id="bg-map" class="map-layer" />
    <!-- 模糊遮罩 -->
    <div class="blur-overlay" />
    <!-- 发光圆点 (当前位置) -->
    <div class="glow-dot" v-if="mapReady" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'

const props = defineProps({
  center: { type: Array, default: () => [102.0, 30.5] },
  zoom: { type: Number, default: 11 },
})

let map = null
let glowMarker = null
const mapReady = ref(false)

onMounted(async () => {
  const AMap = await AMapLoader.load({
    key: import.meta.env.VITE_AMAP_KEY,
    version: '2.0',
  })

  map = new AMap.Map('bg-map', {
    zoom: props.zoom,
    center: props.center,
    mapStyle: 'amap://styles/dark',    // ★ 暗色主题
    viewMode: '2D',
    features: ['bg', 'road'],          // 仅基底+道路，无标注
    dragEnable: false,                  // ★ 禁止交互
    zoomEnable: false,
    touchZoom: false,
    keyboardEnable: false,
    scrollWheel: false,
  })

  // 发光圆点标记
  glowMarker = new AMap.CircleMarker({
    center: props.center,
    radius: 8,
    fillColor: '#3B82F6',
    fillOpacity: 0.6,
    strokeColor: '#93C5FD',
    strokeWeight: 3,
    strokeOpacity: 0.8,
  })
  glowMarker.setMap(map)

  mapReady.value = true
})

// 监听中心坐标变化 → flyTo 动画
watch(() => props.center, (newCenter) => {
  if (map && newCenter) {
    map.setZoomAndCenter(props.zoom, newCenter, true, 800)
    if (glowMarker) {
      glowMarker.setCenter(newCenter)
    }
  }
})

onUnmounted(() => {
  if (map) {
    map.destroy()
    map = null
  }
})

// 暴露 flyTo 方法供外部调用
function flyTo(lon, lat, zoom = 11) {
  if (map) {
    map.setZoomAndCenter(zoom, [lon, lat], true, 800)
    if (glowMarker) {
      glowMarker.setCenter([lon, lat])
    }
  }
}

defineExpose({ flyTo })
</script>

<style scoped>
.background-map {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.map-layer {
  width: 100%;
  height: 100%;
}

.blur-overlay {
  position: absolute;
  inset: 0;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  background: rgba(0, 0, 0, 0.3);
}
</style>
```

**Step 1: 创建目录和文件**

```bash
mkdir -p /Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/scheme-c
```

然后创建 `BackgroundMap.vue`。

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/
git commit -m "feat(frontend-c): add BackgroundMap with dark blur overlay"
```

---

## Task 3: CardTopBar 顶部栏

**Files:**
- Create: `frontend/src/components/scheme-c/CardTopBar.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `dates` | Array | [] | 可选日期列表 (字符串 YYYY-MM-DD) |
| `selectedDate` | String | — | 当前选中日期 |
| `currentIndex` | Number | 0 | 当前卡片索引 (分页指示器) |
| `totalCards` | Number | 0 | 总卡片数 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `date-change` | dateString | 日期切换 |
| `open-map` | — | 打开全屏地图 |
| `capture` | — | 触发截图 |

### 布局 (参考 §10.C.7)

```
┌────────────────────────────┐
│ 📅 2月12日  ● ● ○ ○ ○  🗺️ │  ← 日期标签 + 分页指示器 + 地图入口
└────────────────────────────┘
```

使用日期标签栏 (而非纵向滑动，避免手势冲突):

```
┌──────────────────────────────┐
│  12日  13日  14日  15日  ... │  ← 可横向滚动的日期标签
│  ───                        │
│  (当前选中: 12日)             │
└──────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/components/scheme-c/CardTopBar.vue -->
<template>
  <div class="card-top-bar">
    <!-- 日期标签栏 -->
    <div class="date-tabs" ref="dateTabsRef">
      <button
        v-for="date in dates"
        :key="date"
        :class="['date-tab', { active: date === selectedDate }]"
        @click="emit('date-change', date)"
      >
        {{ formatDate(date) }}
      </button>
    </div>

    <!-- 分页指示器 -->
    <div class="pagination-dots">
      <span
        v-for="i in Math.min(totalCards, 9)"
        :key="i"
        :class="['dot', { active: i - 1 === currentIndex }]"
      />
      <span v-if="totalCards > 9" class="dot-more">...</span>
    </div>

    <!-- 右侧工具栏 -->
    <div class="toolbar">
      <button class="tool-btn" @click="emit('capture')" title="截图">
        📸
      </button>
      <button class="tool-btn" @click="emit('open-map')" title="地图">
        🗺️
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  dates: { type: Array, default: () => [] },
  selectedDate: { type: String, default: '' },
  currentIndex: { type: Number, default: 0 },
  totalCards: { type: Number, default: 0 },
})

const emit = defineEmits(['date-change', 'open-map', 'capture'])

const dateTabsRef = ref(null)

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}
</script>

<style scoped>
.card-top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top));
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

/* 日期标签 */
.date-tabs {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  flex-shrink: 1;
  min-width: 0;
}

.date-tabs::-webkit-scrollbar {
  display: none;
}

.date-tab {
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  font-size: var(--text-xs);
  white-space: nowrap;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.date-tab.active {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border-color: rgba(255, 255, 255, 0.5);
}

/* 分页指示器 */
.pagination-dots {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-shrink: 0;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.3);
  transition: all var(--duration-fast);
}

.dot.active {
  width: 16px;
  background: white;
}

.dot-more {
  color: rgba(255, 255, 255, 0.5);
  font-size: var(--text-xs);
}

/* 右侧工具栏 */
.toolbar {
  display: flex;
  gap: 8px;
  margin-left: auto;
  flex-shrink: 0;
}

.tool-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.1);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}

.tool-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
```

**Step 1: 创建 CardTopBar.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/CardTopBar.vue
git commit -m "feat(frontend-c): add CardTopBar with date tabs, pagination, map entry"
```

---

## Task 4: HomeView 首页布局

**Files:**
- Modify: `frontend/src/views/HomeView.vue` (替换占位)

### 页面结构 (参考 §10.C.2)

```
┌────────────────────────────┐
│ 📅 2月12日  ● ● ○ ○ ○  🗺️ │  ← CardTopBar
│                            │
│  ┏━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃                      ┃  │  ← BackgroundMap (暗色模糊)
│  ┃  ┌──────────────┐    ┃  │
│  ┃  │  牛 背 山     │    ┃  │  ← PredictionCard (via CardSwiper)
│  ┃  │    98  推荐   │    ┃  │
│  ┃  └──────────────┘    ┃  │
│  ┃                      ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━┛  │
│                            │
│  ← 磐羊湖        折多山 → │
└────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/views/HomeView.vue -->
<template>
  <div class="home-view">
    <!-- 底层: 暗色模糊地图 -->
    <BackgroundMap
      ref="bgMapRef"
      :center="currentCenter"
      :zoom="11"
    />

    <!-- 中层: 卡片 Swiper -->
    <CardSwiper
      :viewpoints="viewpoints"
      :forecasts="forecasts"
      :selected-date="selectedDate"
      @slide-change="onSlideChange"
      @card-click="onCardClick"
      @card-flip-back="onCardFlipBack"
      @view-detail="onViewDetail"
    />

    <!-- 顶层: 顶部导航栏 -->
    <CardTopBar
      :dates="availableDates"
      :selected-date="selectedDate"
      :current-index="currentCardIndex"
      :total-cards="viewpoints.length"
      @date-change="onDateChange"
      @open-map="onOpenMap"
      @capture="onCapture"
    />

    <!-- 全屏地图模态 (MC3) -->
    <FullscreenMap
      v-if="showFullscreenMap"
      :viewpoints="viewpoints"
      :forecasts="forecasts"
      :selected-date="selectedDate"
      @close="showFullscreenMap = false"
      @select-viewpoint="onMapSelectViewpoint"
    />

    <!-- GMP 品牌水印 -->
    <div class="watermark">GMP 川西景观预测</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useViewpointStore } from '@/stores/viewpoints'
import { useAppStore } from '@/stores/app'
import BackgroundMap from '@/components/scheme-c/BackgroundMap.vue'
import CardSwiper from '@/components/scheme-c/CardSwiper.vue'
import CardTopBar from '@/components/scheme-c/CardTopBar.vue'
import FullscreenMap from '@/components/scheme-c/FullscreenMap.vue'

const router = useRouter()
const vpStore = useViewpointStore()
const appStore = useAppStore()

const bgMapRef = ref(null)
const currentCardIndex = ref(0)
const showFullscreenMap = ref(false)

// 计算属性
const viewpoints = computed(() => vpStore.index)
const forecasts = computed(() => vpStore.forecasts)
const selectedDate = computed(() => vpStore.selectedDate)

const currentViewpoint = computed(() =>
  viewpoints.value[currentCardIndex.value] ?? null
)

const currentCenter = computed(() => {
  const vp = currentViewpoint.value
  if (!vp?.location) return [102.0, 30.5]
  return [vp.location.lon, vp.location.lat]
})

const availableDates = computed(() => {
  const firstForecast = Object.values(forecasts.value)[0]
  return firstForecast?.daily?.map(d => d.date) ?? []
})

// === 事件处理 ===

function onSlideChange(index) {
  currentCardIndex.value = index
  // 背景地图 flyTo 由 watch currentCenter 自动触发
  const vp = viewpoints.value[index]
  if (vp) {
    vpStore.selectViewpoint(vp.id)
    // 预加载相邻卡片数据
    preloadAdjacentCards(index)
  }
}

function onCardClick(viewpointId) {
  // 卡片点击 → 翻转 (由 CardSwiper/PredictionCard 内部处理)
}

function onCardFlipBack(viewpointId) {
  // 翻转回正面
}

function onViewDetail(viewpointId) {
  router.push(`/viewpoint/${viewpointId}`)
}

function onDateChange(date) {
  vpStore.selectDate(date)
}

function onOpenMap() {
  showFullscreenMap.value = true
}

function onCapture() {
  // 截图逻辑在 MC3 实现
}

function onMapSelectViewpoint(vpId) {
  showFullscreenMap.value = false
  const index = viewpoints.value.findIndex(v => v.id === vpId)
  if (index >= 0) {
    currentCardIndex.value = index
    // TODO: 通过 CardSwiper ref 跳转至对应卡片
  }
}

// 预加载相邻卡片数据 (参考 §10.C.11)
async function preloadAdjacentCards(centerIndex) {
  const range = [-1, 1]
  for (const offset of range) {
    const idx = centerIndex + offset
    if (idx >= 0 && idx < viewpoints.value.length) {
      const vp = viewpoints.value[idx]
      if (!forecasts.value[vp.id]) {
        vpStore.loadForecast(vp.id)
      }
    }
  }
}

// === 初始化 (参考 §10.C.11 数据加载时序) ===

onMounted(async () => {
  await vpStore.loadIndex()

  // 首先加载第一张卡片的数据
  if (viewpoints.value.length > 0) {
    await vpStore.loadForecast(viewpoints.value[0].id)
    vpStore.selectViewpoint(viewpoints.value[0].id)

    // 预加载相邻 2 张卡片
    preloadAdjacentCards(0)
  }
})
</script>

<style scoped>
.home-view {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #0a0a0a;
}

.watermark {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 80;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
</style>
```

**Step 1: 替换 HomeView.vue**

**Step 2: 提交**

```bash
git add frontend/src/views/HomeView.vue
git commit -m "feat(frontend-c): implement card flow HomeView layout with 3-layer structure"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 访问首页 → 暗色模糊地图背景加载，发光圆点显示当前位置
2. 顶部显示日期标签栏 + 分页指示器 + 🗺️ 地图入口
3. 日期标签可横向滚动，点击切换日期
4. 右下角显示 GMP 品牌水印
5. 背景为暗色调，与卡片形成鲜明对比

```bash
# 确认构建不报错
npm run build
```
