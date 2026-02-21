# MH1C: 海报前端页面 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增隐藏路由 `/ops/poster`，实现 `PosterView.vue` 页面和 `PredictionMatrix.vue` 表格组件，支持按山系分组展示预测矩阵表格并一键导出为 PNG 海报图片。

**Architecture:** 前端新增路由 + `loadPoster()` 数据加载 → `PosterView.vue` 页面（标题/天数切换/导出按钮）→ 循环渲染 `PredictionMatrix.vue`（山系×景点×日期×上下午矩阵表格），通过 `useScreenshot` composable 导出 PNG。

**Tech Stack:** Vue 3, Vite, html2canvas

**设计文档:** [12-poster-page.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/12-poster-page.md) §12.4, §12.6

**依赖:** MH1B（后端 `poster.json` 必须已生成）

---

## Proposed Changes

### Task 1: 路由 + 数据加载

---

#### [MODIFY] [index.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/router/index.js)

新增隐藏路由（不在导航中露出）：

```diff
     {
         path: '/route/:id',
         name: 'route-detail',
         component: () => import('@/views/RouteDetail.vue'),
         props: true,
     },
+    {
+        path: '/ops/poster',
+        name: 'poster',
+        component: () => import('@/views/PosterView.vue'),
+    },
 ]
```

---

#### [MODIFY] [useDataLoader.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/composables/useDataLoader.js)

新增 `loadPoster()` 方法：

```diff
+    /**
+     * 加载海报聚合数据
+     * @returns {Promise<Object>} poster.json 内容
+     */
+    async function loadPoster() {
+        return _fetch('poster.json')
+    }

-    return { loadIndex, loadForecast, loadTimeline, loadRouteForecast, loading, error }
+    return { loadIndex, loadForecast, loadTimeline, loadRouteForecast, loadPoster, loading, error }
```

**Step 1:** 修改代码

**Step 2:** Commit

```bash
git add frontend/src/router/index.js frontend/src/composables/useDataLoader.js
git commit -m "feat(poster): add /ops/poster route and loadPoster data loader"
```

---

### Task 2: PredictionMatrix 组件

---

#### [NEW] [PredictionMatrix.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/PredictionMatrix.vue)

Props:
- `group: Object` — `{ name, key, viewpoints }` 山系分组数据
- `days: string[]` — 日期列表
- `showHeader: boolean` — 是否显示组标题行（导出截图时为 true）
- `showFooter: boolean` — 是否显示页脚（导出截图时为 true）
- `generatedAt: string` — 生成时间（页脚用）

表格结构 (设计文档 §12.4)：
- 第一行：组名 | 空 | 日期1 | 日期2 | ...
- 每个景点占两行（上午/下午）
- 格子内容：`天气+事件名`（有推荐事件时）或仅 `天气`
- 格子背景色按 score 着色

色块配色（设计文档 §12.4）：

```javascript
function getCellColor(score) {
    if (score >= 80) return '#C6EFCE'  // 绿色 — 强烈推荐
    if (score >= 50) return '#FFEB9C'  // 黄色 — 值得关注
    if (score >= 25) return '#FFC7CE'  // 橙色 — 条件一般
    return '#F4CCCC'                   // 红色 — 不推荐
}
```

日期格式化：显示为 `M/D` 格式（如 `2/21`）。

**Step 1:** 创建组件

**Step 2:** Commit

```bash
git add frontend/src/components/forecast/PredictionMatrix.vue
git commit -m "feat(poster): add PredictionMatrix table component"
```

---

### Task 3: PosterView 页面

---

#### [NEW] [PosterView.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/PosterView.vue)

页面结构：

```
PosterView.vue
├── PosterHeader          标题 + 日期范围 + 天数切换(3/5/7) + 导出按钮
├── PredictionMatrix ×N   每个山系一个（循环渲染）
└── PosterFooter          数据更新时间 + 品牌信息 (仅截图时可见)
```

主要逻辑：
- `onMounted` 调用 `loadPoster()` 获取数据
- `selectedDays` ref (默认 5)，天数切换改变展示列数
- 「一键导出全部」遍历每个 group 的 `ref`，分别调用 `useScreenshot().capture()`
- 导出时每张图宽度 1080px，自带标题（山系名+日期范围）和页脚（品牌+更新时间）
- 错误/加载状态处理

**Step 1:** 创建页面

**Step 2:** Commit

```bash
git add frontend/src/views/PosterView.vue
git commit -m "feat(poster): add PosterView page with export functionality"
```

---

### Task 4: 前端测试

---

#### [NEW] [PredictionMatrix.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/PredictionMatrix.test.js)

测试用例：
1. `renders group name` — 验证表头显示山系名
2. `renders viewpoint names` — 验证景点名称渲染
3. `renders am/pm rows` — 验证上午/下午行
4. `applies correct score color` — 验证色块映射（≥80 绿 / 50-79 黄 / 25-49 橙 / <25 红）
5. `formats date correctly` — 验证日期格式为 M/D

```javascript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PredictionMatrix from '@/components/forecast/PredictionMatrix.vue'

const mockGroup = {
    name: '贡嘎山系',
    key: 'gongga',
    viewpoints: [{
        id: 'niubei_gongga',
        name: '牛背山',
        daily: [{
            date: '2026-02-21',
            am: { weather: '晴天', event: '日照金山', score: 90 },
            pm: { weather: '晴天', event: '云海', score: 75 },
        }],
    }],
}

describe('PredictionMatrix', () => {
    it('renders group name', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('贡嘎山系')
    })

    it('renders viewpoint names', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('牛背山')
    })

    it('renders am/pm labels', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('上午')
        expect(wrapper.text()).toContain('下午')
    })

    it('applies green background for score >= 80', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        const cells = wrapper.findAll('td')
        const amCell = cells.find(c => c.text().includes('日照金山'))
        expect(amCell?.attributes('style')).toContain('#C6EFCE')
    })
})
```

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend && npx vitest run src/__tests__/components/PredictionMatrix.test.js`

---

#### [NEW] [PosterView.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/PosterView.test.js)

测试用例：
1. `shows loading state` — 验证加载状态
2. `renders all groups after load` — 验证所有分组渲染
3. `day selector defaults to 5` — 验证默认天数

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend && npx vitest run src/__tests__/views/PosterView.test.js`

---

## Verification Plan

### Automated Tests

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/components/PredictionMatrix.test.js src/__tests__/views/PosterView.test.js
```

### 全量前端测试回归

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run
```

### 浏览器验证

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

访问 `http://localhost:5173/ops/poster`，验证：
1. 页面正确加载，显示所有山系分组表格
2. 天数切换 (3/5/7) 正确调整表格列数
3. 表格色块按分数正确着色（绿/黄/橙/红）
4. 格子显示 `天气+事件名` 或仅 `天气`
5. 「一键导出」按钮下载 PNG 图片（每组一张，1080px 宽）

### Manual Verification

用户部署后：
1. 访问 `/ops/poster` 确认数据正确
2. 点击「一键导出全部」下载图片
3. 确认每张图片独立（按山系分组）、宽度 1080px、含标题+页脚

---

*计划版本: v1.0 | 创建: 2026-02-21 | 拆分自 MH1-poster-page.md v2.0*
