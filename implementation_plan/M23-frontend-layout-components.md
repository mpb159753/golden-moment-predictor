# M23: 前端布局通用组件 (DatePicker / FilterBar / UpdateBanner)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现三个布局通用组件，提供日期选择、事件筛选和数据更新时间提示功能。

**依赖模块:** M16 (项目初始化), M17 (Pinia Store)

---

## 背景

布局通用组件在三个方案的首页和详情页中被复用。

### 设计参考

- [10-frontend-common.md §10.0.3 布局通用](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)

---

## Task 1: DatePicker 日期选择器

**Files:**
- Create: `frontend/src/components/layout/DatePicker.vue`
- Test: `frontend/src/__tests__/components/DatePicker.test.js`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `modelValue` | String | — | 选中日期 'YYYY-MM-DD' (v-model) |
| `dates` | Array | [] | 可选日期列表 (forecast 中有数据的日期) |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `update:modelValue` | String | 选中的日期 |

### 实现

水平滚动日期选择器 (Pills 形式):

```
┌───┐ ┌───┐ ┌─────┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐
│2/12│ │2/13│ │ 2/14 │ │2/15│ │2/16│ │2/17│ │2/18│
│ 三 │ │ 四 │ │  五  │ │ 六 │ │ 日 │ │ 一 │ │ 二 │
└───┘ └───┘ └─────┘ └───┘ └───┘ └───┘ └───┘
               ▲ 选中 (高亮)
```

- 水平滚动，居中对齐
- 选中日期高亮 (主色背景 + 白色文字)
- 支持左右箭头键盘导航

---

## Task 2: FilterBar 筛选栏

**Files:**
- Create: `frontend/src/components/layout/FilterBar.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `eventTypes` | Array | [] | 可用的事件类型列表 |
| `selectedEvent` | String/null | null | 当前筛选的事件类型 (v-model) |
| `minScore` | Number | 0 | 最低评分筛选 (v-model) |

### 实现

```
[全部 ▼] [日出金山 ☀️] [云海 ☁️] [观星 ⭐] [雾凇 ❄️]  评分 ≥ [50 ▼]
```

- 事件类型 pill 按钮，点击切换
- 评分下拉: 0 / 50 / 80 / 95
- 使用 EventIcon 显示各事件图标

---

## Task 3: UpdateBanner 数据更新时间提示

**Files:**
- Create: `frontend/src/components/layout/UpdateBanner.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `meta` | Object | null | meta.json 内容 |

### 实现

```vue
<!-- frontend/src/components/layout/UpdateBanner.vue -->
<template>
  <div v-if="meta" class="update-banner">
    <span class="update-banner__icon">🔄</span>
    <span class="update-banner__text">
      数据更新于 {{ formatTime(meta.generated_at) }}
    </span>
  </div>
</template>

<script setup>
defineProps({
  meta: { type: Object, default: null },
})

function formatTime(isoString) {
  if (!isoString) return '—'
  const d = new Date(isoString)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<style scoped>
.update-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-card);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  color: var(--text-muted);
  box-shadow: var(--shadow-card);
}
</style>
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/components/DatePicker.test.js
```
