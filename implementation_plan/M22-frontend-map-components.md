# M22: 前端地图组件 (AMapContainer / ViewpointMarker / RouteLine)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现三个地图公共组件，封装高德地图的初始化、标记点和线路展示。

**依赖模块:** M16 (项目初始化), M18 (useAMap, useScoreColor)

---

## 背景

地图组件被方案 A (沉浸地图) 和方案 B (分屏浏览) 直接使用，方案 C (卡片流) 作为背景层使用。三个方案虽然布局不同，但底层地图能力一致。

### 设计参考

- [10-frontend-common.md §10.0.5 地图公共层](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)

---

## Task 1: AMapContainer 地图容器

**Files:**
- Create: `frontend/src/components/map/AMapContainer.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `mapOptions` | Object | {} | 覆盖默认地图选项 |
| `height` | String | '100%' | 容器高度 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `ready` | map 实例 | 地图初始化完成 |

### 实现

```vue
<!-- frontend/src/components/map/AMapContainer.vue -->
<template>
  <div
    ref="containerRef"
    :id="containerId"
    class="amap-container"
    :style="{ height }"
  />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAMap } from '@/composables/useAMap'

const props = defineProps({
  mapOptions: { type: Object, default: () => ({}) },
  height: { type: String, default: '100%' },
})

const emit = defineEmits(['ready'])

const containerId = `amap-${Date.now()}`
const containerRef = ref(null)
const { init, destroy, map } = useAMap(containerId)

onMounted(async () => {
  await init(props.mapOptions)
  emit('ready', map())
})

onUnmounted(() => {
  destroy()
})

// 暴露地图操作方法给父组件
defineExpose({
  getMap: () => map(),
})
</script>

<style scoped>
.amap-container {
  width: 100%;
  min-height: 200px;
}
</style>
```

---

## Task 2: ViewpointMarker 评分标记

**Files:**
- Create: `frontend/src/components/map/ViewpointMarker.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoint` | Object | — | { id, name, location: {lat, lon} } |
| `score` | Number | 0 | 最佳事件评分 |
| `selected` | Boolean | false | 是否选中 |

### 标记样式

- **常态:** 40x40px 圆形，背景色 = 评分颜色，白色数字
- **选中:** 放大 1.2x + 弹跳动画 + 阴影加深
- **Perfect (95+):** 额外脉冲光圈动画

### 实现说明

本组件并非独立渲染的 Vue 组件，而是通过 `useAMap.addMarker()` 创建 DOM 标记后挂载。但封装为 Vue 组件方便在模板中声明式使用:

```vue
<!-- 使用方式 (在方案特定布局中) -->
<AMapContainer @ready="onMapReady">
  <ViewpointMarker
    v-for="vp in viewpoints"
    :key="vp.id"
    :viewpoint="vp"
    :score="getBestScore(vp.id)"
    :selected="selectedId === vp.id"
    @click="onMarkerClick(vp)"
  />
</AMapContainer>
```

实际实现使用 render function 或 watch 监听 props 变化来操作 AMap Marker 实例。

---

## Task 3: RouteLine 线路连线

**Files:**
- Create: `frontend/src/components/map/RouteLine.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `stops` | Array | [] | 线路站点 (含 location) |
| `highlighted` | Boolean | false | 是否高亮 |

### 样式

- **常态:** 虚线、3px 宽度、蓝色
- **高亮:** 实线、4px 宽度、加深颜色
- 箭头方向: 按 stops 顺序
- hover 时自动高亮

---

## 验证

地图组件依赖浏览器 + 高德 SDK，不做单元测试。通过以下方式验证:

```bash
# 启动开发服务器
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 访问首页 → 地图正常加载
2. 看到观景台标记 (来自 `public/data/index.json` 真实数据)
3. 标记颜色对应评分
4. 点击标记 → emit click 事件
5. 线路连线正确连接两站
