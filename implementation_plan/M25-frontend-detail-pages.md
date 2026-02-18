# M25: 前端共享详情页 (ViewpointDetail / RouteDetail)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现三方案共用的观景台详情页和线路详情页，组装所有公共组件形成完整的详情展示。

**依赖模块:** M17 (Pinia Store), M19-M24 (所有公共组件)

---

## 背景

根据 [10-frontend-common.md §10.0.8](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md) 的路由设计:

> **详情页共享**: `ViewpointDetail.vue` 和 `RouteDetail.vue` 是三方案共用的详情页面，内部使用公共组件组装。各方案的差异仅体现在**首页布局**和**导航至详情的过渡动画**上。

### 路由映射

| 路由 | 组件 | 说明 |
|------|------|------|
| `/viewpoint/:id` | ViewpointDetail.vue | 观景台详情 (默认当日) |
| `/viewpoint/:id/:date` | ViewpointDetail.vue | 指定日期详情 |
| `/route/:id` | RouteDetail.vue | 线路详情 |

---

## Task 1: ViewpointDetail 观景台详情页

**Files:**
- Modify: `frontend/src/views/ViewpointDetail.vue` (替换占位)

### 页面布局

```
┌──────────────────────────────────┐
│  ← 返回    牛背山    📷 截图     │  ← 顶栏
├──────────────────────────────────┤
│  [UpdateBanner]: 更新于 2/12 05:00│
├──────────────────────────────────┤
│  [DatePicker]: 2/12 | 2/13 | ... │  ← 日期选择
├──────────────────────────────────┤
│  [DaySummary 当日摘要]            │
│  ─────────────────────────       │
│  [EventList 事件卡片列表]         │
│  ─────────────────────────       │
│  [HourlyTimeline 逐时时间线]      │
│  ─────────────────────────       │
│  [WeekTrend 七日趋势图]          │
├──────────────────────────────────┤
│  [ScreenshotBtn] [分享按钮]       │  ← 底部操作
└──────────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/views/ViewpointDetail.vue -->
<template>
  <div class="viewpoint-detail" ref="screenshotArea">
    <!-- 顶栏 -->
    <header class="detail-header">
      <button @click="$router.back()" class="back-btn">← 返回</button>
      <h1>{{ viewpoint?.name }}</h1>
      <ScreenshotBtn :target="screenshotArea" :filename="`gmp-${id}.png`" />
    </header>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-spinner">加载中...</div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-message">{{ error }}</div>

    <!-- 主内容 -->
    <main v-else>
      <UpdateBanner :meta="store.meta" />

      <DatePicker
        v-model="selectedDate"
        :dates="availableDates"
      />

      <!-- 当日摘要 -->
      <section v-if="currentDay">
        <DaySummary :day="currentDay" :clickable="false" />
      </section>

      <!-- 事件列表 -->
      <section>
        <h2>景观预测</h2>
        <EventList :events="currentDay?.events ?? []" showBreakdown />
      </section>

      <!-- 逐时时间线 -->
      <section v-if="timeline">
        <h2>逐时详情</h2>
        <HourlyTimeline :hourly="timeline.hourly" />
      </section>

      <!-- 七日趋势 -->
      <section v-if="forecast">
        <h2>七日趋势</h2>
        <WeekTrend :daily="forecast.daily" @select="onDateSelect" />
      </section>

      <!-- 底部操作 -->
      <div class="detail-actions">
        <ScreenshotBtn :target="screenshotArea" />
        <button @click="showShareCard = true" class="share-btn">分享</button>
      </div>
    </main>

    <!-- 分享卡片 -->
    <ShareCard
      :visible="showShareCard"
      :viewpoint="viewpoint"
      :day="currentDay"
      @close="showShareCard = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useViewpointStore } from '@/stores/viewpoints'
// 导入所有公共组件...

const props = defineProps({
  id: { type: String, required: true },
  date: { type: String, default: null },
})

const store = useViewpointStore()
const screenshotArea = ref(null)
const showShareCard = ref(false)

// 计算属性
const viewpoint = computed(() => store.currentViewpoint)
const forecast = computed(() => store.currentForecast)
const loading = computed(() => store.loading)
const error = computed(() => store.error)
const timeline = computed(() => store.currentTimeline)

const selectedDate = computed({
  get: () => store.selectedDate,
  set: (val) => store.selectDate(val),
})

const availableDates = computed(() =>
  forecast.value?.daily?.map(d => d.date) ?? []
)

const currentDay = computed(() =>
  forecast.value?.daily?.find(d => d.date === selectedDate.value)
)

// 初始化
onMounted(async () => {
  await store.selectViewpoint(props.id)
  if (props.date) {
    await store.selectDate(props.date)
  }
})

// 监听路由参数变化
watch(() => props.id, async (newId) => {
  await store.selectViewpoint(newId)
})

function onDateSelect(date) {
  store.selectDate(date)
}
</script>

<style scoped>
.viewpoint-detail {
  max-width: 640px;
  margin: 0 auto;
  padding: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
}

.detail-header h1 {
  font-size: var(--text-xl);
  font-weight: 700;
}

.back-btn {
  background: none;
  border: none;
  font-size: var(--text-base);
  color: var(--color-primary);
  cursor: pointer;
}

section {
  margin-bottom: 24px;
}

section h2 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.detail-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 20px 0;
}

.share-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
  font-size: var(--text-sm);
}
</style>
```

---

## Task 2: RouteDetail 线路详情页

**Files:**
- Modify: `frontend/src/views/RouteDetail.vue` (替换占位)

### 页面布局

```
┌──────────────────────────────────┐
│  ← 返回    理小路    📷 截图     │
├──────────────────────────────────┤
│  [地图: 线路全貌 + 各站标记]      │
├──────────────────────────────────┤
│  站点 1/2: 折多山                │
│  [DaySummary]                    │
│  ─────────────────────────       │
│  站点 2/2: 牛背山                │
│  [DaySummary]                    │
│  ─────────────────────────       │
│  [WeekTrend: 各站对比]           │
└──────────────────────────────────┘
```

### 线路数据结构参考

[05-api.md §5.2 routes/{id}/forecast.json](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md)

```javascript
// 线路预测以 stops 为顶层组织
{
  route_id: 'lixiao',
  stops: [
    {
      viewpoint_id: 'zheduo_gongga',
      viewpoint_name: '折多山',
      order: 1,
      stay_note: '建议停留2小时观赏日出金山',
      forecast: { /* 与单站 forecast.json 结构一致 */ }
    },
    // ...
  ]
}
```

### 实现

遍历 `stops` 数组，每站渲染一个 `DaySummary` 摘要。点击站点可跳转到该观景台的详情页。

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 访问 `/viewpoint/niubei_gongga` → 详情页正常渲染
2. 日期选择器切换日期 → 数据联动更新
3. 事件卡片展示评分明细
4. 七日趋势图正确绘制
5. 截图按钮可用
6. 分享卡片弹出 → 截图下载
7. 访问 `/route/lixiao` → 线路详情显示 2 个站点
