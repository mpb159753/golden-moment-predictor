# M19: 前端评分可视化组件 (ScoreRing / ScoreBar / StatusBadge)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现三个评分可视化公共组件，作为所有方案共享的评分展示基础。

**依赖模块:** M16 (项目初始化), M18 (useScoreColor)

---

## 背景

评分可视化是 GMP 前端最核心的视觉要素。三个评分组件在首页 Marker、卡片列表、详情页中被广泛复用。

### 设计参考

- [10-frontend-common.md §10.0.3 ScoreRing/StatusBadge](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)

### 评分颜色映射 (useScoreColor 提供)

| 范围 | 颜色 | 状态 |
|------|------|------|
| 95-100 | 金色渐变 | Perfect |
| 80-94 | 翠绿 | Recommended |
| 50-79 | 琥珀 | Possible |
| 0-49 | 灰色 | Not Recommended |

---

## Task 1: ScoreRing 环形评分组件

**Files:**
- Create: `frontend/src/components/score/ScoreRing.vue`
- Test: `frontend/src/__tests__/components/ScoreRing.test.js`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `score` | Number | 0 | 0-100 评分 |
| `size` | String | `'md'` | `'sm'` / `'md'` / `'lg'` / `'xl'` |
| `showLabel` | Boolean | true | 是否显示中心数字 |
| `animated` | Boolean | true | 是否动画过渡 |

### 尺寸规格

| Size | 直径 | 环宽 | 字号 | 用途 |
|------|------|------|------|------|
| `sm` | 32px | 3px | 12px | 列表项内嵌 |
| `md` | 48px | 4px | 16px | 卡片内标题旁 |
| `lg` | 72px | 5px | 24px | 详情页标题 |
| `xl` | 120px | 6px | 48px | 卡片流方案主评分 |

### 实现要点

```vue
<!-- frontend/src/components/score/ScoreRing.vue -->
<template>
  <div class="score-ring" :class="[`score-ring--${size}`]">
    <svg :width="diameter" :height="diameter" :viewBox="`0 0 ${diameter} ${diameter}`">
      <!-- 背景环 -->
      <circle
        :cx="center" :cy="center" :r="radius"
        fill="none"
        stroke="#E5E7EB"
        :stroke-width="strokeWidth"
      />
      <!-- 评分环 -->
      <circle
        :cx="center" :cy="center" :r="radius"
        fill="none"
        :stroke="colorInfo.gradient ? 'url(#scoreGradient)' : colorInfo.color"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        :style="animated ? { transition: 'stroke-dashoffset 1s var(--ease-out-expo)' } : {}"
        transform="rotate(-90, center, center)"
      />
      <!-- 渐变定义 (仅 Perfect 使用) -->
      <defs v-if="colorInfo.gradient">
        <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#FFD700" />
          <stop offset="100%" stop-color="#FF8C00" />
        </linearGradient>
      </defs>
    </svg>
    <!-- 中心数字 -->
    <span v-if="showLabel" class="score-ring__label" :style="{ fontSize: labelSize }">
      {{ score }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
  score: { type: Number, default: 0 },
  size: { type: String, default: 'md', validator: v => ['sm', 'md', 'lg', 'xl'].includes(v) },
  showLabel: { type: Boolean, default: true },
  animated: { type: Boolean, default: true },
})

const { getScoreColor } = useScoreColor()

const sizeMap = {
  sm:  { diameter: 32, strokeWidth: 3, labelSize: '12px' },
  md:  { diameter: 48, strokeWidth: 4, labelSize: '16px' },
  lg:  { diameter: 72, strokeWidth: 5, labelSize: '24px' },
  xl:  { diameter: 120, strokeWidth: 6, labelSize: '48px' },
}

const config = computed(() => sizeMap[props.size])
const diameter = computed(() => config.value.diameter)
const strokeWidth = computed(() => config.value.strokeWidth)
const labelSize = computed(() => config.value.labelSize)
const center = computed(() => diameter.value / 2)
const radius = computed(() => center.value - strokeWidth.value)
const circumference = computed(() => 2 * Math.PI * radius.value)
const dashOffset = computed(() => circumference.value * (1 - props.score / 100))
const colorInfo = computed(() => getScoreColor(props.score))
</script>

<style scoped>
.score-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.score-ring__label {
  position: absolute;
  font-weight: 700;
  color: var(--text-primary);
}
</style>
```

### 应测试的内容

- 渲染: 传入 score=85, size='md' → SVG 正确渲染
- Props 验证: size 只接受 sm/md/lg/xl
- 颜色: score=96 → 使用渐变色
- 颜色: score=85 → 使用翠绿
- showLabel=false → 不显示数字
- dashOffset 计算正确: score=50 → offset = 50% circumference

---

## Task 2: ScoreBar 条形评分组件

**Files:**
- Create: `frontend/src/components/score/ScoreBar.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `score` | Number | 0 | 0-100 |
| `label` | String | '' | 维度名称 (如"光路通畅") |
| `max` | Number | 100 | 满分值 |
| `showValues` | Boolean | true | 显示 "得分/满分" 文字 |

### 实现

```vue
<!-- frontend/src/components/score/ScoreBar.vue -->
<template>
  <div class="score-bar">
    <div class="score-bar__header">
      <span class="score-bar__label">{{ label }}</span>
      <span v-if="showValues" class="score-bar__values">{{ score }} / {{ max }}</span>
    </div>
    <div class="score-bar__track">
      <div
        class="score-bar__fill"
        :style="{
          width: `${percentage}%`,
          backgroundColor: colorInfo.color,
          backgroundImage: colorInfo.gradient || 'none',
          transition: 'width 0.8s var(--ease-out-expo)',
        }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
  score: { type: Number, default: 0 },
  label: { type: String, default: '' },
  max: { type: Number, default: 100 },
  showValues: { type: Boolean, default: true },
})

const { getScoreColor } = useScoreColor()
const percentage = computed(() => props.max > 0 ? (props.score / props.max) * 100 : 0)
const normalizedScore = computed(() => props.max > 0 ? Math.round((props.score / props.max) * 100) : 0)
const colorInfo = computed(() => getScoreColor(normalizedScore.value))
</script>

<style scoped>
.score-bar__track {
  height: 6px;
  background: #E5E7EB;
  border-radius: var(--radius-full);
  overflow: hidden;
}

.score-bar__fill {
  height: 100%;
  border-radius: var(--radius-full);
}

.score-bar__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: var(--text-sm);
}

.score-bar__label {
  color: var(--text-secondary);
}

.score-bar__values {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
</style>
```

---

## Task 3: StatusBadge 状态标签组件

**Files:**
- Create: `frontend/src/components/score/StatusBadge.vue`
- Test: `frontend/src/__tests__/components/StatusBadge.test.js`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `status` | String | — | `'Perfect'` / `'Recommended'` / `'Possible'` / `'Not Recommended'` |
| `lang` | String | `'cn'` | `'cn'` 中文 / `'en'` 英文 |

### 实现

```vue
<!-- frontend/src/components/score/StatusBadge.vue -->
<template>
  <span
    class="status-badge"
    :style="{
      backgroundColor: bgColor,
      color: textColor,
    }"
  >
    {{ displayText }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: v => ['Perfect', 'Recommended', 'Possible', 'Not Recommended'].includes(v),
  },
  lang: { type: String, default: 'cn' },
})

const { getStatusColor } = useScoreColor()

const labelMap = {
  cn: {
    'Perfect': '完美',
    'Recommended': '推荐',
    'Possible': '一般',
    'Not Recommended': '不推荐',
  },
  en: {
    'Perfect': 'Perfect',
    'Recommended': 'Recommended',
    'Possible': 'Possible',
    'Not Recommended': 'Not Recommended',
  },
}

const displayText = computed(() => labelMap[props.lang]?.[props.status] ?? props.status)
const baseColor = computed(() => getStatusColor(props.status))
const bgColor = computed(() => `${baseColor.value}20`) // 12% 透明度背景
const textColor = computed(() => baseColor.value)
</script>

<style scoped>
.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
  white-space: nowrap;
}
</style>
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/components/ScoreRing.test.js
npx vitest run src/__tests__/components/StatusBadge.test.js
```
