# M16: 前端项目初始化

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 创建 Vite + Vue 3 前端项目，安装所有公共依赖，建立目录骨架和全局样式系统。

**依赖模块:** 无 (前端独立项目)

---

## 背景

GMP 前端是一个独立的 Vue 3 SPA 项目，部署在 Cloudflare Pages 上。后端 Python 引擎通过 `generate-all` 命令预生成 JSON 数据文件到 `public/data/` 目录，前端按需加载这些静态 JSON。

前端项目位于仓库根目录下的 `frontend/` 目录中，与 Python 后端代码 (`gmp/`) 并列。

### 设计参考

- [10-frontend-common.md §10.0.1 技术栈与项目结构](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [10-frontend-common.md §10.0.7 配色方案](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [10-frontend-common.md §10.0.8 路由设计](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)

### 技术栈

| 技术 | 版本/说明 |
|------|-----------|
| Vite | 最新稳定版 |
| Vue 3 | Composition API |
| Pinia | 状态管理 |
| Vue Router | 路由 |
| UnoCSS | 原子化 CSS (Attributify Mode) |
| GSAP | 动画库 (含 ScrollTrigger) |
| ECharts | 图表 (按需引入) |
| html2canvas | 截图导出 |
| 高德地图 JS API v2.0 | 地图服务 |

---

## Task 1: 创建 Vite + Vue 3 项目

**Files:**
- Create: `frontend/` (项目根目录)

**Step 1: 初始化 Vue 项目**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor
npx -y create-vite@latest frontend -- --template vue
```

**Step 2: 安装核心依赖**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm install vue-router@4 pinia
npm install gsap echarts html2canvas
npm install -D unocss @unocss/preset-attributify @unocss/preset-uno @unocss/transformer-attributify-jsx
```

**Step 3: 验证项目可运行**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

Expected: 浏览器可访问 `http://localhost:5173`，显示 Vite + Vue 默认页面。

**Step 4: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): init Vite + Vue 3 project with dependencies"
```

---

## Task 2: 配置 UnoCSS

**Files:**
- Create: `frontend/uno.config.js`
- Modify: `frontend/vite.config.js`

**Step 1: 创建 UnoCSS 配置**

```javascript
// frontend/uno.config.js
import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
  ],
  theme: {
    colors: {
      primary: '#3B82F6',
      'primary-light': '#93C5FD',
      accent: '#F59E0B',
      'accent-warm': '#EF4444',
      'score-recommended': '#10B981',
      'score-possible': '#F59E0B',
      'score-not-recommended': '#9CA3AF',
    },
    borderRadius: {
      sm: '8px',
      md: '12px',
      lg: '20px',
      full: '9999px',
    },
  },
})
```

**Step 2: 集成到 Vite**

```javascript
// frontend/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'

export default defineConfig({
  plugins: [
    UnoCSS(),
    vue(),
  ],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
```

**Step 3: 在 main.js 中引入 UnoCSS**

```javascript
// frontend/src/main.js
import 'virtual:uno.css'
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```

**Step 4: 验证 UnoCSS 生效**

在 `App.vue` 中添加一个使用 UnoCSS 类名的元素:
```html
<div text-2xl font-bold text-primary>GMP 测试</div>
```

运行 `npm run dev`，确认蓝色加粗文字正常显示。

**Step 5: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): configure UnoCSS with attributify mode"
```

---

## Task 3: 建立目录骨架

**Files:**
- Create: 以下所有目录和空文件

**Step 1: 创建目录结构**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend/src

# 删除 Vite 默认文件
rm -rf components/HelloWorld.vue assets/vue.svg style.css

# 创建目录结构
mkdir -p router
mkdir -p stores
mkdir -p composables
mkdir -p components/score
mkdir -p components/event
mkdir -p components/forecast
mkdir -p components/map
mkdir -p components/layout
mkdir -p components/export
mkdir -p assets/icons
mkdir -p assets/styles
mkdir -p assets/illustrations
mkdir -p views
```

**Step 2: 创建目录占位文件**

为每个目录创建空的 `index.js` 或占位文件，确保 Git 追踪。

```bash
# 入口文件
touch router/index.js
touch stores/viewpoints.js
touch stores/routes.js
touch stores/app.js

# composables
touch composables/useDataLoader.js
touch composables/useScoreColor.js
touch composables/useComboTags.js
touch composables/useAMap.js
touch composables/useScreenshot.js

# views (三方案共用的详情页)
touch views/ViewpointDetail.vue
touch views/RouteDetail.vue
```

**Step 3: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): create directory skeleton"
```

---

## Task 4: 全局样式系统 — CSS 变量

**Files:**
- Create: `frontend/src/assets/styles/variables.css`
- Create: `frontend/src/assets/styles/typography.css`
- Create: `frontend/src/assets/styles/animations.css`
- Modify: `frontend/src/main.js`

**Step 1: 创建 CSS 变量文件**

```css
/* frontend/src/assets/styles/variables.css */

:root {
  /* 基础色调 */
  --color-primary: #3B82F6;       /* 高山蓝 */
  --color-primary-light: #93C5FD;
  --color-accent: #F59E0B;        /* 日出金 */
  --color-accent-warm: #EF4444;   /* 晚霞红 */

  /* 评分色阶 */
  --score-perfect: linear-gradient(135deg, #FFD700, #FF8C00);
  --score-recommended: #10B981;
  --score-possible: #F59E0B;
  --score-not-recommended: #9CA3AF;

  /* 评分纯色 (用于非渐变场景) */
  --score-perfect-solid: #FFD700;
  --score-recommended-solid: #10B981;
  --score-possible-solid: #F59E0B;
  --score-not-recommended-solid: #9CA3AF;

  /* 背景 */
  --bg-primary: #F8FAFC;
  --bg-card: #FFFFFF;
  --bg-overlay: rgba(255, 255, 255, 0.85);

  /* 文字 */
  --text-primary: #1E293B;
  --text-secondary: #64748B;
  --text-muted: #94A3B8;

  /* 圆角 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-full: 9999px;

  /* 阴影 */
  --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-elevated: 0 8px 24px rgba(0, 0, 0, 0.1);
  --shadow-float: 0 16px 48px rgba(0, 0, 0, 0.12);

  /* 动画 */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 200ms;
  --duration-normal: 350ms;
  --duration-slow: 600ms;
}
```

**Step 2: 创建字体系统**

```css
/* frontend/src/assets/styles/typography.css */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --font-sans: 'Inter', -apple-system, 'PingFang SC', 'Noto Sans SC', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  --text-xs: 0.75rem;    /* 12px — 标签 */
  --text-sm: 0.875rem;   /* 14px — 辅助说明 */
  --text-base: 1rem;     /* 16px — 正文 */
  --text-lg: 1.125rem;   /* 18px — 小标题 */
  --text-xl: 1.5rem;     /* 24px — 标题 */
  --text-2xl: 2rem;      /* 32px — 大标题 */
  --text-4xl: 3rem;      /* 48px — 评分数字 */
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  color: var(--text-primary);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

**Step 3: 创建公共动画定义**

```css
/* frontend/src/assets/styles/animations.css */

/* 评分环进入动画 */
@keyframes score-ring-fill {
  from { stroke-dashoffset: var(--ring-circumference); }
  to   { stroke-dashoffset: var(--ring-target-offset); }
}

/* 卡片浮入 */
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 弹跳标记 */
@keyframes marker-bounce {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-8px); }
}

/* 脉冲光圈 (Perfect 状态) */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.4); }
  50%      { box-shadow: 0 0 0 12px rgba(255, 215, 0, 0); }
}

/* 渐入 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-out-expo);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 上滑进入 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all var(--duration-normal) var(--ease-out-expo);
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(30px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
```

**Step 4: 在 main.js 引入全局样式**

```javascript
// frontend/src/main.js
import 'virtual:uno.css'
import './assets/styles/variables.css'
import './assets/styles/typography.css'
import './assets/styles/animations.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

**Step 5: 验证样式生效**

修改 `App.vue` 使用 CSS 变量:
```vue
<template>
  <div :style="{ color: 'var(--color-primary)' }">
    <h1 :style="{ fontSize: 'var(--text-2xl)' }">GMP 前端</h1>
    <p :style="{ color: 'var(--text-secondary)' }">样式系统测试</p>
  </div>
</template>
```

运行 `npm run dev`，确认字体为 Inter、颜色为高山蓝。

**Step 6: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): add global style system (variables, typography, animations)"
```

---

## Task 5: Vue Router 基础配置

**Files:**
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/views/HomeView.vue` (占位)
- Create: `frontend/src/views/ViewpointDetail.vue` (占位)
- Create: `frontend/src/views/RouteDetail.vue` (占位)
- Modify: `frontend/src/App.vue`

**Step 1: 创建路由配置**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/viewpoint/:id',
    name: 'viewpoint-detail',
    component: () => import('@/views/ViewpointDetail.vue'),
    props: true,
  },
  {
    path: '/viewpoint/:id/:date',
    name: 'viewpoint-date',
    component: () => import('@/views/ViewpointDetail.vue'),
    props: true,
  },
  {
    path: '/route/:id',
    name: 'route-detail',
    component: () => import('@/views/RouteDetail.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

路由定义参考: [10-frontend-common.md §10.0.8](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)

**Step 2: 创建占位 Views**

```vue
<!-- frontend/src/views/HomeView.vue -->
<template>
  <div class="home-view">
    <h1>GMP — 川西景观预测</h1>
    <p>首页 (方案特定布局将在此挂载)</p>
  </div>
</template>

<script setup>
// 方案 A/B/C 将替换此组件
</script>
```

```vue
<!-- frontend/src/views/ViewpointDetail.vue -->
<template>
  <div class="viewpoint-detail">
    <h1>观景台详情: {{ id }}</h1>
    <p v-if="date">日期: {{ date }}</p>
    <p>详情页组件将在 M25 中实现</p>
  </div>
</template>

<script setup>
const props = defineProps({
  id: String,
  date: { type: String, default: null },
})
</script>
```

```vue
<!-- frontend/src/views/RouteDetail.vue -->
<template>
  <div class="route-detail">
    <h1>线路详情: {{ id }}</h1>
    <p>线路详情页组件将在 M25 中实现</p>
  </div>
</template>

<script setup>
const props = defineProps({
  id: String,
})
</script>
```

**Step 3: 更新 App.vue**

```vue
<!-- frontend/src/App.vue -->
<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
// 根组件，提供路由视图和过渡动画
</script>

<style>
/* 全局重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: var(--bg-primary);
}

#app {
  min-height: 100vh;
}
</style>
```

**Step 4: 验证路由**

运行 `npm run dev`，分别访问:
- `http://localhost:5173/` → 显示首页占位
- `http://localhost:5173/viewpoint/niubei_gongga` → 显示观景台详情占位
- `http://localhost:5173/route/lixiao` → 显示线路详情占位

**Step 5: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): configure Vue Router with route stubs"
```

---

## Task 6: 高德地图 JS API 引入

**Files:**
- Modify: `frontend/index.html`
- Create: `frontend/.env.development`
- Create: `frontend/.env.production`

**Step 1: 配置环境变量**

```bash
# frontend/.env.development
VITE_AMAP_KEY=your_development_key_here
VITE_AMAP_SECURITY_CODE=your_security_code_here
```

```bash
# frontend/.env.production
VITE_AMAP_KEY=your_production_key_here
VITE_AMAP_SECURITY_CODE=your_security_code_here
```

> [!IMPORTANT]
> 高德地图 API Key 需在 https://console.amap.com/ 申请。开发阶段可先使用占位值，确保代码结构正确。
> `.env.development` 和 `.env.production` 应添加到 `.gitignore`。

**Step 2: 在 index.html 引入高德地图**

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="川西景观预测 — 日照金山、云海、观星、雾凇 最佳时机一键查看">
    <meta property="og:title" content="川西景观预测引擎 GMP">
    <meta property="og:description" content="让每一次川西之行，都不错过自然的馈赠">
    <title>川西景观预测 — GMP</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

> [!NOTE]
> 高德地图 JS API v2.0 推荐通过 `AMapLoader` 动态加载，不在 index.html 中直接引入 script 标签。
> 具体加载逻辑在 `useAMap` composable 中实现 (M18)。

**Step 3: 安装高德地图加载器**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm install @amap/amap-jsapi-loader
```

**Step 4: 更新 .gitignore**

在 `frontend/.gitignore` 中添加:
```
.env.development
.env.production
.env.local
```

**Step 5: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): add AMap loader dependency and env config"
```

---

## Task 7: 创建模拟 JSON 数据

**Files:**
- Create: `frontend/public/data/index.json`
- Create: `frontend/public/data/meta.json`
- Create: `frontend/public/data/viewpoints/niubei_gongga/forecast.json`
- Create: `frontend/public/data/viewpoints/niubei_gongga/timeline_2026-02-12.json`

> [!IMPORTANT]
> 这些是开发阶段的模拟数据，数据结构严格遵循 [05-api.md §5.2](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md)。
> 生产环境中由后端 `generate-all` 命令生成真实数据替换。

**Step 1: 创建 index.json**

```json
{
  "viewpoints": [
    {
      "id": "niubei_gongga",
      "name": "牛背山",
      "location": {"lat": 29.75, "lon": 102.35, "altitude": 3660},
      "capabilities": ["sunrise", "cloud_sea", "stargazing", "frost"],
      "forecast_url": "viewpoints/niubei_gongga/forecast.json"
    },
    {
      "id": "zheduo_gongga",
      "name": "折多山",
      "location": {"lat": 30.05, "lon": 101.75, "altitude": 4298},
      "capabilities": ["sunrise", "cloud_sea", "frost", "snow_tree"],
      "forecast_url": "viewpoints/zheduo_gongga/forecast.json"
    }
  ],
  "routes": [
    {
      "id": "lixiao",
      "name": "理小路",
      "stops": [
        {"viewpoint_id": "zheduo_gongga", "name": "折多山"},
        {"viewpoint_id": "niubei_gongga", "name": "牛背山"}
      ],
      "forecast_url": "routes/lixiao/forecast.json"
    }
  ]
}
```

**Step 2: 创建模拟 forecast.json 和 timeline.json**

forecast.json 和 timeline.json 结构参考 [05-api.md §5.2](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md)。

包含 7 天完整数据，各 event_type 评分在 30-98 范围内分布，确保覆盖所有 4 个 status 等级 (Perfect / Recommended / Possible / Not Recommended)。

**Step 3: 提交**

```bash
git add frontend/public/data/
git commit -m "feat(frontend): add mock JSON data for development"
```

---

## 验证命令

```bash
# 确认项目可以正常构建
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run build

# 确认开发服务器可以正常启动
npm run dev
```
