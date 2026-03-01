# MI1A: PosterView 参数化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** PosterView 支持 URL query `?days=N` 设置初始天数，天数从明天起算，天数选择器改为 3/7。

**Architecture:** 引入 `vue-router` 的 `useRoute()` 读取 query 参数；`displayedDays` 改为 `days.slice(1, 1+N)` 跳过今天。

**Tech Stack:** Vue 3, vue-router, Vitest

---

### Task 1: 更新测试

**Files:**
- Modify: [`PosterView.test.js`](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/PosterView.test.js)

**Step 1: 修改测试文件**

1. 扩展 `mockPosterData.days` 到 8 天（今天 + 7 天），以覆盖 `slice(1, 1+7)` 场景
2. 新增 `vi.mock('vue-router', ...)` mock
3. 将 `'day selector defaults to 5'` 改为 `'day selector defaults to 7'`
4. 新增 `'reads days from URL query parameter'` 测试

```javascript
// 顶部新增 vue-router mock（模块级）
const mockRouteQuery = {}
vi.mock('vue-router', () => ({
    useRoute: () => ({ query: mockRouteQuery }),
}))

// 在 beforeEach 中重置 query
beforeEach(() => {
    mockLoadPoster.mockReset()
    mockLoadPoster.mockResolvedValue(mockPosterData)
    // 清空 query
    Object.keys(mockRouteQuery).forEach(k => delete mockRouteQuery[k])
})

// 修改默认天数测试
it('day selector defaults to 7', async () => {
    const wrapper = mount(PosterView, { global: globalConfig })
    await flushPromises()
    const activeBtn = wrapper.find('.day-btn.active')
    expect(activeBtn?.text()).toBe('7天')
})

// 新增 query 参数测试
it('reads days from URL query parameter', async () => {
    mockRouteQuery.days = '3'
    const wrapper = mount(PosterView, { global: globalConfig })
    await flushPromises()
    const activeBtn = wrapper.find('.day-btn.active')
    expect(activeBtn?.text()).toBe('3天')
})
```

**Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/__tests__/views/PosterView.test.js`

Expected: FAIL — `selectedDays` 仍为 5，且未用 `useRoute`

---

### Task 2: 修改 PosterView.vue

**Files:**
- Modify: [`PosterView.vue`](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/PosterView.vue)

**Step 1: 修改 script 部分**

```diff
 <script setup>
 import { ref, computed, reactive, onMounted } from 'vue'
+import { useRoute } from 'vue-router'
 import { useDataLoader } from '@/composables/useDataLoader'
 import PredictionMatrix from '@/components/forecast/PredictionMatrix.vue'

+const route = useRoute()
 const { loadPoster } = useDataLoader()

 const posterData = ref(null)
 const loading = ref(true)
 const error = ref(null)
-const selectedDays = ref(5)
+const selectedDays = ref(Number(route.query.days) || 7)

 const displayedDays = computed(() => {
     if (!posterData.value) return []
-    return posterData.value.days.slice(0, selectedDays.value)
+    return posterData.value.days.slice(1, 1 + selectedDays.value)
 })
```

**Step 2: 修改 template — 天数选择器**

```diff
-<button v-for="d in [3, 5, 7]" ...>{{ d }}天</button>
+<button v-for="d in [3, 7]" ...>{{ d }}天</button>
```

**Step 3: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/__tests__/views/PosterView.test.js`

Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/views/PosterView.vue frontend/src/__tests__/views/PosterView.test.js
git commit -m "feat(poster): read days from URL query, start from tomorrow"
```

---

## 验证计划

### 自动化测试
```bash
cd frontend && npx vitest run src/__tests__/views/PosterView.test.js
```

### 浏览器验证（MI1D 阶段执行）
- 访问 `/ops/poster?days=3`，确认显示从明天起 3 天
- 访问 `/ops/poster`（无参数），确认默认 7 天
- 确认天数选择器只有 3 和 7 两个按钮
