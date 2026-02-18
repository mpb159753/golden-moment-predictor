# MC4: C 方案 — 动画与优化

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 为 C 方案添加所有特有动画效果 (卡片入场、Swiper 过渡、3D 翻转增强、Perfect 粒子、颜色渐变)，并进行性能优化。

**依赖模块:** MC1 (首页布局), MC2 (核心卡片), GSAP

---

## 背景

C 方案的视觉冲击力依赖于精心设计的动画效果。从卡片首次入场到滑动切换、3D 翻转、Perfect 评分的金色粒子光效，每个交互节点都需要流畅的动画增强体验。

### 设计参考

- [10-frontend-C-card-flow.md §10.C.9 特有动画](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-C-card-flow.md)

### 动画清单

| 动画 | 效果 | 时机 |
|------|------|------|
| **卡片入场** | 从底部弹起 + 旋转微晃 (spring) | 首次加载 |
| **滑动切换** | Cards effect 堆叠推送 | 左右滑动 |
| **背景飞行** | 底层地图 flyTo + 缩放 | 切换卡片时 800ms |
| **3D 翻转** | Y 轴 180° 翻转 (perspective) | 点击卡片正面 |
| **评分环填充** | 弧线从 0 渐进填满到目标分数 | 卡片进入视口 |
| **粒子效果** | 金色光点飘散 | Perfect 评分卡片 |
| **渐变脉冲** | 卡片边框发光呼吸 | Recommended 卡片 |
| **颜色渐变** | 顶栏颜色平滑过渡 | 卡片切换时 |
| **背景正反切换** | 模糊程度变化 | 卡片翻转时 |

---

## Task 1: 卡片入场动画 (GSAP)

**Files:**
- Modify: `frontend/src/components/scheme-c/CardSwiper.vue`

### 效果

首次加载时，卡片从底部弹起 + 微小旋转晃动 (spring 物理效果):

```javascript
import gsap from 'gsap'

function animateCardEntrance() {
  const slides = document.querySelectorAll('.card-slide')
  gsap.from(slides, {
    y: 200,
    rotation: 5,
    opacity: 0,
    duration: 0.8,
    ease: 'elastic.out(1, 0.6)',
    stagger: 0.1,
  })
}
```

在 `onMounted` 中，数据加载完成后调用:

```javascript
onMounted(async () => {
  // 等待 Swiper 初始化 + 数据加载
  await nextTick()
  animateCardEntrance()
})
```

**Step 1: 添加 GSAP 入场动画**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/CardSwiper.vue
git commit -m "feat(frontend-c): add GSAP spring entrance animation for cards"
```

---

## Task 2: Perfect 粒子光效

**Files:**
- Modify: `frontend/src/components/scheme-c/CardFront.vue`

### CSS 粒子效果 (参考 §10.C.9)

Perfect 评分 (95+) 的卡片显示金色光芒脉冲:

```css
/* Perfect 评分粒子光效 */
.card--perfect::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  background: radial-gradient(circle at 50% 30%, rgba(255, 215, 0, 0.3), transparent 60%);
  animation: sparkle 3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes sparkle {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
```

### Recommended 边框呼吸发光

```css
.card--recommended {
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
  animation: glow-pulse 4s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.2); }
  50% { box-shadow: 0 0 40px rgba(16, 185, 129, 0.5); }
}
```

**Step 1: 添加 CSS 动画效果**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/CardFront.vue
git commit -m "feat(frontend-c): add sparkle and glow-pulse animations for score states"
```

---

## Task 3: 顶栏颜色渐变过渡

**Files:**
- Modify: `frontend/src/components/scheme-c/CardTopBar.vue`
- Modify: `frontend/src/views/HomeView.vue`

### 效果

卡片切换时，顶栏背景色平滑过渡，反映当前卡片的评分色:

### 实现

在 `CardTopBar.vue` 中添加动态颜色:

```vue
<script setup>
// 新增 prop
const props = defineProps({
  // ... 现有 props
  accentColor: { type: String, default: 'rgba(0, 0, 0, 0.3)' },
})
</script>

<style scoped>
.card-top-bar {
  /* 移除固定 background，使用动态绑定 */
  background: v-bind('props.accentColor');
  transition: background 500ms ease;
}
</style>
```

在 `HomeView.vue` 中计算颜色:

```javascript
import { useScoreColor } from '@/composables/useScoreColor'

const { getColor } = useScoreColor()

const topBarColor = computed(() => {
  const vp = currentViewpoint.value
  if (!vp) return 'rgba(0, 0, 0, 0.3)'
  const forecast = forecasts.value[vp.id]
  const score = forecast?.daily?.[0]?.best_event?.score ?? 0
  const color = getColor(score)
  return `${color}40`  // 加透明度后缀
})
```

**Step 1: 添加颜色过渡**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/CardTopBar.vue frontend/src/views/HomeView.vue
git commit -m "feat(frontend-c): add accent color transition to CardTopBar on slide change"
```

---

## Task 4: 3D 翻转增强 + 背景模糊变化

**Files:**
- Modify: `frontend/src/components/scheme-c/PredictionCard.vue`
- Modify: `frontend/src/components/scheme-c/BackgroundMap.vue`

### 翻转时背景模糊度变化

卡片翻转到背面时，背景模糊度增加，让注意力集中在数据上:

在 `PredictionCard.vue` 中:

```javascript
const emit = defineEmits(['click', 'view-detail', 'long-press', 'flip-state'])

function toggleFlip() {
  isFlipped.value = !isFlipped.value
  emit('click', props.viewpoint?.id)
  emit('flip-state', isFlipped.value)
}
```

在 `BackgroundMap.vue` 中添加动态模糊:

```vue
<template>
  <div class="background-map">
    <div id="bg-map" class="map-layer" />
    <div
      class="blur-overlay"
      :style="{ backdropFilter: `blur(${blurAmount}px)` }"
    />
  </div>
</template>

<script setup>
const props = defineProps({
  center: { type: Array, default: () => [102.0, 30.5] },
  zoom: { type: Number, default: 11 },
  extraBlur: { type: Boolean, default: false },
})

const blurAmount = computed(() => props.extraBlur ? 30 : 20)
</script>
```

在 `HomeView.vue` 中连接:

```javascript
const isCardFlipped = ref(false)

function onCardFlipState(flipped) {
  isCardFlipped.value = flipped
}
```

```html
<BackgroundMap :extra-blur="isCardFlipped" ... />
```

**Step 1: 翻转与背景联动**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/PredictionCard.vue \
       frontend/src/components/scheme-c/BackgroundMap.vue \
       frontend/src/views/HomeView.vue
git commit -m "feat(frontend-c): link card flip state to background blur intensity"
```

---

## Task 5: 评分环填充动画 + 性能优化

**Files:**
- Modify: `frontend/src/components/scheme-c/CardSwiper.vue`

### 评分环 IntersectionObserver

卡片进入视口时触发 ScoreRing 的填充动画 (ScoreRing 的 `animated` prop 已支持，但需要在卡片可见时重新触发):

```javascript
import { onMounted } from 'vue'

onMounted(() => {
  // Swiper 的 slideChange 事件已经在 onSlideChange 中处理
  // ScoreRing 的 animated=true 会在首次渲染时触发
  // 如果需要每次滑入都重新触发，可使用 key 强制重新挂载
})
```

### 性能优化: 懒加载卡片

仅渲染当前卡片 ± 2 张:

```javascript
const visibleRange = computed(() => {
  const idx = currentIndex.value
  return {
    start: Math.max(0, idx - 2),
    end: Math.min(props.viewpoints.length - 1, idx + 2),
  }
})

function isVisible(index) {
  return index >= visibleRange.value.start && index <= visibleRange.value.end
}
```

在模板中:

```html
<SwiperSlide v-for="(vp, index) in viewpoints" :key="vp.id">
  <PredictionCard v-if="isVisible(index)" ... />
  <div v-else class="skeleton-card" />
</SwiperSlide>
```

### 骨架卡片样式

```css
.skeleton-card {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg);
  background: linear-gradient(160deg, #2a2a2a, #3a3a3a);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}
```

**Step 1: 添加懒加载和骨架**

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-c/CardSwiper.vue
git commit -m "feat(frontend-c): add lazy card rendering and skeleton placeholder"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 首次加载 → 卡片从底部弹起 + 微旋转 (spring 效果)
2. Perfect 评分卡片 → 金色光芒脉冲动画
3. Recommended 卡片 → 边框绿色呼吸发光
4. 切换卡片 → 顶栏颜色平滑过渡
5. 点击翻转 → 背景模糊度增加
6. 翻转回来 → 背景模糊度恢复
7. 快速滑动 → 骨架占位卡片显示，性能流畅
8. 评分环 → 卡片进入视口时弧线渐进填充

```bash
npm run build
```
