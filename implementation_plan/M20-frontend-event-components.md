# M20: 前端事件展示组件 (EventIcon / EventCard / EventList)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现景观事件展示相关的三个公共组件，提供统一的图标、卡片和列表展示。

**依赖模块:** M16 (项目初始化), M18 (useScoreColor), M19 (ScoreRing, StatusBadge)

---

## 背景

每种景观类型 (event_type) 对应独特的 SVG 图标和主题颜色。事件展示组件在列表、卡片、详情页中广泛使用。

### 设计参考

- [10-frontend-common.md §10.0.3 EventIcon](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [05-api.md §5.3 枚举值定义](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md)

### 事件类型→图标映射

| event_type | 图标文件 | 主色 | 描述 |
|------------|----------|------|------|
| `sunrise_golden_mountain` | `sunrise-golden-mountain.svg` | `#FF8C00` | 山峰 + 日出光芒 |
| `sunset_golden_mountain` | `sunset-golden-mountain.svg` | `#FF4500` | 山峰 + 夕阳光芒 |
| `cloud_sea` | `cloud-sea.svg` | `#87CEEB` | 叠层云海 |
| `stargazing` | `stargazing.svg` | `#4A0E8F` | 星空 |
| `frost` | `frost.svg` | `#B0E0E6` | 冰花/雾凇 |
| `snow_tree` | `snow-tree.svg` | `#E0E8EF` | 树挂积雪 |
| `ice_icicle` | `ice-icicle.svg` | `#ADD8E6` | 冰柱/冰挂 |

---

## Task 1: SVG 图标资源

**Files:**
- Create: `frontend/src/assets/icons/sunrise-golden-mountain.svg`
- Create: `frontend/src/assets/icons/sunset-golden-mountain.svg`
- Create: `frontend/src/assets/icons/cloud-sea.svg`
- Create: `frontend/src/assets/icons/stargazing.svg`
- Create: `frontend/src/assets/icons/frost.svg`
- Create: `frontend/src/assets/icons/snow-tree.svg`
- Create: `frontend/src/assets/icons/ice-icicle.svg`

> [!IMPORTANT]
> **SVG 图标需由专门模型生成**
>
> 以下 7 个 SVG 图标文件需要使用图标生成模型创建。当前步骤先创建**占位 SVG**，后续替换。
>
> 每个占位 SVG 使用简单的圆形 + 首字母作为临时标识。

### 图标设计要求

每个 SVG 图标需满足以下规范:

**通用规格:**
- 尺寸: 24x24 viewBox，填充区域居中
- 风格: 线性图标 (Line Icon)，2px 描边
- 格式: 单色 SVG，颜色通过 `currentColor` 继承
- 无外部依赖，纯 path 绘制

**各图标设计细节:**

1. **sunrise-golden-mountain.svg** — 日出金山
   - 前景: 三角山峰轮廓 (类似贡嘎雪山的锐利山尖)
   - 背景: 半圆太阳从山峰背后升起，3-5 道放射状光芒线
   - 整体感觉: 壮丽、神圣

2. **sunset-golden-mountain.svg** — 日落金山
   - 与日出类似，但太阳位于山峰右上方偏下，正在落入山后
   - 光芒线更粗、更少 (2-3 道)，营造温暖感
   - 可加少量云层轮廓

3. **cloud-sea.svg** — 云海
   - 底部: 2-3 层波浪状云线 (前后层叠，表示厚重云层)
   - 顶部: 小山尖从云层中突出
   - 整体感觉: 轻盈、绵延

4. **stargazing.svg** — 观星
   - 中央: 一颗较大的六角星
   - 周围: 3-4 颗小星点 (不同大小)
   - 底部: 简化的山脊线轮廓
   - 整体感觉: 静谧、深邃

5. **frost.svg** — 雾凇
   - 中央: 六角雪花结晶图案 (对称)
   - 结晶分支: 3 组对称分支，每组有细小的分叉
   - 整体感觉: 精致、晶莹

6. **snow-tree.svg** — 树挂积雪
   - 中央: 简化的松树/针叶树轮廓
   - 树冠: 不规则的积雪覆盖 (白色区域/粗描边模拟)
   - 底部: 简单的雪地线
   - 整体感觉: 安静、童话

7. **ice-icicle.svg** — 冰挂
   - 顶部: 水平岩壁/悬崖线
   - 下方: 3-5 根长短不一的冰柱垂挂
   - 冰柱: 上粗下尖，略带弧度
   - 可加 1-2 个水滴元素
   - 整体感觉: 冷峻、剔透

### 占位 SVG 模板

每个文件暂时使用以下模板 (将 `LETTER` 和 `COLOR` 替换为对应值):

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <!-- TODO: 替换为正式图标 — 见上方设计要求 -->
  <circle cx="12" cy="12" r="10" />
  <text x="12" y="16" text-anchor="middle" font-size="10" fill="currentColor" stroke="none">LETTER</text>
</svg>
```

| 文件名 | LETTER | 备注 |
|--------|--------|------|
| `sunrise-golden-mountain.svg` | 日 | 日出金山 |
| `sunset-golden-mountain.svg` | 落 | 日落金山 |
| `cloud-sea.svg` | 云 | 云海 |
| `stargazing.svg` | 星 | 观星 |
| `frost.svg` | 霜 | 雾凇 |
| `snow-tree.svg` | 雪 | 树挂 |
| `ice-icicle.svg` | 冰 | 冰挂 |

---

## Task 2: EventIcon 组件

**Files:**
- Create: `frontend/src/components/event/EventIcon.vue`
- Test: `frontend/src/__tests__/components/EventIcon.test.js`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `eventType` | String | — | event_type 值 |
| `size` | Number | 24 | 图标尺寸 (px) |
| `colored` | Boolean | true | 是否使用主题色 |

### 实现

```vue
<!-- frontend/src/components/event/EventIcon.vue -->
<template>
  <span
    class="event-icon"
    :style="{
      width: `${size}px`,
      height: `${size}px`,
      color: colored ? eventColor : 'currentColor',
    }"
    :title="eventName"
  >
    <component :is="iconComponent" />
  </span>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'

const props = defineProps({
  eventType: { type: String, required: true },
  size: { type: Number, default: 24 },
  colored: { type: Boolean, default: true },
})

/**
 * event_type → 配置映射
 */
const EVENT_CONFIG = {
  sunrise_golden_mountain: { color: '#FF8C00', name: '日出金山', icon: 'sunrise-golden-mountain' },
  sunset_golden_mountain:  { color: '#FF4500', name: '日落金山', icon: 'sunset-golden-mountain' },
  cloud_sea:               { color: '#87CEEB', name: '云海',     icon: 'cloud-sea' },
  stargazing:              { color: '#4A0E8F', name: '观星',     icon: 'stargazing' },
  frost:                   { color: '#B0E0E6', name: '雾凇',     icon: 'frost' },
  snow_tree:               { color: '#E0E8EF', name: '树挂积雪', icon: 'snow-tree' },
  ice_icicle:              { color: '#ADD8E6', name: '冰挂',     icon: 'ice-icicle' },
}

const config = computed(() => EVENT_CONFIG[props.eventType] ?? { color: '#9CA3AF', name: props.eventType, icon: null })
const eventColor = computed(() => config.value.color)
const eventName = computed(() => config.value.name)

// SVG 图标通过 import 方式加载 (Vite 支持 ?component 后缀)
// 实现时需根据 Vite SVG 插件配置调整
const iconComponent = computed(() => {
  const iconName = config.value.icon
  if (!iconName) return null
  // 使用 vite-svg-loader 或类似插件将 SVG 作为 Vue 组件加载
  return defineAsyncComponent(() => import(`@/assets/icons/${iconName}.svg`))
})
</script>

<style scoped>
.event-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.event-icon :deep(svg) {
  width: 100%;
  height: 100%;
}
</style>
```

> [!NOTE]
> SVG 作为 Vue 组件加载需要安装 `vite-svg-loader`:
> ```bash
> npm install -D vite-svg-loader
> ```
> 并在 `vite.config.js` 中配置:
> ```javascript
> import svgLoader from 'vite-svg-loader'
> // plugins: [svgLoader(), UnoCSS(), vue()]
> ```

---

## Task 3: EventCard 事件详情卡片

**Files:**
- Create: `frontend/src/components/event/EventCard.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `event` | Object | — | 一个事件对象 (来自 forecast.json 的 events 数组项) |
| `showBreakdown` | Boolean | false | 是否展示评分明细 |

### 事件对象结构 (参考 [05-api.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md))

```javascript
{
  event_type: 'sunrise_golden_mountain',
  display_name: '日出金山',
  time_window: '07:15 - 07:45',
  score: 90,
  status: 'Recommended',
  confidence: 'High',
  tags: ['sunrise', 'golden_mountain', 'clear_sky'],
  conditions: ['东方少云 ☀️', '贡嘎可见 🏔️', '光路通畅 ✨'],
  score_breakdown: {
    light_path:     { score: 35, max: 35 },
    target_visible: { score: 35, max: 40 },
    local_clear:    { score: 20, max: 25 },
  }
}
```

### 实现结构

```
┌─────────────────────────────────┐
│ [EventIcon] 日出金山     [90/环] │
│ 07:15 - 07:45                    │
│ [Recommended] [High]             │
│ ─────────────────────────        │
│ • 东方少云 ☀️                    │
│ • 贡嘎可见 🏔️                   │
│ • 光路通畅 ✨                    │
│ ─────────────────────────        │
│ (展开) 评分明细:                  │
│   光路通畅  ████████ 35/35       │
│   目标可见  ███████▒ 35/40       │
│   本地晴朗  ██████▒▒ 20/25      │
└─────────────────────────────────┘
```

使用的子组件: `EventIcon` (M20.T2), `ScoreRing` (M19.T1), `StatusBadge` (M19.T3), `ScoreBar` (M19.T2)

---

## Task 4: EventList 事件列表

**Files:**
- Create: `frontend/src/components/event/EventList.vue`

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `events` | Array | [] | 事件数组 |
| `showBreakdown` | Boolean | false | 传递给 EventCard |

### 实现

简单的列表容器，遍历 `events` 数组渲染 `EventCard`，带入场动画 (staggered fade-in)。

```vue
<template>
  <div class="event-list">
    <TransitionGroup name="slide-up">
      <EventCard
        v-for="(event, index) in events"
        :key="event.event_type"
        :event="event"
        :showBreakdown="showBreakdown"
        :style="{ transitionDelay: `${index * 80}ms` }"
      />
    </TransitionGroup>
  </div>
</template>
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/components/EventIcon.test.js
```
