# M24: 前端导出组件 (ScreenshotBtn / ShareCard)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现截图导出按钮和社交分享卡片合成组件。

**依赖模块:** M16 (项目初始化), M18 (useScreenshot)

---

## 背景

运营每日需截取素材发小红书帖子。前端提供一键截图和分享卡片合成功能。

### 设计参考

- [10-frontend-common.md §10.0.6 截图导出](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [10-frontend.md §10.5 截图需求](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend.md)

### 小红书截图需求

| 截图类型 | 内容 | 尺寸 |
|---------|------|------|
| 地图总览 | 地图上所有观景台标记 + 当日最佳评分 | 自适应 |
| 单日预测卡片 | 某观景台某日的详细预测 | 自适应 |
| 分享卡片 | 合成品牌图 | 1080×1440 (竖版) |

---

## Task 1: ScreenshotBtn 截图按钮

**Files:**
- Create: `frontend/src/components/export/ScreenshotBtn.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `target` | [String, Object] | — | 截图目标: CSS 选择器或 ref |
| `filename` | String | 'gmp-prediction.png' | 下载文件名 |

### 实现

```vue
<!-- frontend/src/components/export/ScreenshotBtn.vue -->
<template>
  <button
    class="screenshot-btn"
    :class="{ 'screenshot-btn--loading': capturing }"
    @click="handleCapture"
    :disabled="capturing"
  >
    <span v-if="!capturing" class="screenshot-btn__icon">📷</span>
    <span v-else class="screenshot-btn__spinner" />
    <span class="screenshot-btn__text">
      {{ capturing ? '截图中...' : '截图' }}
    </span>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import { useScreenshot } from '@/composables/useScreenshot'

const props = defineProps({
  target: { type: [String, Object], required: true },
  filename: { type: String, default: 'gmp-prediction.png' },
})

const { capture } = useScreenshot()
const capturing = ref(false)

async function handleCapture() {
  capturing.value = true
  try {
    const element = typeof props.target === 'string'
      ? document.querySelector(props.target)
      : props.target?.$el ?? props.target
    await capture(element, props.filename)
  } catch (e) {
    console.error('Screenshot failed:', e)
  } finally {
    capturing.value = false
  }
}
</script>

<style scoped>
.screenshot-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--bg-card);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-primary);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.screenshot-btn:hover {
  box-shadow: var(--shadow-elevated);
  transform: translateY(-1px);
}

.screenshot-btn--loading {
  opacity: 0.7;
  cursor: wait;
}

.screenshot-btn__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--text-muted);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
```

---

## Task 2: ShareCard 分享卡片

**Files:**
- Create: `frontend/src/components/export/ShareCard.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoint` | Object | — | 观景台信息 |
| `day` | Object | — | 某日预测数据 |
| `visible` | Boolean | false | 是否显示 |

### 卡片布局 (1080×1440)

```
┌──────────────────────────────┐
│                              │
│  🏔️ GMP 川西景观预测          │
│                              │
│  ┌──────────────────────┐    │
│  │                      │    │
│  │   牛背山 · 2月12日    │    │
│  │   ━━━━━━━━━━━━━━━    │    │
│  │                      │    │
│  │   [ScoreRing xl]     │    │
│  │      90              │    │
│  │   推荐出行            │    │
│  │                      │    │
│  │   🌄 日出金山  90     │    │
│  │   ☁️ 云海      90     │    │
│  │   ⭐ 观星      45     │    │
│  │                      │    │
│  │   🎯 组合日           │    │
│  │   📸 摄影师推荐        │    │
│  │                      │    │
│  └──────────────────────┘    │
│                              │
│  让每一次川西之行              │
│  都不错过自然的馈赠            │
│                              │
│            gmp.example       │
└──────────────────────────────┘
```

### 实现

```vue
<template>
  <teleport to="body">
    <div v-if="visible" class="share-overlay" @click.self="$emit('close')">
      <div ref="cardRef" class="share-card">
        <!-- 品牌头 -->
        <div class="share-card__header">
          <span class="share-card__logo">🏔️</span>
          <span class="share-card__brand">GMP 川西景观预测</span>
        </div>

        <!-- 内容区 -->
        <div class="share-card__content">
          <h2>{{ viewpoint?.name }} · {{ formatDate(day?.date) }}</h2>
          <ScoreRing :score="bestScore" size="xl" />
          <StatusBadge :status="bestStatus" />

          <div class="share-card__events">
            <div v-for="event in day?.events" :key="event.event_type" class="share-card__event-row">
              <EventIcon :eventType="event.event_type" :size="20" />
              <span>{{ event.display_name }}</span>
              <span class="share-card__event-score">{{ event.score }}</span>
            </div>
          </div>

          <!-- 标签 -->
          <div class="share-card__tags">
            <span v-for="tag in comboTags" :key="tag.type">{{ tag.icon }} {{ tag.label }}</span>
          </div>
        </div>

        <!-- 品牌底 -->
        <div class="share-card__footer">
          <p>让每一次川西之行，都不错过自然的馈赠</p>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="share-overlay__actions">
        <ScreenshotBtn :target="cardRef" filename="gmp-share.png" />
        <button @click="$emit('close')">关闭</button>
      </div>
    </div>
  </teleport>
</template>
```

---

## 验证

手动验证:
1. 在详情页点击"分享"按钮 → ShareCard 弹出
2. 点击"截图" → 下载 1080×1440 PNG
3. 检查图片质量: 文字清晰、颜色正确、品牌元素完整
