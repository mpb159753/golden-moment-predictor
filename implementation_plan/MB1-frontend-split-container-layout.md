# MB1: B 方案 — 分屏首页布局

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 B 方案 (Split List) 的首页布局，包含可拖拽上下分割容器 + 搜索/筛选/排序栏 + 地图面板 + 列表面板。

**依赖模块:** M16 (项目初始化), M17 (数据层), M18 (composables), M19-M21 (公共组件), M22 (地图组件)

---

## 背景

B 方案的核心理念是"列表优先，效率为王"。上半部分为地图区域 (35%)，下半部分为可滚动卡片列表 (65%)，中间由可拖拽的分割条调整比例。列表与地图通过 Intersection Observer 联动。

### 设计参考

- [10-frontend-B-split-list.md §10.B.2 页面结构](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)
- [10-frontend-B-split-list.md §10.B.3 交互逻辑](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)
- [10-frontend-B-split-list.md §10.B.6 拖拽分割条](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)
- [10-frontend-B-split-list.md §10.B.10 组件树](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-B-split-list.md)

### 组件树 (方案 B 首页)

```
App.vue
└── HomeView.vue (方案B首页)
    ├── ListTopBar.vue            # 日期 + 搜索 + 筛选 + 排序
    ├── SplitContainer.vue        # ★ 方案B核心: 分割容器 ★
    │   ├── MapPanel.vue          # 上半部分: 地图面板
    │   │   ├── AMapContainer.vue [公共]
    │   │   │   ├── ViewpointMarker.vue × N [公共]
    │   │   │   └── RouteLine.vue [公共]
    │   │   └── MapToggleBtn.vue  # 地图最小化/恢复按钮
    │   ├── DragBar.vue           # 拖拽分割条
    │   └── ListPanel.vue         # 下半部分: 列表面板
    │       ├── ViewpointListItem.vue × N  → MB2
    │       └── RouteListItem.vue          → MB3
    └── ScreenshotBtn.vue         [公共]
```

---

## Task 1: SplitContainer 分割容器

**Files:**
- Create: `frontend/src/components/scheme-b/SplitContainer.vue`

> [!NOTE]
> B 方案专有组件统一放在 `components/scheme-b/` 目录下，与公共组件和 A 方案组件隔离。

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `initialRatio` | Number | 0.35 | 地图区域初始高度比例 (0-1) |
| `minRatio` | Number | 0.0 | 地图最小比例 (0 = 可完全隐藏) |
| `maxRatio` | Number | 0.6 | 地图最大比例 |
| `storageKey` | String | 'split-ratio' | localStorage 持久化 key |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `ratio-change` | Number (0-1) | 拖拽导致比例变化 |
| `map-hidden` | — | 地图被完全隐藏 |
| `map-restored` | — | 地图从隐藏状态恢复 |
| `list-hidden` | — | 列表被完全隐藏 (向下拖至极限) |
| `list-restored` | — | 列表从隐藏状态恢复 |

### Slots

| Slot | 说明 |
|------|------|
| `map` | 上半部分地图内容 |
| `drag` | 拖拽条 (默认渲染 DragBar) |
| `list` | 下半部分列表内容 |

### 实现

```vue
<!-- frontend/src/components/scheme-b/SplitContainer.vue -->
<template>
  <div ref="containerRef" class="split-container" :class="{ 'map-hidden': isMapHidden, 'list-hidden': isListHidden }">
    <!-- 地图区域 -->
    <div
      class="split-map"
      :style="{ height: isMapHidden ? '0px' : `${mapHeight}px` }"
    >
      <slot name="map" />
    </div>

    <!-- 拖拽分割条 -->
    <slot name="drag">
      <DragBar
        :is-map-hidden="isMapHidden"
        :is-list-hidden="isListHidden"
        :direction="direction"
        @drag-start="onDragStart"
        @drag-move="onDragMove"
        @drag-end="onDragEnd"
        @double-click="onDoubleClick"
        @restore-map="restoreMap"
        @restore-list="restoreList"
      />
    </slot>

    <!-- 列表区域 -->
    <div class="split-list" :style="{ flex: 1 }">
      <slot name="list" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import DragBar from './DragBar.vue'

const props = defineProps({
  initialRatio: { type: Number, default: 0.35 },
  minRatio: { type: Number, default: 0.0 },
  maxRatio: { type: Number, default: 0.6 },
  storageKey: { type: String, default: 'split-ratio' },
})

const emit = defineEmits(['ratio-change', 'map-hidden', 'map-restored', 'list-hidden', 'list-restored'])

const containerRef = ref(null)
const currentRatio = ref(props.initialRatio)
const isDragging = ref(false)
const isMapHidden = ref(false)
const isListHidden = ref(false)

// 横屏/竖屏自动检测拖拽方向
const direction = ref('vertical') // 'vertical' | 'horizontal'
function updateDirection() {
  direction.value = window.innerWidth >= 1024 ? 'horizontal' : 'vertical'
}
onMounted(() => {
  updateDirection()
  window.addEventListener('resize', updateDirection)
})
onUnmounted(() => window.removeEventListener('resize', updateDirection))

let startY = 0
let startRatio = 0

// 计算地图区域像素高度
const mapHeight = computed(() => {
  if (!containerRef.value) return 0
  return containerRef.value.clientHeight * currentRatio.value
})

// 从 localStorage 恢复用户偏好
onMounted(() => {
  const saved = localStorage.getItem(props.storageKey)
  if (saved !== null) {
    const ratio = parseFloat(saved)
    if (!isNaN(ratio) && ratio >= props.minRatio && ratio <= props.maxRatio) {
      currentRatio.value = ratio
    }
    if (ratio <= 0) {
      isMapHidden.value = true
    }
  }
})

// 持久化比例
function saveRatio(ratio) {
  localStorage.setItem(props.storageKey, ratio.toString())
}

// === 拖拽处理 ===

function onDragStart(y) {
  isDragging.value = true
  startY = y
  startRatio = currentRatio.value
}

function onDragMove(pos) {
  if (!isDragging.value || !containerRef.value) return
  const containerSize = direction.value === 'horizontal'
    ? containerRef.value.clientWidth
    : containerRef.value.clientHeight
  const delta = pos - startY
  const deltaRatio = delta / containerSize
  const newRatio = Math.max(
    props.minRatio,
    Math.min(props.maxRatio, startRatio + deltaRatio)
  )
  currentRatio.value = newRatio
}

function onDragEnd() {
  isDragging.value = false

  // 拖至极小 → 隐藏地图
  if (currentRatio.value <= 0.05) {
    currentRatio.value = 0
    isMapHidden.value = true
    isListHidden.value = false
    emit('map-hidden')
  }

  // 拖至极大 → 隐藏列表 (§10.B.6 向下拖至极限)
  if (currentRatio.value >= props.maxRatio - 0.05) {
    currentRatio.value = 1.0
    isListHidden.value = true
    isMapHidden.value = false
    emit('list-hidden')
  }

  saveRatio(currentRatio.value)
  emit('ratio-change', currentRatio.value)
}

// 双击 → 恢复默认比例
function onDoubleClick() {
  currentRatio.value = props.initialRatio
  isMapHidden.value = false
  isListHidden.value = false
  saveRatio(currentRatio.value)
  emit('ratio-change', currentRatio.value)
  if (isMapHidden.value) emit('map-restored')
  if (isListHidden.value) emit('list-restored')
}

// 从隐藏状态恢复地图
function restoreMap() {
  currentRatio.value = props.initialRatio
  isMapHidden.value = false
  isListHidden.value = false
  saveRatio(currentRatio.value)
  emit('map-restored')
}

// 从隐藏状态恢复列表 (§10.B.6)
function restoreList() {
  currentRatio.value = props.initialRatio
  isListHidden.value = false
  isMapHidden.value = false
  saveRatio(currentRatio.value)
  emit('list-restored')
}
</script>

<style scoped>
.split-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.split-map {
  position: relative;
  overflow: hidden;
  transition: height var(--duration-normal) var(--ease-out-expo);
  flex-shrink: 0;
}

/* 拖拽中禁用过渡 */
.split-container:active .split-map {
  transition: none;
}

.split-list {
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

/* 地图隐藏时列表占满 */
.map-hidden .split-map {
  height: 0 !important;
}

/* 列表隐藏时地图占满 (§10.B.6 向下拖至极限 → 纯地图模式) */
.list-hidden .split-list {
  flex: 0 !important;
  overflow: hidden;
}
</style>
```

**Step 1: 创建目录和文件**

```bash
mkdir -p /Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/scheme-b
```

然后创建 `SplitContainer.vue`。

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-b/
git commit -m "feat(frontend-b): add SplitContainer with drag-resizable split"
```

---

## Task 2: DragBar 拖拽分割条

**Files:**
- Create: `frontend/src/components/scheme-b/DragBar.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `isMapHidden` | Boolean | false | 地图是否被隐藏 |
| `isListHidden` | Boolean | false | 列表是否被隐藏 |
| `direction` | String | 'vertical' | 拖拽方向: 'vertical' (竖屏) / 'horizontal' (横屏) |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `drag-start` | Number (clientY) | 拖拽开始 |
| `drag-move` | Number (clientY) | 拖拽移动 |
| `drag-end` | — | 拖拽结束 |
| `double-click` | — | 双击恢复 |
| `restore-map` | — | 点击"显示地图"按钮 |
| `restore-list` | — | 点击"显示列表"按钮 |

### 实现

```vue
<!-- frontend/src/components/scheme-b/DragBar.vue -->
<template>
  <div class="drag-bar-wrapper">
    <!-- 地图隐藏时显示恢复按钮 -->
    <button v-if="isMapHidden" class="restore-btn" @click="emit('restore-map')">
      🗺️ 显示地图
    </button>

    <!-- 列表隐藏时显示恢复按钮 (§10.B.6) -->
    <button v-else-if="isListHidden" class="restore-btn" @click="emit('restore-list')">
      📋 显示列表
    </button>

    <!-- 拖拽条 -->
    <div
      v-else
      class="drag-bar"
      :class="{ horizontal: direction === 'horizontal' }"
      @touchstart.passive="onTouchStart"
      @touchmove.passive="onTouchMove"
      @touchend="onTouchEnd"
      @mousedown="onMouseDown"
      @dblclick="emit('double-click')"
    >
      <div class="drag-handle">≡</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isMapHidden: { type: Boolean, default: false },
  isListHidden: { type: Boolean, default: false },
  direction: { type: String, default: 'vertical' },
})

const emit = defineEmits(['drag-start', 'drag-move', 'drag-end', 'double-click', 'restore-map', 'restore-list'])

// Touch 事件 (支持竖屏/横屏方向)
function getPosition(e) {
  const touch = e.touches?.[0] ?? e
  return props.direction === 'horizontal' ? touch.clientX : touch.clientY
}

function onTouchStart(e) {
  emit('drag-start', getPosition(e))
}

function onTouchMove(e) {
  emit('drag-move', getPosition(e))
}

function onTouchEnd() {
  emit('drag-end')
}

// Mouse 事件 (桌面端，支持横屏时水平拖拽)
function onMouseDown(e) {
  emit('drag-start', getPosition(e))

  const onMouseMove = (ev) => emit('drag-move', getPosition(ev))
  const onMouseUp = () => {
    emit('drag-end')
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<style scoped>
.drag-bar-wrapper {
  flex-shrink: 0;
}

.drag-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 24px;
  cursor: row-resize;
  background: var(--bg-card);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  touch-action: none;
  user-select: none;
}

/* 横屏时水平方向拖拽 */
.drag-bar.horizontal {
  width: 24px;
  height: 100%;
  cursor: col-resize;
  border-top: none;
  border-bottom: none;
  border-left: 1px solid rgba(0, 0, 0, 0.06);
  border-right: 1px solid rgba(0, 0, 0, 0.06);
}

.drag-bar.horizontal .drag-handle {
  writing-mode: vertical-rl;
}

.drag-handle {
  font-size: 14px;
  color: var(--text-muted);
  letter-spacing: 2px;
  line-height: 1;
}

.drag-bar:hover {
  background: var(--bg-primary);
}

.drag-bar:active {
  background: var(--color-primary-light);
}

.restore-btn {
  width: 100%;
  padding: 8px;
  border: none;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: var(--bg-card);
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.restore-btn:hover {
  background: var(--bg-primary);
}
</style>
```

**Step 1: 创建 DragBar.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-b/DragBar.vue
git commit -m "feat(frontend-b): add DragBar with touch/mouse drag and double-click reset"
```

---

## Task 3: ListTopBar 搜索/筛选/排序栏

**Files:**
- Create: `frontend/src/components/scheme-b/ListTopBar.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoints` | Array | [] | 所有观景台 (用于搜索匹配) |
| `selectedDate` | String | — | 当前选中日期 |
| `availableDates` | Array | [] | 可选日期列表 |
| `activeFilters` | Array | [] | 当前激活的事件类型筛选 |
| `sortBy` | String | 'score' | 当前排序方式 |
| `activeTab` | String | 'viewpoints' | 当前标签: 'viewpoints' / 'routes' |
| `scoreThreshold` | Number | 0 | 评分门槛滑块值 (0-100) (§10.B.5) |
| `statusFilter` | String | 'all' | 状态过滤: 'recommended' / 'possible' / 'all' (§10.B.5) |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `search` | viewpointId | 搜索选中某个观景台 |
| `filter` | filterTypes[] | 事件类型筛选变更 |
| `date-change` | dateString | 日期切换 |
| `sort-change` | sortKey | 排序方式变更 |
| `tab-change` | 'viewpoints' / 'routes' | 标签切换 |
| `score-threshold-change` | Number (0-100) | 评分门槛变更 (§10.B.5) |
| `status-filter-change` | String | 状态过滤变更 (§10.B.5) |

### 实现

```vue
<!-- frontend/src/components/scheme-b/ListTopBar.vue -->
<template>
  <div class="list-top-bar">
    <!-- 第一行: 日期 + 搜索 -->
    <div class="top-row">
      <button class="date-btn" @click="showDatePicker = !showDatePicker">
        📅 {{ formatDate(selectedDate) }}
      </button>

      <!-- 日期选择器弹出层 (§10.B.5 修复: 渲染实际 DatePicker 组件) -->
      <DatePicker
        v-if="showDatePicker"
        :dates="availableDates"
        :selected="selectedDate"
        @select="onDateSelect"
        class="date-picker-popup"
      />

      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索观景台..."
        />
        <!-- 搜索结果下拉 -->
        <ul v-if="searchResults.length" class="search-results">
          <li
            v-for="vp in searchResults"
            :key="vp.id"
            @click="selectResult(vp)"
          >
            {{ vp.name }}
          </li>
        </ul>
      </div>
    </div>

    <!-- 第二行: 筛选 Chips + 排序 + 标签切换 -->
    <div class="bottom-row">
      <!-- 事件类型筛选 -->
      <div class="filter-chips">
        <button
          v-for="filter in filterOptions"
          :key="filter.type"
          :class="['chip', { active: activeFilters.includes(filter.type) }]"
          @click="toggleFilter(filter.type)"
        >
          {{ filter.icon }}
        </button>
      </div>

      <!-- 标签切换: 观景台 / 线路 -->
      <div class="tab-switch">
        <button
          :class="['tab-btn', { active: activeTab === 'viewpoints' }]"
          @click="emit('tab-change', 'viewpoints')"
        >
          观景台
        </button>
        <button
          :class="['tab-btn', { active: activeTab === 'routes' }]"
          @click="emit('tab-change', 'routes')"
        >
          线路
        </button>
      </div>

      <!-- 排序下拉 -->
      <div class="sort-dropdown">
        <select :value="sortBy" @change="emit('sort-change', $event.target.value)">
          <option value="score">推荐</option>
          <option value="name">名称</option>
          <option value="distance">距离</option>
        </select>
        <span class="sort-icon">▼</span>
      </div>
    </div>

    <!-- 第三行: 评分门槛 + 状态过滤 (§10.B.5) -->
    <div class="filter-row">
      <!-- 评分门槛滑块 -->
      <div class="score-threshold">
        <label>评分≥{{ scoreThreshold }}</label>
        <input
          type="range"
          min="0"
          max="100"
          :value="scoreThreshold"
          @input="emit('score-threshold-change', Number($event.target.value))"
          class="threshold-slider"
        />
      </div>

      <!-- 状态过滤按钮组 -->
      <div class="status-filter">
        <button
          v-for="opt in statusOptions"
          :key="opt.value"
          :class="['status-btn', { active: statusFilter === opt.value }]"
          @click="emit('status-filter-change', opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import DatePicker from '@/components/layout/DatePicker.vue'

const props = defineProps({
  viewpoints: { type: Array, default: () => [] },
  selectedDate: { type: String, default: '' },
  availableDates: { type: Array, default: () => [] },
  activeFilters: { type: Array, default: () => [] },
  sortBy: { type: String, default: 'score' },
  activeTab: { type: String, default: 'viewpoints' },
  scoreThreshold: { type: Number, default: 0 },
  statusFilter: { type: String, default: 'all' },
})

const emit = defineEmits([
  'search', 'filter', 'date-change', 'sort-change', 'tab-change',
  'score-threshold-change', 'status-filter-change',
])

const searchQuery = ref('')
const showDatePicker = ref(false)

const filterOptions = [
  { type: 'golden_mountain', icon: '🏔️' },
  { type: 'cloud_sea', icon: '☁️' },
  { type: 'stargazing', icon: '⭐' },
  { type: 'frost', icon: '❄️' },
]

// 状态过滤选项 (§10.B.5)
const statusOptions = [
  { value: 'recommended', label: '推荐' },
  { value: 'possible', label: '可能' },
  { value: 'all', label: '全部' },
]

const searchResults = computed(() => {
  if (!searchQuery.value) return []
  return props.viewpoints.filter(vp =>
    vp.name.includes(searchQuery.value)
  ).slice(0, 5)
})

function selectResult(vp) {
  searchQuery.value = ''
  emit('search', vp.id)
}

function toggleFilter(type) {
  const current = [...props.activeFilters]
  const index = current.indexOf(type)
  if (index >= 0) {
    current.splice(index, 1)
  } else {
    current.push(type)
  }
  emit('filter', current)
}

function formatDate(dateStr) {
  if (!dateStr) return '今天'
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function onDateSelect(date) {
  showDatePicker.value = false
  emit('date-change', date)
}
</script>

<style scoped>
.list-top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg-card);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  padding: 8px 12px;
}

.top-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.date-btn {
  flex-shrink: 0;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: var(--bg-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-fast);
}

.date-btn:hover {
  background: var(--color-primary-light);
}

.search-box {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  background: var(--bg-primary);
  border-radius: var(--radius-full);
  padding: 6px 12px;
}

.search-box input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.search-icon {
  margin-right: 6px;
  font-size: var(--text-sm);
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-elevated);
  list-style: none;
  padding: 4px 0;
  z-index: 10;
}

.search-results li {
  padding: 8px 16px;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.search-results li:hover {
  background: var(--bg-primary);
}

.bottom-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-chips {
  display: flex;
  gap: 4px;
}

.chip {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: var(--bg-primary);
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}

.chip.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.tab-switch {
  display: flex;
  background: var(--bg-primary);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-left: auto;
}

.tab-btn {
  padding: 4px 12px;
  border: none;
  background: transparent;
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--duration-fast);
  color: var(--text-secondary);
}

.tab-btn.active {
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-full);
}

.sort-dropdown {
  position: relative;
}

.sort-dropdown select {
  appearance: none;
  padding: 4px 24px 4px 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  font-size: var(--text-xs);
  cursor: pointer;
  color: var(--text-secondary);
}

.sort-icon {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 8px;
  pointer-events: none;
  color: var(--text-muted);
}

/* 第三行: 评分门槛 + 状态过滤 (§10.B.5) */
.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.score-threshold {
  display: flex;
  align-items: center;
  gap: 6px;
}

.score-threshold label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
}

.threshold-slider {
  width: 80px;
  accent-color: var(--color-primary);
}

.status-filter {
  display: flex;
  background: var(--bg-primary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.status-btn {
  padding: 3px 10px;
  border: none;
  background: transparent;
  font-size: var(--text-xs);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--duration-fast);
}

.status-btn.active {
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-full);
}

/* DatePicker 弹出层 */
.date-picker-popup {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 200;
  margin-top: 4px;
}
</style>
```

**Step 1: 创建 ListTopBar.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-b/ListTopBar.vue
git commit -m "feat(frontend-b): add ListTopBar with search, filter, sort, tab switch"
```

---

## Task 4: MapPanel + MapToggleBtn

**Files:**
- Create: `frontend/src/components/scheme-b/MapPanel.vue`
- Create: `frontend/src/components/scheme-b/MapToggleBtn.vue`

### MapPanel

地图面板包装组件，管理地图容器和 Marker 渲染：

```vue
<!-- frontend/src/components/scheme-b/MapPanel.vue -->
<template>
  <div class="map-panel">
    <AMapContainer
      ref="mapRef"
      height="100%"
      :map-options="mapOptions"
      @ready="onMapReady"
    />

    <template v-if="mapInstance">
      <ViewpointMarker
        v-for="vp in visibleViewpoints"
        :key="vp.id"
        :viewpoint="vp"
        :score="getScore(vp.id)"
        :selected="highlightedId === vp.id"
        @click="emit('marker-click', vp)"
      />
      <RouteLine
        v-if="showRoutes"
        v-for="route in routes"
        :key="route.id"
        :stops="route.stops"
      />
    </template>

    <MapToggleBtn
      class="toggle-btn"
      @click="emit('toggle-map')"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AMapContainer from '@/components/map/AMapContainer.vue'
import ViewpointMarker from '@/components/map/ViewpointMarker.vue'
import RouteLine from '@/components/map/RouteLine.vue'
import MapToggleBtn from './MapToggleBtn.vue'

const props = defineProps({
  visibleViewpoints: { type: Array, default: () => [] },
  routes: { type: Array, default: () => [] },
  highlightedId: { type: String, default: null },
  showRoutes: { type: Boolean, default: false },
  getScore: { type: Function, default: () => 0 },
})

const emit = defineEmits(['marker-click', 'toggle-map', 'map-ready'])

const mapRef = ref(null)
const mapInstance = ref(null)

const mapOptions = {
  zoom: 8,
  center: [102.0, 30.5],
  mapStyle: 'amap://styles/light',
  zooms: [6, 15],
}

function onMapReady(map) {
  mapInstance.value = map
  emit('map-ready', map)
}

// 暴露 map 实例，供父组件调用 panTo/flyTo
defineExpose({
  getMap: () => mapRef.value?.getMap?.(),
  panTo: (lon, lat) => {
    const map = mapRef.value?.getMap?.()
    if (map) map.panTo([lon, lat], true)
  },
  // §10.B.3: 点击卡片时使用 flyTo (带缩放动画)
  flyTo: (lon, lat, zoom = 12) => {
    const map = mapRef.value?.getMap?.()
    if (map) map.setZoomAndCenter(zoom, [lon, lat], true, 800)
  },
})
</script>

<style scoped>
.map-panel {
  position: relative;
  width: 100%;
  height: 100%;
}

.toggle-btn {
  position: absolute;
  bottom: 8px;
  right: 8px;
  z-index: 10;
}
</style>
```

### MapToggleBtn

```vue
<!-- frontend/src/components/scheme-b/MapToggleBtn.vue -->
<template>
  <button class="map-toggle-btn" @click="emit('click')">
    🗺️
  </button>
</template>

<script setup>
const emit = defineEmits(['click'])
</script>

<style scoped>
.map-toggle-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: none;
  background: var(--bg-card);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}

.map-toggle-btn:hover {
  box-shadow: var(--shadow-elevated);
  transform: scale(1.05);
}
</style>
```

**Step 1: 创建 MapPanel.vue 和 MapToggleBtn.vue**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-b/MapPanel.vue frontend/src/components/scheme-b/MapToggleBtn.vue
git commit -m "feat(frontend-b): add MapPanel and MapToggleBtn"
```

---

## Task 5: HomeView 首页布局组装

**Files:**
- Modify: `frontend/src/views/HomeView.vue` (替换占位)

### 页面结构

```
┌────────────────────────────┐
│ 📅 2月12日  🔍  🏔️☁️⭐❄️   │  ← ListTopBar (固定顶栏)
├────────────────────────────┤
│                            │
│    地 图 区 域 (35%)        │  ← MapPanel
│       ● 牛背山             │
│              ● 折多山       │
│                            │
├══ ≡ 拖拽调整比例 ═══════════┤  ← DragBar
│                            │
│  ┌──────────────────────┐  │  ← ListPanel (65%)
│  │ 🏔️ 牛背山    98分     │  │     ViewpointListItem × N → MB2
│  │ 日出金山+云海 推荐     │  │
│  └──────────────────────┘  │
│         ...                │
└────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/views/HomeView.vue -->
<template>
  <div class="home-view">
    <!-- 顶部栏 -->
    <ListTopBar
      :viewpoints="viewpoints"
      :selected-date="selectedDate"
      :available-dates="availableDates"
      :active-filters="activeFilters"
      :sort-by="sortBy"
      :active-tab="activeTab"
      :score-threshold="scoreThreshold"
      :status-filter="statusFilter"
      @search="onSearch"
      @filter="onFilter"
      @date-change="onDateChange"
      @sort-change="onSortChange"
      @tab-change="onTabChange"
      @score-threshold-change="onScoreThresholdChange"
      @status-filter-change="onStatusFilterChange"
    />

    <!-- 分割容器 -->
    <SplitContainer
      :initial-ratio="0.35"
      :min-ratio="0.0"
      :max-ratio="0.6"
      @ratio-change="onRatioChange"
      @map-hidden="onMapHidden"
      @map-restored="onMapRestored"
    >
      <!-- 地图面板 -->
      <template #map>
        <MapPanel
          ref="mapPanelRef"
          :visible-viewpoints="filteredViewpoints"
          :routes="routes"
          :highlighted-id="highlightedId"
          :show-routes="activeTab === 'routes'"
          :get-score="getBestScore"
          @marker-click="onMarkerClick"
          @map-ready="onMapReady"
        />
      </template>

      <!-- 列表面板 -->
      <template #list>
        <!-- 观景台列表 -->
        <div v-if="activeTab === 'viewpoints'" class="viewpoint-list">
          <ViewpointListItem
            v-for="vp in sortedViewpoints"
            :key="vp.id"
            :ref="el => setItemRef(vp.id, el)"
            :viewpoint="vp"
            :forecast="forecasts[vp.id]"
            :selected-date="selectedDate"
            :expanded="expandedId === vp.id"
            @click="onCardClick(vp)"
            @expand="onCardExpand(vp)"
            @go-detail="goToDetail(vp.id)"
          />
        </div>

        <!-- 线路列表 → MB3 -->
        <div v-else class="route-list">
          <RouteListItem
            v-for="route in routes"
            :key="route.id"
            :route="route"
            :selected-date="selectedDate"
            @click="onRouteClick(route)"
          />
        </div>
      </template>
    </SplitContainer>

    <!-- 截图按钮 -->
    <ScreenshotBtn
      class="screenshot-btn"
      :target="$el"
      filename="gmp-split-view.png"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useViewpointStore } from '@/stores/viewpoints'
import { useRouteStore } from '@/stores/routes'
import { useAppStore } from '@/stores/app'
import ListTopBar from '@/components/scheme-b/ListTopBar.vue'
import SplitContainer from '@/components/scheme-b/SplitContainer.vue'
import MapPanel from '@/components/scheme-b/MapPanel.vue'
import ViewpointListItem from '@/components/scheme-b/ViewpointListItem.vue'
import RouteListItem from '@/components/scheme-b/RouteListItem.vue'
import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'

const router = useRouter()
const vpStore = useViewpointStore()
const routeStore = useRouteStore()
const appStore = useAppStore()

const mapPanelRef = ref(null)
const mapInstance = ref(null)

// 状态
const activeFilters = ref([])
const sortBy = ref('score')
const activeTab = ref('viewpoints')
const expandedId = ref(null)
const highlightedId = ref(null)
const scoreThreshold = ref(0)         // §10.B.5 评分门槛
const statusFilter = ref('all')       // §10.B.5 状态过滤

// 列表项 ref 映射 (用于 scrollIntoView)
const itemRefs = {}
function setItemRef(id, el) {
  if (el) itemRefs[id] = el
}

// 计算属性
const viewpoints = computed(() => vpStore.index)
const routes = computed(() => routeStore.index)
const forecasts = computed(() => vpStore.forecasts)
const selectedDate = computed(() => vpStore.selectedDate)

const availableDates = computed(() => {
  const first = Object.values(forecasts.value)[0]
  return first?.daily?.map(d => d.date) ?? []
})

// 筛选后的观景台 (合并事件类型 + 评分门槛 + 状态过滤 §10.B.5)
const filteredViewpoints = computed(() => {
  let list = viewpoints.value

  // 事件类型筛选
  if (activeFilters.value.length > 0) {
    list = list.filter(vp =>
      vp.capabilities?.some(cap =>
        activeFilters.value.some(f => cap.includes(f))
      )
    )
  }

  // 评分门槛筛选 (§10.B.5)
  if (scoreThreshold.value > 0) {
    list = list.filter(vp => getBestScore(vp.id) >= scoreThreshold.value)
  }

  // 状态过滤 (§10.B.5)
  if (statusFilter.value !== 'all') {
    list = list.filter(vp => {
      const score = getBestScore(vp.id)
      if (statusFilter.value === 'recommended') return score >= 80
      if (statusFilter.value === 'possible') return score >= 50
      return true
    })
  }

  return list
})

// 排序后的观景台
const sortedViewpoints = computed(() => {
  const list = [...filteredViewpoints.value]
  switch (sortBy.value) {
    case 'score':
      return list.sort((a, b) => getBestScore(b.id) - getBestScore(a.id))
    case 'name':
      return list.sort((a, b) => a.name.localeCompare(b.name, 'zh'))
    case 'distance':
      // 距离排序需要用户定位，暂按名称排序
      return list.sort((a, b) => a.name.localeCompare(b.name, 'zh'))
    default:
      return list
  }
})

// 获取某个观景台的最佳评分
function getBestScore(vpId) {
  const forecast = forecasts.value[vpId]
  if (!forecast) return 0
  const today = forecast.daily?.[0]
  return today?.best_event?.score ?? today?.events?.[0]?.score ?? 0
}

// === Intersection Observer 联动 (§10.B.3) ===

let observer = null

function setupIntersectionObserver() {
  observer = new IntersectionObserver((entries) => {
    const visible = entries.find(e => e.isIntersecting)
    if (visible) {
      const vpId = visible.target.dataset?.viewpointId
      if (vpId && vpId !== highlightedId.value) {
        highlightedId.value = vpId
        // 地图联动 panTo
        const vp = viewpoints.value.find(v => v.id === vpId)
        if (vp && mapPanelRef.value) {
          mapPanelRef.value.panTo(vp.location.lon, vp.location.lat)
        }
      }
    }
  }, { threshold: 0.6 })
}

// === 事件处理 ===

function onMapReady(map) {
  mapInstance.value = map
}

function onMarkerClick(vp) {
  highlightedId.value = vp.id
  // 滚动列表至对应卡片
  const itemEl = itemRefs[vp.id]?.$el
  if (itemEl) {
    itemEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
    // 闪烁高亮效果
    itemEl.classList.add('flash-highlight')
    setTimeout(() => itemEl.classList.remove('flash-highlight'), 1000)
  }
}

function onCardClick(vp) {
  highlightedId.value = vp.id
  // 地图 flyTo (§10.B.3: 点击卡片用 flyTo，区别于滚动联动 panTo)
  if (mapPanelRef.value) {
    mapPanelRef.value.flyTo(vp.location.lon, vp.location.lat)
  }
}

function onCardExpand(vp) {
  expandedId.value = expandedId.value === vp.id ? null : vp.id
  if (expandedId.value) {
    onCardClick(vp)
  }
}

function onSearch(vpId) {
  const vp = viewpoints.value.find(v => v.id === vpId)
  if (vp) {
    onMarkerClick(vp)
    onCardExpand(vp)
  }
}

function onFilter(filters) {
  activeFilters.value = filters
}

function onDateChange(date) {
  vpStore.selectDate(date)
}

function onSortChange(key) {
  sortBy.value = key
}

function onTabChange(tab) {
  activeTab.value = tab
}

function onScoreThresholdChange(val) {
  scoreThreshold.value = val
}

function onStatusFilterChange(val) {
  statusFilter.value = val
}

function onRatioChange(ratio) {
  // 比例变化时可做地图 resize
  nextTick(() => {
    mapInstance.value?.resize?.()
  })
}

function onMapHidden() {
  // 地图隐藏时释放资源
}

function onMapRestored() {
  nextTick(() => {
    mapInstance.value?.resize?.()
  })
}

function onRouteClick(route) {
  router.push(`/route/${route.id}`)
}

function goToDetail(vpId) {
  router.push(`/viewpoint/${vpId}`)
}

// === 初始化 ===

onMounted(async () => {
  await vpStore.loadIndex()
  await routeStore.loadIndex()

  // B 方案: 并发加载所有观景台的 forecast (参考 §10.B.11)
  const allLoads = viewpoints.value.map(vp => vpStore.loadForecast(vp.id))
  await Promise.allSettled(allLoads)

  // 设置 Intersection Observer
  setupIntersectionObserver()
  await nextTick()
  document.querySelectorAll('[data-viewpoint-id]').forEach(el => {
    observer?.observe(el)
  })
})
</script>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-primary);
}

.viewpoint-list,
.route-list {
  padding: 8px;
}

.screenshot-btn {
  position: fixed;
  right: 16px;
  bottom: 24px;
  z-index: 90;
}

/* 点击 Marker 后卡片闪烁 */
:deep(.flash-highlight) {
  animation: flash 0.5s ease-out 2;
}

@keyframes flash {
  0%, 100% { background: transparent; }
  50% { background: rgba(59, 130, 246, 0.1); }
}

/* 横屏适配 (Desktop) */
@media (min-width: 1024px) {
  .home-view :deep(.split-container) {
    flex-direction: row;
  }
  .home-view :deep(.split-map) {
    width: 40%;
    height: 100% !important;
  }
  .home-view :deep(.drag-bar) {
    cursor: col-resize;
    width: 24px;
    height: 100%;
  }
}
</style>
```

**Step 1: 替换 HomeView.vue**

> [!IMPORTANT]
> 由于 HomeView.vue 在 A/B/C 三方案间是不同的，实际部署时需要通过构建时配置或路由条件来切换。开发阶段直接替换即可。

**Step 2: 提交**

```bash
git add frontend/src/views/HomeView.vue
git commit -m "feat(frontend-b): implement split-list HomeView with map-list sync"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 访问首页 → 上部地图 (35%) + 下部列表 (65%)
2. 拖拽分割条 → 比例平滑调整
3. 向上拖至极限 → 地图隐藏，出现"显示地图"按钮
4. 双击分割条 → 恢复 35%/65% 默认比例
5. 搜索框输入"牛背" → 下拉显示匹配结果
6. 事件类型筛选 → 列表过滤 + 地图 Marker 过滤
7. 排序切换 → 卡片重排
8. 滚动列表 → 地图联动 panTo
9. 点击 Marker → 列表滚动至对应卡片 + 闪烁高亮

```bash
# 确认构建不报错
npm run build
```
